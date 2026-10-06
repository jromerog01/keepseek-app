from pathlib import Path

from yt_dlp import YoutubeDL

from app.services import platforms
from app.services.ytdlp_options import browser_request_opts

RES_TARGETS = (2160, 1080, 720, 480)
AUDIO_TARGETS = (320, 192, 128)
RECOMMENDED_VIDEO = 1080
RECOMMENDED_AUDIO = 320


def _res(fmt: dict) -> int | None:
    sides = [v for v in (fmt.get("width"), fmt.get("height")) if v]
    return min(sides) if sides else None


def _has_video(fmt: dict) -> bool:
    return fmt.get("vcodec") not in (None, "none")


def _has_audio(fmt: dict) -> bool:
    return fmt.get("acodec") not in (None, "none")


def _estimate_bytes(fmt: dict | None, duration: int | None) -> int | None:
    if not fmt:
        return None
    size = fmt.get("filesize") or fmt.get("filesize_approx")
    if size:
        return int(size)
    tbr = fmt.get("tbr")
    if tbr and duration:
        return int(tbr * 1000 / 8 * duration)
    return None


def _largest(formats: list[dict]) -> dict | None:
    return max(formats, key=lambda f: f.get("tbr") or 0) if formats else None


def _codec_matches(fmt: dict, field: str, prefixes: tuple[str, ...]) -> bool:
    return (fmt.get(field) or "").lower().startswith(prefixes)


def _expected_video(tier: list[dict]) -> dict | None:
    """El formato que bajará el descargador: H.264 si existe en esa resolución, si no VP9, si no el más pesado."""
    for prefixes in (("avc", "h264"), ("vp9", "vp09")):
        candidates = [f for f in tier if _codec_matches(f, "vcodec", prefixes)]
        if candidates:
            return _largest(candidates)
    return _largest(tier)


def _expected_audio(audios: list[dict]) -> dict | None:
    """El descargador prefiere audio AAC (m4a); sin él, el más pesado."""
    aac = [f for f in audios if _codec_matches(f, "acodec", ("mp4a", "aac"))]
    return _largest(aac) or _largest(audios)


def video_qualities(formats: list[dict], duration: int | None) -> list[dict]:
    videos = [f for f in formats if _has_video(f) and _res(f)]
    if not videos:
        return []
    audios = [f for f in formats if _has_audio(f) and not _has_video(f)]
    best_audio = _expected_audio(audios)

    resolutions = sorted({_res(f) for f in videos})
    max_res = resolutions[-1]

    result = []
    for target in RES_TARGETS:
        if target != RES_TARGETS[-1] and max_res < target * 0.9:
            continue
        eligible = [r for r in resolutions if r <= target]
        chosen = max(eligible) if eligible else min(resolutions)
        tier = [f for f in videos if _res(f) == chosen]
        best_video = _expected_video(tier)

        video_bytes = _estimate_bytes(best_video, duration)
        audio_bytes = 0 if _has_audio(best_video) else _estimate_bytes(best_audio, duration)
        size = None if video_bytes is None or audio_bytes is None else video_bytes + audio_bytes

        has_60 = any((f.get("fps") or 0) >= 50 for f in tier)
        result.append(
            {
                "id": str(target),
                "label": f"{target}p",
                "sub": {2160: "4K", 1080: "Full HD", 720: "HD", 480: "SD"}[target],
                "size_bytes": size,
                "fps": [60, 30] if has_60 else [],
                "note": None,
            }
        )

    recommended = next((q for q in result if q["id"] == str(RECOMMENDED_VIDEO)), result[0])
    recommended["note"] = "Recomendado"
    return result


def audio_qualities(formats: list[dict], duration: int | None) -> list[dict]:
    names = {320: "Máxima", 192: "Alta", 128: "Ligera"}
    result = []
    for kbps in AUDIO_TARGETS:
        size = int(kbps * 1000 / 8 * duration) if duration else None
        result.append(
            {
                "id": str(kbps),
                "label": f"{kbps} kbps",
                "sub": names[kbps],
                "size_bytes": size,
                "fps": [],
                "note": "Recomendado" if kbps == RECOMMENDED_AUDIO else None,
            }
        )
    return result


def _fixed_playlist_qualities() -> list[dict]:
    result = []
    for target in RES_TARGETS:
        result.append(
            {
                "id": str(target),
                "label": f"{target}p",
                "sub": {2160: "4K", 1080: "Full HD", 720: "HD", 480: "SD"}[target],
                "size_bytes": None,
                "fps": [60, 30] if target >= 1080 else [],
                "note": "Recomendado" if target == RECOMMENDED_VIDEO else None,
            }
        )
    return result


def _thumbnail(info: dict) -> str | None:
    if info.get("thumbnail"):
        return info["thumbnail"]
    thumbs = [t for t in (info.get("thumbnails") or []) if t.get("url")]
    return thumbs[-1]["url"] if thumbs else None


def _entry(raw: dict) -> dict:
    return {
        "url": raw.get("url") or raw.get("webpage_url"),
        "title": raw.get("title") or "Sin título",
        "duration": int(raw["duration"]) if raw.get("duration") else None,
    }


def analyze(url: str, cookies_path: Path | None = None) -> dict:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "playlistend": 200,
        "socket_timeout": 20,
        **browser_request_opts(url),
    }
    if cookies_path:
        opts["cookiefile"] = str(cookies_path)

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    platform = platforms.from_extractor(info.get("extractor_key"), url)
    is_playlist = info.get("_type") == "playlist"

    if is_playlist:
        entries = [_entry(e) for e in (info.get("entries") or []) if e and (e.get("url") or e.get("webpage_url"))]
        return {
            "url": url,
            "platform": platform,
            "title": info.get("title") or "Playlist",
            "uploader": info.get("uploader") or info.get("channel"),
            "duration": None,
            "thumbnail": _thumbnail(info),
            "is_playlist": True,
            "entries": entries,
            "audio_only": False,
            "video_qualities": _fixed_playlist_qualities(),
            "audio_qualities": audio_qualities([], None),
        }

    formats = info.get("formats") or []
    duration = int(info["duration"]) if info.get("duration") else None
    videos = video_qualities(formats, duration)
    audio_only = not videos and any(_has_audio(f) for f in formats)
    if not videos and not audio_only:
        videos = _fixed_playlist_qualities()

    return {
        "url": url,
        "platform": platform,
        "title": info.get("title") or "Sin título",
        "uploader": info.get("uploader") or info.get("channel"),
        "duration": duration,
        "thumbnail": _thumbnail(info),
        "is_playlist": False,
        "entries": [],
        "audio_only": audio_only,
        "video_qualities": videos,
        "audio_qualities": audio_qualities(formats, duration),
    }
