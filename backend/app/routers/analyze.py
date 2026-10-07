from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import require_auth
from app.routers.deps import checked_url
from app.schemas import AnalyzeRequest
from app.services import analyzer
from app.services.errors import clean_error

router = APIRouter(prefix="/api", tags=["analyze"], dependencies=[Depends(require_auth)])


@router.post("/analyze")
def analyze(body: AnalyzeRequest, request: Request):
    url = checked_url(request, body.url)
    settings = request.app.state.settings
    try:
        return analyzer.analyze(url, cookies_path=settings.cookies_path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=clean_error(exc))


def _size_label(size_bytes: int | None) -> str:
    if not size_bytes:
        return ""
    mb = size_bytes / 1_000_000
    return f" · ~{mb / 1000:.1f} GB" if mb >= 1000 else f" · ~{mb:.0f} MB"


@router.post("/quick/options")
def quick_options(body: AnalyzeRequest, request: Request):
    """Calidades reales del video, como texto listo para un menú del Atajo."""
    info = analyze(body, request)
    options = [f"{q['id']}p · {q['sub']}{_size_label(q['size_bytes'])}" for q in info["video_qualities"]]
    options.append("MP3 · solo audio")
    return {"title": info["title"], "options": options}
