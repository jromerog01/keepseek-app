import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Lo que la app Fotos del iPhone acepta guardar
PHOTOS_VIDEO_CODECS = {"h264", "hevc"}
PHOTOS_AUDIO_CODECS = {"aac", "mp3", "alac"}

FFPROBE_TIMEOUT = 60


@dataclass
class Verdict:
    video_ok: bool
    audio_ok: bool

    @property
    def ok(self) -> bool:
        return self.video_ok and self.audio_ok


def _probe(path: Path) -> list[dict]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", str(path)],
        capture_output=True, text=True, check=True, timeout=FFPROBE_TIMEOUT,
    )
    return json.loads(result.stdout).get("streams", [])


def _video_stream_ok(stream: dict) -> bool:
    if stream.get("codec_name") not in PHOTOS_VIDEO_CODECS:
        return False
    # iOS no decodifica H.264 de 10 bits (High 10)
    if stream["codec_name"] == "h264" and stream.get("pix_fmt", "yuv420p") != "yuv420p":
        return False
    return True


def check(path: Path) -> Verdict:
    streams = _probe(path)
    videos = [s for s in streams if s.get("codec_type") == "video" and not s.get("disposition", {}).get("attached_pic")]
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    return Verdict(
        video_ok=all(_video_stream_ok(s) for s in videos),
        audio_ok=all(s.get("codec_name") in PHOTOS_AUDIO_CODECS for s in audios),
    )


def fix(path: Path, verdict: Verdict) -> None:
    """Convierte solo lo que Fotos no acepta; lo compatible se copia sin recodificar."""
    output = path.with_name(path.stem + ".compat.mp4")
    command = ["ffmpeg", "-y", "-v", "error", "-i", str(path), "-map", "0:v:0?", "-map", "0:a:0?"]

    if verdict.video_ok:
        command += ["-c:v", "copy"]
    else:
        command += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p"]

    if verdict.audio_ok:
        command += ["-c:a", "copy"]
    else:
        command += ["-c:a", "aac", "-b:a", "192k"]

    command += ["-movflags", "+faststart", str(output)]

    try:
        subprocess.run(command, capture_output=True, text=True, check=True)
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    path.unlink()
    output.rename(path)
