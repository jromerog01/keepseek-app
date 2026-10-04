from pathlib import Path

VIDEO_QUALITIES = ("2160", "1080", "720", "480")
AUDIO_QUALITIES = ("320", "192", "128")
VIDEO_FORMATS = ("MP4", "WEBM", "MKV")
AUDIO_FORMATS = ("MP3", "M4A", "OPUS")
FPS_VALUES = (30, 60)

_AUDIO_CODECS = {"MP3": "mp3", "M4A": "m4a", "OPUS": "opus"}


def validate_options(mode: str, quality: str, fps: int | None, fmt: str) -> None:
    if mode == "video":
        if quality not in VIDEO_QUALITIES:
            raise ValueError(f"Calidad de video no válida: {quality}")
        if fmt not in VIDEO_FORMATS:
            raise ValueError(f"Formato de video no válido: {fmt}")
        if fps is not None and fps not in FPS_VALUES:
            raise ValueError(f"Fotogramas no válidos: {fps}")
    elif mode == "audio":
        if quality not in AUDIO_QUALITIES:
            raise ValueError(f"Calidad de audio no válida: {quality}")
        if fmt not in AUDIO_FORMATS:
            raise ValueError(f"Formato de audio no válido: {fmt}")
        if fps is not None:
            raise ValueError("El audio no usa fotogramas")
    else:
        raise ValueError(f"Modo no válido: {mode}")


def spec_label(mode: str, quality: str, fps: int | None, fmt: str) -> str:
    if mode == "audio":
        return f"{quality} kbps · {fmt}"
    resolution = f"{quality}p"
    if fps:
        resolution += f" {fps} fps"
    return f"{resolution} · {fmt}"


def build_ydl_opts(
    *,
    mode: str,
    quality: str,
    fps: int | None,
    fmt: str,
    out_dir: Path,
    cookies_path: Path | None = None,
) -> dict:
    validate_options(mode, quality, fps, fmt)

    opts: dict = {
        "outtmpl": str(out_dir / "%(title).90B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "playlist_items": "1",
        "continuedl": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "windowsfilenames": True,
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 30,
        "concurrent_fragment_downloads": 4,
    }
    if cookies_path:
        opts["cookiefile"] = str(cookies_path)

    if mode == "audio":
        opts["format"] = "ba/b"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": _AUDIO_CODECS[fmt],
                "preferredquality": quality,
            }
        ]
        return opts

    sort = [f"res:{quality}"]
    if fps:
        sort.append(f"fps:{fps}")
    if fmt == "MP4":
        sort += ["vcodec:h264", "acodec:m4a"]
    elif fmt == "WEBM":
        sort += ["vcodec:vp9", "acodec:opus"]

    opts["format"] = "bv*+ba/b"
    opts["format_sort"] = sort
    opts["merge_output_format"] = fmt.lower()
    return opts


def quick_options() -> dict:
    return {"mode": "video", "quality": "1080", "fps": None, "fmt": "MP4"}
