import re

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_PREFIX = re.compile(r"^(ERROR:\s*)?(\[[^\]]+\]\s*[^:\s]*:\s*)?")


def clean_error(exc: BaseException) -> str:
    text = _ANSI.sub("", str(exc)).strip()
    if "HTTP Error 403" in text or "Forbidden" in text:
        return "El sitio bloqueó la solicitud (403). Si el video abre en tu navegador, actualiza cookies.txt en el servidor e intenta otra vez."
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    last = lines[-1] if lines else exc.__class__.__name__
    last = _PREFIX.sub("", last).strip() or last
    return last[:300]
