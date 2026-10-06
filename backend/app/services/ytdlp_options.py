from importlib.util import find_spec
from urllib.parse import urlparse

from yt_dlp.utils import std_headers

try:
    from yt_dlp.networking.impersonate import ImpersonateTarget
except ImportError:  # pragma: no cover - compatibilidad con yt-dlp viejo
    ImpersonateTarget = None


def _origin(url: str) -> str | None:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}/"


def browser_request_opts(url: str) -> dict:
    headers = {
        **std_headers,
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        "Upgrade-Insecure-Requests": "1",
    }
    referer = _origin(url)
    if referer:
        headers["Referer"] = referer

    opts = {"http_headers": headers}
    if ImpersonateTarget is not None and find_spec("curl_cffi") is not None:
        opts["impersonate"] = ImpersonateTarget.from_str("chrome")
    return opts
