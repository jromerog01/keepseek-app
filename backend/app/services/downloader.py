import logging
import subprocess
from pathlib import Path

from yt_dlp import YoutubeDL

from app.config import Settings
from app.models import Job
from app.services import compat, formats, platforms
from app.services.job_manager import Reporter

log = logging.getLogger("clipo")

_TEMPORARY_SUFFIXES = {".part", ".ytdl", ".temp"}


def _stream_kind(info: dict) -> str:
    has_video = info.get("vcodec") not in (None, "none")
    has_audio = info.get("acodec") not in (None, "none")
    if has_video and not has_audio:
        return "video"
    if has_audio and not has_video:
        return "audio"
    return "both"


def _find_output(out_dir: Path, info: dict | None) -> Path:
    for item in (info or {}).get("requested_downloads") or []:
        candidate = Path(item.get("filepath") or "")
        if candidate.is_file():
            return candidate

    files = [p for p in out_dir.iterdir() if p.is_file() and p.suffix not in _TEMPORARY_SUFFIXES]
    if not files:
        raise RuntimeError("yt-dlp terminó pero no generó ningún archivo")
    return max(files, key=lambda p: p.stat().st_size)


def ytdlp_download(job: Job, out_dir: Path, reporter: Reporter, *, settings: Settings) -> Path:
    opts = formats.build_ydl_opts(
        mode=job.mode,
        quality=job.quality,
        fps=job.fps,
        fmt=job.format,
        out_dir=out_dir,
        cookies_path=settings.cookies_path,
    )

    def on_progress(data: dict) -> None:
        reporter.check()
        info = data.get("info_dict") or {}
        reporter.meta(
            title=info.get("title"),
            uploader=info.get("uploader") or info.get("channel"),
            platform=platforms.from_extractor(info.get("extractor_key"), job.url),
        )
        key = data.get("filename") or info.get("format_id") or "stream"
        kind = _stream_kind(info)
        if data["status"] == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            reporter.stream(key, kind, data.get("downloaded_bytes"), total, data.get("speed"))
        elif data["status"] == "finished":
            reporter.stream_done(key, kind, data.get("total_bytes") or data.get("downloaded_bytes"))

    def on_postprocess(data: dict) -> None:
        reporter.check()
        name = data.get("postprocessor", "")
        key = "merge" if name == "Merger" else "convert" if "ExtractAudio" in name else None
        if key is None:
            return
        if data["status"] == "started":
            reporter.stage("Uniendo audio y video" if key == "merge" else "Convirtiendo", 90 if key == "merge" else 85, key=key)
        elif data["status"] == "finished":
            reporter.stage_done(key)

    opts["progress_hooks"] = [on_progress]
    opts["postprocessor_hooks"] = [on_postprocess]

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(job.url, download=True)

    path = _find_output(out_dir, info)
    if job.mode == "video" and job.format == "MP4":
        _make_photos_compatible(path, reporter)
    return path


def _make_photos_compatible(path: Path, reporter: Reporter) -> None:
    try:
        verdict = compat.check(path)
        if verdict.ok:
            return
        reporter.begin_conversion()
        compat.fix(path, verdict, on_progress=reporter.conversion_progress)
        reporter.stage_done("convert_ios")
    except (OSError, subprocess.SubprocessError, ValueError):
        log.exception("No se pudo comprobar o convertir %s; se entrega tal cual", path.name)
