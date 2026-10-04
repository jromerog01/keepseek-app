import re

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_PREFIX = re.compile(r"^(ERROR:\s*)?(\[[^\]]+\]\s*[^:\s]*:\s*)?")


def clean_error(exc: BaseException) -> str:
    text = _ANSI.sub("", str(exc)).strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    last = lines[-1] if lines else exc.__class__.__name__
    last = _PREFIX.sub("", last).strip() or last
    return last[:300]
