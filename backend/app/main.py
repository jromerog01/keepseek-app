import asyncio
import logging
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.auth import LoginLimiter
from app.config import Settings, get_settings
from app.db import make_engine
from app.routers import analyze, auth, jobs, system
from app.services.downloader import ytdlp_download
from app.services.job_manager import Downloader, JobManager
from app.services.thumbnails import ThumbnailStore

log = logging.getLogger("clipo")

CLEANUP_EVERY_SECONDS = 600
NO_CACHE_FILES = {"index.html", "sw.js", "registerSW.js", "manifest.webmanifest"}


def create_app(settings: Settings | None = None, downloader: Downloader | None = None) -> FastAPI:
    settings = settings or get_settings()
    if not settings.api_token or not settings.secret_key:
        raise RuntimeError("Faltan API_TOKEN y SECRET_KEY en el entorno (.env)")

    manager = JobManager(
        engine=make_engine(settings.db_path),
        downloads_dir=settings.downloads_dir,
        downloader=downloader or partial(ytdlp_download, settings=settings),
        max_concurrent=settings.max_concurrent,
        file_ttl_hours=settings.file_ttl_hours,
        history_days=settings.history_days,
        thumbnails=ThumbnailStore(settings.data_dir / "thumbs"),
        allow_private_urls=settings.allow_private_urls,
    )

    async def cleanup_loop() -> None:
        while True:
            await asyncio.sleep(CLEANUP_EVERY_SECONDS)
            try:
                await asyncio.to_thread(manager.cleanup)
            except Exception:
                log.exception("Falló la limpieza periódica")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        manager.start()
        task = asyncio.create_task(cleanup_loop())
        yield
        task.cancel()
        await asyncio.to_thread(manager.shutdown)

    app = FastAPI(title="Clipo", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.manager = manager
    app.state.login_limiter = LoginLimiter()

    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(analyze.router)
    app.include_router(jobs.router)

    _mount_frontend(app, settings.static_dir)
    return app


def _mount_frontend(app: FastAPI, static_dir: Path) -> None:
    if not static_dir.is_dir():
        return
    root = static_dir.resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)

        candidate = (root / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(root):
            target = candidate
        else:
            target = root / "index.html"

        if target.name in NO_CACHE_FILES:
            cache = "no-cache"
        elif "assets" in target.relative_to(root).parts:
            cache = "public, max-age=31536000, immutable"
        else:
            cache = "public, max-age=3600"
        return FileResponse(target, headers={"Cache-Control": cache})
