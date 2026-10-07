import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.auth import require_auth
from sqlmodel import Session, select

from app.models import Invite, Job, utcnow
from app import auth
from app.routers.deps import checked_url, get_manager, visible_job, visible_owner
from app.schemas import JobCreate, JobOut, QuickRequest
from app.services import formats
from app.services.devices import device_label
from app.services.job_manager import JobManager

router = APIRouter(prefix="/api", tags=["jobs"], dependencies=[Depends(require_auth)])


ADMIN_LABEL = "Token original"


def _owner_labels(request: Request, jobs: list[Job]) -> dict[str, str]:
    """Nombre de cada invitación dueña de alguna descarga (también las revocadas)."""
    ids = {job.owner for job in jobs} - {auth.OWNER_ADMIN}
    labels = {auth.OWNER_ADMIN: ADMIN_LABEL}
    if ids:
        with Session(request.app.state.engine) as session:
            invites = session.exec(select(Invite).where(Invite.id.in_(ids))).all()
        labels.update({invite.id: invite.label for invite in invites})
    return labels


def _out(request: Request, job: Job, labels: dict[str, str] | None = None) -> JobOut:
    state = request.app.state
    manager = state.manager
    labels = labels if labels is not None else _owner_labels(request, [job])
    return JobOut.from_job(
        job,
        state.settings.file_ttl_hours,
        manager.stages_for(job.id),
        manager.has_thumbnail(job.id),
        labels.get(job.owner, "Invitación eliminada"),
    )


def _device(request: Request) -> str | None:
    return device_label(request.headers.get("x-device-name"), request.headers.get("user-agent"))


@router.post("/jobs", status_code=201)
def create_jobs(body: JobCreate, request: Request, manager: JobManager = Depends(get_manager)):
    try:
        formats.validate_options(body.mode, body.quality, body.fps, body.format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    now = utcnow()
    common = dict(
        owner=auth.current_owner(request),
        device=_device(request),
        mode=body.mode,
        quality=body.quality,
        fps=body.fps,
        fmt=body.format,
        uploader=body.uploader,
        thumbnail=body.thumbnail,
        created_at=now,
    )

    if body.items:
        jobs = [
            manager.create(
                url=checked_url(request, item.url),
                title=item.title,
                duration=item.duration,
                **common,
            )
            for item in body.items
        ]
    else:
        jobs = [
            manager.create(
                url=checked_url(request, body.url),
                title=body.title,
                duration=body.duration,
                size_estimate=body.size_estimate,
                **common,
            )
        ]
    labels = _owner_labels(request, jobs)
    return [_out(request, job, labels) for job in jobs]


@router.post("/quick", status_code=201)
def quick(body: QuickRequest, request: Request, manager: JobManager = Depends(get_manager)):
    options = formats.quick_options()
    choice = (body.quality or "").strip()
    if body.mode == "audio" or choice.upper().startswith("MP3"):
        options = {"mode": "audio", "quality": "320", "fps": None, "fmt": "MP3"}
    elif choice:
        options["quality"] = re.match(r"\d*", choice).group() or choice
    try:
        formats.validate_options(options["mode"], options["quality"], options["fps"], options["fmt"])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    job = manager.create(
        url=checked_url(request, body.url),
        mode=options["mode"],
        quality=options["quality"],
        fps=options["fps"],
        fmt=options["fmt"],
        source="shortcut",
        owner=auth.current_owner(request),
        device=_device(request),
    )
    return _out(request, job)


@router.get("/jobs")
def list_jobs(request: Request, manager: JobManager = Depends(get_manager)):
    jobs = manager.all_jobs(visible_owner(request))
    labels = _owner_labels(request, jobs)
    return [_out(request, job, labels) for job in jobs]


@router.post("/jobs/pause-all")
def pause_all(request: Request, manager: JobManager = Depends(get_manager)):
    manager.pause_all(visible_owner(request))
    return {"ok": True}


@router.post("/jobs/resume-all")
def resume_all(request: Request, manager: JobManager = Depends(get_manager)):
    manager.resume_all(visible_owner(request))
    return {"ok": True}


@router.delete("/jobs")
def clear_finished(request: Request, status: str = Query("done"), manager: JobManager = Depends(get_manager)):
    if status != "done":
        raise HTTPException(status_code=422, detail="Solo se admite status=done")
    return {"removed": manager.clear_finished(visible_owner(request))}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request):
    return _out(request, visible_job(request, job_id))


@router.get("/jobs/{job_id}/wait")
def wait_job(
    job_id: str,
    request: Request,
    timeout: float = Query(50, ge=1, le=90),
    manager: JobManager = Depends(get_manager),
):
    visible_job(request, job_id)
    try:
        job = manager.wait(job_id, timeout)
    except KeyError:
        raise HTTPException(status_code=404, detail="Descarga no encontrada")
    return _out(request, job)


@router.post("/jobs/{job_id}/pause")
def pause_job(job_id: str, request: Request, manager: JobManager = Depends(get_manager)):
    visible_job(request, job_id)
    return _out(request, manager.pause(job_id))


@router.post("/jobs/{job_id}/resume")
def resume_job(job_id: str, request: Request, manager: JobManager = Depends(get_manager)):
    visible_job(request, job_id)
    return _out(request, manager.resume(job_id))


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str, request: Request, manager: JobManager = Depends(get_manager)):
    visible_job(request, job_id)
    manager.cancel(job_id)


@router.get("/jobs/{job_id}/thumbnail")
def job_thumbnail(job_id: str, request: Request, manager: JobManager = Depends(get_manager)):
    visible_job(request, job_id)
    path = manager.thumbnail_path(job_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Este video no tiene miniatura")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


@router.get("/jobs/{job_id}/file")
def download_file(job_id: str, request: Request, manager: JobManager = Depends(get_manager)):
    job = visible_job(request, job_id)
    if job.status == "expired":
        raise HTTPException(status_code=410, detail="El archivo ya expiró")
    path = manager.file_path(job)
    if path is None:
        raise HTTPException(status_code=409, detail="La descarga todavía no termina")
    return FileResponse(path, filename=path.name)
