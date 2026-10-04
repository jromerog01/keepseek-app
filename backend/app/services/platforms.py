import re

OTHER = {"id": "other", "name": "Otros", "mono": "+"}

_PLATFORMS = [
    ({"id": "youtube", "name": "YouTube", "mono": "YT"}, re.compile(r"youtu\.?be")),
    ({"id": "instagram", "name": "Instagram", "mono": "IG"}, re.compile(r"instagram|instagr\.am")),
    ({"id": "facebook", "name": "Facebook", "mono": "FB"}, re.compile(r"facebook|fb\.watch")),
    ({"id": "tiktok", "name": "TikTok", "mono": "TT"}, re.compile(r"tiktok")),
    ({"id": "x", "name": "X", "mono": "X"}, re.compile(r"(^|//|\.)(x|twitter)\.com")),
    ({"id": "vimeo", "name": "Vimeo", "mono": "VI"}, re.compile(r"vimeo")),
    ({"id": "reddit", "name": "Reddit", "mono": "RD"}, re.compile(r"reddit|redd\.it")),
    ({"id": "soundcloud", "name": "SoundCloud", "mono": "SC"}, re.compile(r"soundcloud")),
]

_EXTRACTOR_PREFIXES = {
    "youtube": "youtube",
    "instagram": "instagram",
    "facebook": "facebook",
    "tiktok": "tiktok",
    "twitter": "x",
    "vimeo": "vimeo",
    "reddit": "reddit",
    "soundcloud": "soundcloud",
}


def from_url(url: str) -> dict:
    lowered = url.lower()
    for platform, pattern in _PLATFORMS:
        if pattern.search(lowered):
            return dict(platform)
    return dict(OTHER)


def from_extractor(extractor_key: str | None, url: str) -> dict:
    key = (extractor_key or "").lower()
    for prefix, platform_id in _EXTRACTOR_PREFIXES.items():
        if key.startswith(prefix):
            return next(dict(p) for p, _ in _PLATFORMS if p["id"] == platform_id)
    return from_url(url)
