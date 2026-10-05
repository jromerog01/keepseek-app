from pathlib import Path

import pytest

from app.services import formats

OUT = Path("/tmp/out")


def opts(**kwargs):
    base = dict(mode="video", quality="1080", fps=None, fmt="MP4", out_dir=OUT)
    base.update(kwargs)
    return formats.build_ydl_opts(**base)


def test_mp4_requires_h264_and_aac_for_iphone_with_fallback():
    selector = opts()["format"]
    first_choice, *fallbacks = selector.split("/")
    assert "avc|h264" in first_choice and "mp4a|aac" in first_choice
    assert fallbacks[-1] == "b" and "bv*+ba" in fallbacks


def test_mp4_prefers_h264_and_m4a_for_iphone():
    result = opts()
    assert result["format_sort"] == ["res:1080", "vcodec:h264", "acodec:m4a"]
    assert result["merge_output_format"] == "mp4"


def test_fps_cap_goes_before_codec_preference():
    result = opts(quality="720", fps=30)
    assert result["format_sort"] == ["res:720", "fps:30", "vcodec:h264", "acodec:m4a"]


def test_webm_and_mkv_do_not_force_h264():
    assert opts(fmt="WEBM")["format"] == "bv*+ba/b"
    assert opts(fmt="MKV")["format"] == "bv*+ba/b"


def test_webm_prefers_vp9_opus():
    result = opts(fmt="WEBM")
    assert result["format_sort"] == ["res:1080", "vcodec:vp9", "acodec:opus"]
    assert result["merge_output_format"] == "webm"


def test_mkv_has_no_codec_preference():
    result = opts(fmt="MKV")
    assert result["format_sort"] == ["res:1080"]
    assert result["merge_output_format"] == "mkv"


@pytest.mark.parametrize(
    "fmt,codec",
    [("MP3", "mp3"), ("M4A", "m4a"), ("OPUS", "opus")],
)
def test_audio_uses_extract_audio_postprocessor(fmt, codec):
    result = opts(mode="audio", quality="192", fmt=fmt)
    assert result["format"] == "ba/b"
    assert result["postprocessors"] == [
        {"key": "FFmpegExtractAudio", "preferredcodec": codec, "preferredquality": "192"}
    ]
    assert "format_sort" not in result


def test_common_options():
    result = opts()
    assert result["noplaylist"] is True
    assert result["continuedl"] is True
    assert result["outtmpl"] == "/tmp/out/%(title).90B [%(id)s].%(ext)s"
    assert "cookiefile" not in result


def test_cookies_are_added_when_present(tmp_path):
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("")
    assert opts(cookies_path=cookies)["cookiefile"] == str(cookies)


@pytest.mark.parametrize(
    "mode,quality,fps,fmt",
    [
        ("video", "999", None, "MP4"),
        ("video", "1080", None, "MP3"),
        ("video", "1080", 24, "MP4"),
        ("audio", "1080", None, "MP3"),
        ("audio", "320", 30, "MP3"),
        ("audio", "320", None, "MP4"),
        ("subtitles", "1080", None, "MP4"),
    ],
)
def test_invalid_combinations_raise(mode, quality, fps, fmt):
    with pytest.raises(ValueError):
        formats.validate_options(mode, quality, fps, fmt)


def test_spec_labels():
    assert formats.spec_label("video", "1080", None, "MP4") == "1080p · MP4"
    assert formats.spec_label("video", "1080", 60, "MP4") == "1080p 60 fps · MP4"
    assert formats.spec_label("audio", "320", None, "MP3") == "320 kbps · MP3"
