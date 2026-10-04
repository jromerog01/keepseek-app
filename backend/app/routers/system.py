import shutil
import subprocess
from functools import lru_cache

from fastapi import APIRouter, Depends, Request
from yt_dlp.version import __version__ as ytdlp_version

from app.auth import require_auth
from app.routers.deps import get_manager
from app.services.job_manager import JobManager

router = APIRouter(prefix="/api", tags=["system"])


_VERSION_FLAG = {"ffmpeg": "-version"}


@lru_cache
def _tool_version(binary: str) -> str | None:
    if not shutil.which(binary):
        return None
    flag = _VERSION_FLAG.get(binary, "--version")
    try:
        out = subprocess.run([binary, flag], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    first_line = out.splitlines()[0] if out else ""
    return first_line.strip() or None


@router.get("/health")
def health(manager: JobManager = Depends(get_manager)):
    return {"ok": True, "active_jobs": manager.active_count()}


@router.get("/system", dependencies=[Depends(require_auth)])
def system(request: Request, manager: JobManager = Depends(get_manager)):
    return {
        "ytdlp_version": ytdlp_version,
        "ffmpeg": _tool_version("ffmpeg"),
        "deno": _tool_version("deno"),
        "active_jobs": manager.active_count(),
        "file_ttl_hours": request.app.state.settings.file_ttl_hours,
    }
