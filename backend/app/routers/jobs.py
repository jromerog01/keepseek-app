from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from app.auth import require_auth
from app.models import Job, utcnow
from app.routers.deps import checked_url, get_manager
from app.schemas import JobCreate, JobOut, QuickRequest
from app.services import formats
from app.services.job_manager import JobManager

router = APIRouter(prefix="/api", tags=["jobs"], dependencies=[Depends(require_auth)])


def _out(request: Request, job: Job) -> JobOut:
    return JobOut.from_job(job, request.app.state.settings.file_ttl_hours)


def _get_or_404(manager: JobManager, job_id: str) -> Job:
    try:
        return manager.get(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Descarga no encontrada")


@router.post("/jobs", status_code=201)
def create_jobs(body: JobCreate, request: Request, manager: JobManager = Depends(get_manager)):
    try:
        formats.validate_options(body.mode, body.quality, body.fps, body.format)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    now = utcnow()
    common = dict(
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
    return [_out(request, job) for job in jobs]


@router.post("/quick", status_code=201)
def quick(body: QuickRequest, request: Request, manager: JobManager = Depends(get_manager)):
    options = formats.quick_options()
    if body.mode == "audio":
        options = {"mode": "audio", "quality": "320", "fps": None, "fmt": "MP3"}
    job = manager.create(
        url=checked_url(request, body.url),
        mode=options["mode"],
        quality=options["quality"],
        fps=options["fps"],
        fmt=options["fmt"],
        source="shortcut",
    )
    return _out(request, job)


@router.get("/jobs")
def list_jobs(request: Request, manager: JobManager = Depends(get_manager)):
    return [_out(request, job) for job in manager.all_jobs()]


@router.post("/jobs/pause-all")
def pause_all(manager: JobManager = Depends(get_manager)):
    manager.pause_all()
    return {"ok": True}


@router.post("/jobs/resume-all")
def resume_all(manager: JobManager = Depends(get_manager)):
    manager.resume_all()
    return {"ok": True}


@router.delete("/jobs")
def clear_finished(status: str = Query("done"), manager: JobManager = Depends(get_manager)):
    if status != "done":
        raise HTTPException(status_code=422, detail="Solo se admite status=done")
    return {"removed": manager.clear_finished()}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request, manager: JobManager = Depends(get_manager)):
    return _out(request, _get_or_404(manager, job_id))


@router.get("/jobs/{job_id}/wait")
def wait_job(
    job_id: str,
    request: Request,
    timeout: float = Query(50, ge=1, le=90),
    manager: JobManager = Depends(get_manager),
):
    _get_or_404(manager, job_id)
    try:
        job = manager.wait(job_id, timeout)
    except KeyError:
        raise HTTPException(status_code=404, detail="Descarga no encontrada")
    return _out(request, job)


@router.post("/jobs/{job_id}/pause")
def pause_job(job_id: str, request: Request, manager: JobManager = Depends(get_manager)):
    _get_or_404(manager, job_id)
    return _out(request, manager.pause(job_id))


@router.post("/jobs/{job_id}/resume")
def resume_job(job_id: str, request: Request, manager: JobManager = Depends(get_manager)):
    _get_or_404(manager, job_id)
    return _out(request, manager.resume(job_id))


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str, manager: JobManager = Depends(get_manager)):
    _get_or_404(manager, job_id)
    manager.cancel(job_id)


@router.get("/jobs/{job_id}/file")
def download_file(job_id: str, manager: JobManager = Depends(get_manager)):
    job = _get_or_404(manager, job_id)
    if job.status == "expired":
        raise HTTPException(status_code=410, detail="El archivo ya expiró")
    path = manager.file_path(job)
    if path is None:
        raise HTTPException(status_code=409, detail="La descarga todavía no termina")
    return FileResponse(path, filename=path.name)
