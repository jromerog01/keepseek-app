import json
import shutil
import subprocess

import pytest

from app.services import compat

NEEDED = ("libx264", "libvpx-vp9", "libopus", "aac")


def _have_encoders() -> bool:
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        return False
    out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    return all(name in out for name in NEEDED)


pytestmark = pytest.mark.skipif(not _have_encoders(), reason="ffmpeg con libx264, vp9, opus y aac no disponible")


def make_video(path, video_args, audio_args):
    command = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=15",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        *video_args, *audio_args, "-shortest", str(path),
    ]
    subprocess.run(command, check=True, capture_output=True)
    return path


def codecs(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return {s["codec_type"]: (s["codec_name"], s.get("pix_fmt")) for s in json.loads(out)["streams"]}


H264 = ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
AAC = ["-c:a", "aac"]


def test_h264_aac_is_already_compatible(tmp_path):
    path = make_video(tmp_path / "ok.mp4", H264, AAC)
    verdict = compat.check(path)
    assert verdict.ok


def test_vp9_and_opus_are_flagged_and_converted(tmp_path):
    path = make_video(tmp_path / "vp9.mp4", ["-c:v", "libvpx-vp9"], ["-c:a", "libopus"])
    verdict = compat.check(path)
    assert not verdict.video_ok and not verdict.audio_ok

    compat.fix(path, verdict)

    assert path.is_file()
    assert not list(tmp_path.glob("*.compat.mp4"))
    result = codecs(path)
    assert result["video"][0] == "h264" and result["video"][1] == "yuv420p"
    assert result["audio"][0] == "aac"
    assert compat.check(path).ok


def test_only_audio_is_converted_when_video_is_fine(tmp_path):
    path = make_video(tmp_path / "opus.mp4", H264, ["-c:a", "libopus"])
    verdict = compat.check(path)
    assert verdict.video_ok and not verdict.audio_ok

    compat.fix(path, verdict)

    result = codecs(path)
    assert result["video"][0] == "h264"
    assert result["audio"][0] == "aac"


def test_ten_bit_h264_is_not_accepted_by_ios(tmp_path):
    path = make_video(tmp_path / "10bit.mp4", ["-c:v", "libx264", "-pix_fmt", "yuv420p10le"], AAC)
    verdict = compat.check(path)
    assert not verdict.video_ok and verdict.audio_ok

    compat.fix(path, verdict)

    assert codecs(path)["video"] == ("h264", "yuv420p")


def test_failed_conversion_keeps_the_original(tmp_path):
    path = tmp_path / "roto.mp4"
    path.write_bytes(b"esto no es un video")
    with pytest.raises(subprocess.CalledProcessError):
        compat.fix(path, compat.Verdict(video_ok=False, audio_ok=False))
    assert path.read_bytes() == b"esto no es un video"
    assert not list(tmp_path.glob("*.compat.mp4"))
