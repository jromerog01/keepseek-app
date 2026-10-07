from fastapi import HTTPException, Request

from app import auth
from app.models import Job

from app.services.job_manager import JobManager
from app.services.urls import InvalidUrl, validate_url


def get_manager(request: Request) -> JobManager:
    return request.app.state.manager


def checked_url(request: Request, raw: str) -> str:
    settings = request.app.state.settings
    try:
        return validate_url(raw, allow_private=settings.allow_private_urls)
    except InvalidUrl as exc:
        raise HTTPException(status_code=400, detail=str(exc))


def visible_owner(request: Request) -> str | None:
    """Admin ve todo (None); un invitado solo lo que descargó con su invitación."""
    owner = auth.current_owner(request)
    return None if owner == auth.OWNER_ADMIN else owner


def visible_job(request: Request, job_id: str) -> Job:
    """Descarga solicitada; si no existe o es de otro dueño, responde 404 igual."""
    try:
        job = get_manager(request).get(job_id)
    except KeyError:
        job = None
    owner = visible_owner(request)
    if job is None or (owner is not None and job.owner != owner):
        raise HTTPException(status_code=404, detail="Descarga no encontrada")
    return job
