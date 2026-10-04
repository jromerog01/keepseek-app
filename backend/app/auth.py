import secrets
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

COOKIE_NAME = "clipo_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365
_SALT = "clipo-session"


def _serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt=_SALT)


def token_matches(candidate: str | None, expected: str) -> bool:
    if not candidate or not expected:
        return False
    return secrets.compare_digest(candidate.encode(), expected.encode())


def make_session_cookie(secret_key: str) -> str:
    return _serializer(secret_key).dumps({"ok": True})


def cookie_is_valid(value: str | None, secret_key: str) -> bool:
    if not value:
        return False
    try:
        _serializer(secret_key).loads(value, max_age=COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return False
    return True


def require_auth(request: Request) -> None:
    settings = request.app.state.settings
    if token_matches(request.headers.get("x-api-key"), settings.api_token):
        return
    if cookie_is_valid(request.cookies.get(COOKIE_NAME), settings.secret_key):
        return
    raise HTTPException(status_code=401, detail="No autorizado")


class LoginLimiter:
    """Bloquea intentos de login por fuerza bruta: 10 fallos cada 10 minutos."""

    def __init__(self, max_failures: int = 10, window_seconds: int = 600):
        self._max = max_failures
        self._window = window_seconds
        self._failures: dict[str, deque] = defaultdict(deque)

    def _prune(self, key: str) -> deque:
        failures = self._failures[key]
        while failures and time.monotonic() - failures[0] > self._window:
            failures.popleft()
        return failures

    def blocked(self, key: str) -> bool:
        return len(self._prune(key)) >= self._max

    def register_failure(self, key: str) -> None:
        self._prune(key).append(time.monotonic())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
