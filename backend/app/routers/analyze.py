from fastapi import APIRouter, Depends, HTTPException, Request
from yt_dlp.utils import DownloadError, ExtractorError

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
    except (DownloadError, ExtractorError) as exc:
        raise HTTPException(status_code=422, detail=clean_error(exc))
