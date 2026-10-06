import logging
import subprocess
import tempfile
from pathlib import Path

import requests

from app.services.urls import InvalidUrl, validate_url

log = logging.getLogger("clipo")

MAX_BYTES = 3_000_000
FETCH_TIMEOUT = 10
FFMPEG_TIMEOUT = 30
WIDTH = 480
USER_AGENT = "Mozilla/5.0 (compatible; Clipo/1.0)"


class ThumbnailStore:
    """Miniaturas JPEG guardadas en disco, una por job."""

    def __init__(self, directory: Path):
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)

    def path(self, job_id: str) -> Path:
        return self._dir / f"{job_id}.jpg"

    def has(self, job_id: str) -> bool:
        return self.path(job_id).is_file()

    def delete(self, job_id: str) -> None:
        self.path(job_id).unlink(missing_ok=True)

    def ids(self) -> set[str]:
        return {p.stem for p in self._dir.glob("*.jpg")}

    def directory(self) -> Path:
        return self._dir


def _to_jpeg(source: Path, dest: Path, seek: float | None = None) -> bool:
    """Reduce la imagen o el fotograma a un JPEG de 480 px de ancho. Escribe a un temporal y renombra."""
    temp = dest.with_name(dest.stem + ".tmp.jpg")
    command = ["ffmpeg", "-y", "-v", "error"]
    if seek:
        command += ["-ss", f"{seek:.2f}"]
    command += ["-i", str(source), "-frames:v", "1", "-vf", f"scale='min({WIDTH},iw)':-2", "-q:v", "4", str(temp)]
    try:
        subprocess.run(command, capture_output=True, check=True, timeout=FFMPEG_TIMEOUT)
        if not temp.is_file() or temp.stat().st_size == 0:
            return False
        temp.replace(dest)
        return True
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        temp.unlink(missing_ok=True)


def fetch_remote(url: str, dest: Path, allow_private: bool = False) -> bool:
    """Descarga la miniatura que publica el sitio. Devuelve False ante cualquier problema."""
    try:
        validate_url(url, allow_private=allow_private)
        with requests.get(url, stream=True, timeout=FETCH_TIMEOUT, headers={"User-Agent": USER_AGENT}) as response:
            response.raise_for_status()
            declared = int(response.headers.get("Content-Length") or 0)
            if declared > MAX_BYTES:
                return False
            data = bytearray()
            for chunk in response.iter_content(65536):
                data += chunk
                if len(data) > MAX_BYTES:
                    return False
    except (InvalidUrl, requests.RequestException, ValueError, OSError) as exc:
        log.info("Sin miniatura remota (%s): %s", url[:80], exc)
        return False

    with tempfile.NamedTemporaryFile(dir=dest.parent, suffix=".src", delete=False) as source:
        source.write(data)
    try:
        return _to_jpeg(Path(source.name), dest)
    finally:
        Path(source.name).unlink(missing_ok=True)


def from_video(video: Path, dest: Path, duration: float | None = None) -> bool:
    """Saca un fotograma del propio video (a ~10 % de la duración, máximo 5 s)."""
    seek = min(max((duration or 0) * 0.1, 1.0), 5.0)
    return _to_jpeg(video, dest, seek=seek) or _to_jpeg(video, dest)
