import re

MAX_LEN = 60

_DEVICES = (
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Android", "Android"),
    ("Windows", "Windows"),
    ("CrOS", "Chromebook"),
    ("Macintosh", "Mac"),
    ("Linux", "Linux"),
)

# El orden importa: Edge y Opera también dicen "Chrome", y Chrome también dice "Safari"
_BROWSERS = (
    ("EdgiOS", "Edge"), ("Edg/", "Edge"),
    ("OPR/", "Opera"),
    ("FxiOS", "Firefox"), ("Firefox/", "Firefox"),
    ("CriOS", "Chrome"), ("Chrome/", "Chrome"),
    ("Safari/", "Safari"),
)


def _clean(name: str) -> str:
    return re.sub(r"[\x00-\x1f\x7f]+", " ", name).strip()[:MAX_LEN]


def device_label(header_name: str | None, user_agent: str | None) -> str | None:
    """Nombre que envía el cliente (el Atajo puede mandar el real) o uno deducido del navegador."""
    if header_name and (name := _clean(header_name)):
        return name
    ua = user_agent or ""
    if ua.startswith(("Shortcuts", "BackgroundShortcutRunner", "WorkflowKit")):
        return "Atajo de iOS"
    device = next((label for key, label in _DEVICES if key in ua), None)
    if device is None:
        return None
    browser = next((label for key, label in _BROWSERS if key in ua), None)
    return f"{device} · {browser}" if browser else device
