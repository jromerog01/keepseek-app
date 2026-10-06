from app.services import analyzer, platforms
from app.services.errors import clean_error
from app.services.urls import InvalidUrl, validate_url

import pytest


def vfmt(width, height, fps=30, tbr=1000, vcodec="avc1", **extra):
    return {"width": width, "height": height, "fps": fps, "tbr": tbr, "vcodec": vcodec, "acodec": "none", **extra}


AUDIO = {"vcodec": "none", "acodec": "mp4a", "tbr": 128}


def test_only_available_resolutions_are_offered():
    formats = [vfmt(1920, 1080), vfmt(1280, 720), vfmt(854, 480), AUDIO]
    ids = [q["id"] for q in analyzer.video_qualities(formats, 100)]
    assert ids == ["1080", "720", "480"]


def test_recommended_is_1080_when_available():
    formats = [vfmt(3840, 2160), vfmt(1920, 1080), vfmt(1280, 720), AUDIO]
    qualities = analyzer.video_qualities(formats, 100)
    assert [q["id"] for q in qualities] == ["2160", "1080", "720", "480"]
    assert [q["id"] for q in qualities if q["note"]] == ["1080"]


def test_recommended_falls_back_to_best_when_no_1080():
    qualities = analyzer.video_qualities([vfmt(1280, 720), AUDIO], 100)
    assert qualities[0]["id"] == "720"
    assert qualities[0]["note"] == "Recomendado"


def test_low_resolution_video_still_offers_480_floor():
    qualities = analyzer.video_qualities([vfmt(640, 360), AUDIO], 100)
    assert [q["id"] for q in qualities] == ["480"]


def test_vertical_video_is_classified_by_short_side():
    formats = [vfmt(1080, 1920), vfmt(720, 1280), AUDIO]
    ids = [q["id"] for q in analyzer.video_qualities(formats, 30)]
    assert ids == ["1080", "720", "480"]


def test_fps_options_only_when_that_resolution_has_60fps():
    formats = [vfmt(1920, 1080, fps=60), vfmt(1920, 1080, fps=30), vfmt(1280, 720, fps=30), AUDIO]
    by_id = {q["id"]: q for q in analyzer.video_qualities(formats, 100)}
    assert by_id["1080"]["fps"] == [60, 30]
    assert by_id["720"]["fps"] == []


def test_size_is_video_plus_audio():
    formats = [vfmt(1920, 1080, filesize=1000), {**AUDIO, "filesize": 200}]
    qualities = analyzer.video_qualities(formats, 100)
    assert qualities[0]["size_bytes"] == 1200


def test_size_is_estimated_from_bitrate_when_missing():
    formats = [vfmt(1920, 1080, tbr=800), {**AUDIO, "tbr": 200}]
    size = analyzer.video_qualities(formats, 10)[0]["size_bytes"]
    assert size == int(800 * 1000 / 8 * 10) + int(200 * 1000 / 8 * 10)


def test_size_is_none_without_data():
    formats = [vfmt(1920, 1080, tbr=None), AUDIO]
    assert analyzer.video_qualities(formats, None)[0]["size_bytes"] is None


def test_audio_qualities_recommend_320():
    qualities = analyzer.audio_qualities([], 60)
    assert [q["id"] for q in qualities] == ["320", "192", "128"]
    assert qualities[0]["note"] == "Recomendado"
    assert qualities[0]["size_bytes"] == 320 * 1000 // 8 * 60


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://youtu.be/abc", "youtube"),
        ("https://www.instagram.com/reel/x", "instagram"),
        ("https://fb.watch/x", "facebook"),
        ("https://www.tiktok.com/@a/video/1", "tiktok"),
        ("https://x.com/a/status/1", "x"),
        ("https://twitter.com/a/status/1", "x"),
        ("https://vimeo.com/1", "vimeo"),
        ("https://redd.it/x", "reddit"),
        ("https://soundcloud.com/a/b", "soundcloud"),
        ("https://www.twitch.tv/videos/1", "other"),
    ],
)
def test_platform_from_url(url, expected):
    assert platforms.from_url(url)["id"] == expected


def test_platform_from_extractor_key():
    assert platforms.from_extractor("TikTok", "https://x")["mono"] == "TT"
    assert platforms.from_extractor("YoutubeTab", "https://x")["id"] == "youtube"
    assert platforms.from_extractor("Twitter", "https://x")["id"] == "x"
    assert platforms.from_extractor("Twitch", "https://twitch.tv/v")["id"] == "other"


def test_url_validation():
    assert validate_url("https://example.com/video", allow_private=True) == "https://example.com/video"
    for bad in ["ftp://example.com/x", "javascript:alert(1)", "no-es-url", ""]:
        with pytest.raises(InvalidUrl):
            validate_url(bad, allow_private=True)


@pytest.mark.parametrize("url", ["http://127.0.0.1:8000/x", "http://localhost/x", "http://192.168.1.10/x", "http://[::1]/x"])
def test_private_hosts_are_rejected(url):
    with pytest.raises(InvalidUrl):
        validate_url(url, allow_private=False)


def test_clean_error_strips_ansi_and_prefixes():
    exc = Exception("\x1b[0;31mERROR:\x1b[0m [youtube] abc123: Video unavailable")
    assert clean_error(exc) == "Video unavailable"


def test_clean_error_explains_forbidden_site_blocks():
    exc = Exception("ERROR: [Example] abc: Unable to download webpage: HTTP Error 403: Forbidden")
    assert clean_error(exc).startswith("El sitio bloqueó la solicitud (403).")


def test_size_estimate_follows_the_codec_the_downloader_will_pick():
    small_h264 = vfmt(1920, 1080, tbr=800, vcodec="avc1.640028", filesize=100)
    big_av1 = vfmt(1920, 1080, tbr=2000, vcodec="av01.0.08M.08", filesize=900)
    formats = [small_h264, big_av1, {**AUDIO, "filesize": 10}]
    assert analyzer.video_qualities(formats, 100)[0]["size_bytes"] == 110


def test_4k_estimate_uses_vp9_not_the_heaviest_codec():
    vp9 = vfmt(3840, 2160, tbr=15000, vcodec="vp09.00.50.08", filesize=1000)
    av1 = vfmt(3840, 2160, tbr=25000, vcodec="av01.0.12M.08", filesize=1800)
    formats = [vp9, av1, vfmt(1920, 1080), {**AUDIO, "filesize": 10}]
    by_id = {q["id"]: q for q in analyzer.video_qualities(formats, 100)}
    assert by_id["2160"]["size_bytes"] == 1010


def test_audio_estimate_prefers_aac_like_the_downloader():
    opus = {"vcodec": "none", "acodec": "opus", "tbr": 160, "filesize": 500}
    aac = {"vcodec": "none", "acodec": "mp4a.40.2", "tbr": 128, "filesize": 100}
    formats = [vfmt(1920, 1080, filesize=1000), opus, aac]
    assert analyzer.video_qualities(formats, 100)[0]["size_bytes"] == 1100


# ---------- el estimado de tamaño nunca queda vacío ----------

def bare(width, height, **extra):
    """Formato sin peso ni bitrate, como publican algunos sitios."""
    return {"width": width, "height": height, "vcodec": "avc1", "acodec": "none", **extra}


def test_every_quality_has_a_rate_even_when_the_site_gives_no_size_or_bitrate():
    qualities = analyzer.video_qualities([bare(1920, 1080), bare(1280, 720), AUDIO_NO_TBR], 120)
    assert qualities
    for quality in qualities:
        assert isinstance(quality["bps"], int) and quality["bps"] > 0


AUDIO_NO_TBR = {"vcodec": "none", "acodec": "mp4a"}


def test_model_rate_is_used_when_there_is_no_data():
    by_id = {q["id"]: q for q in analyzer.video_qualities([bare(1920, 1080), bare(1280, 720)], None)}
    assert by_id["1080"]["bps"] == analyzer.MODEL_VIDEO_BPS[1080]
    assert by_id["720"]["bps"] == analyzer.MODEL_VIDEO_BPS[720]


def test_rate_comes_from_the_bitrate_when_available():
    quality = analyzer.video_qualities([vfmt(1920, 1080, tbr=800), {**AUDIO, "tbr": 200}], None)[0]
    assert quality["bps"] == 800 * 125 + 200 * 125


def test_size_needs_a_duration_but_the_rate_does_not():
    quality = analyzer.video_qualities([vfmt(1920, 1080, tbr=800), AUDIO], None)[0]
    assert quality["size_bytes"] is None and quality["bps"] > 0
    with_duration = analyzer.video_qualities([vfmt(1920, 1080, tbr=800), AUDIO], 10)[0]
    assert with_duration["size_bytes"] == round(with_duration["bps"] * 10)


def test_30fps_rate_uses_the_real_30fps_format_when_it_exists():
    formats = [vfmt(1920, 1080, fps=60, tbr=4000), vfmt(1920, 1080, fps=30, tbr=2500), {**AUDIO, "tbr": 128}]
    quality = analyzer.video_qualities(formats, 100)[0]
    assert quality["bps"] == 4000 * 125 + 128 * 125
    assert quality["bps_30"] == 2500 * 125 + 128 * 125


def test_30fps_rate_is_derived_when_only_60fps_exists():
    quality = analyzer.video_qualities([vfmt(1920, 1080, fps=60, tbr=4000), {**AUDIO, "tbr": 128}], 100)[0]
    assert quality["bps_30"] == round(quality["bps"] / analyzer.FPS_60_FACTOR)


def test_no_30fps_rate_when_there_is_no_fps_choice():
    quality = analyzer.video_qualities([vfmt(1920, 1080, fps=30), AUDIO], 100)[0]
    assert quality["fps"] == [] and quality["bps_30"] is None


def test_audio_qualities_carry_their_exact_rate():
    assert [(q["id"], q["bps"]) for q in analyzer.audio_qualities([], None)] == [("320", 40000), ("192", 24000), ("128", 16000)]


def test_playlist_and_formatless_sites_use_the_model():
    qualities = analyzer._fixed_playlist_qualities()
    assert [q["bps"] for q in qualities] == [analyzer.MODEL_VIDEO_BPS[h] for h in analyzer.RES_TARGETS]
    assert [q["bps_30"] is not None for q in qualities] == [True, True, False, False]
