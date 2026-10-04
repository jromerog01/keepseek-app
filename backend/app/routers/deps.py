from fastapi import HTTPException, Request

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
