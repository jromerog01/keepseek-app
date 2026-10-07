import hashlib
import secrets
import time
from datetime import timedelta
from collections import defaultdict, deque

from fastapi import HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlmodel import Session, select

from app.models import Invite, utcnow

COOKIE_NAME = "clipo_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365
_SALT = "clipo-session"
OWNER_ADMIN = "admin"


def _serializer(secret_key: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret_key, salt=_SALT)


def token_matches(candidate: str | None, expected: str) -> bool:
    if not candidate or not expected:
        return False
    return secrets.compare_digest(candidate.encode(), expected.encode())


def make_session_cookie(secret_key: str, invite_id: str | None = None) -> str:
    payload = {"ok": True}
    if invite_id:
        payload["inv"] = invite_id
    return _serializer(secret_key).dumps(payload)


def read_session_cookie(value: str | None, secret_key: str) -> dict | None:
    if not value:
        return None
    try:
        data = _serializer(secret_key).loads(value, max_age=COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    return data if isinstance(data, dict) else None


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_invite(engine, label: str, days: float) -> tuple[Invite, str]:
    token = "clipo-" + secrets.token_urlsafe(12)
    invite = Invite(
        id=secrets.token_hex(6),
        label=label,
        token_hash=hash_invite_token(token),
        expires_at=utcnow() + timedelta(days=days),
    )
    with Session(engine) as session:
        session.add(invite)
        session.commit()
        session.refresh(invite)
    return invite, token


def invite_is_active(invite: Invite | None) -> bool:
    if invite is None or invite.revoked:
        return False
    return invite.expires_at.replace(tzinfo=None) > utcnow()


def find_invite_by_token(engine, token: str) -> Invite | None:
    with Session(engine) as session:
        invite = session.exec(select(Invite).where(Invite.token_hash == hash_invite_token(token))).first()
    return invite if invite_is_active(invite) else None


def touch_invite(engine, invite_id: str) -> None:
    with Session(engine) as session:
        invite = session.get(Invite, invite_id)
        if invite:
            invite.last_used_at = utcnow()
            session.add(invite)
            session.commit()


def authorize(request: Request) -> str | None:
    """Devuelve 'admin' o 'guest' si la petición está autorizada, si no None."""
    state = request.app.state
    if token_matches(request.headers.get("x-api-key"), state.settings.api_token):
        return "admin"
    data = read_session_cookie(request.cookies.get(COOKIE_NAME), state.settings.secret_key)
    if data is None:
        return None
    invite_id = data.get("inv")
    if not invite_id:
        return "admin"
    with Session(state.engine) as session:
        invite = session.get(Invite, invite_id)
    return "guest" if invite_is_active(invite) else None


def current_owner(request: Request) -> str:
    """'admin' para el token original; el id de la invitación para una sesión de invitado."""
    state = request.app.state
    if token_matches(request.headers.get("x-api-key"), state.settings.api_token):
        return OWNER_ADMIN
    data = read_session_cookie(request.cookies.get(COOKIE_NAME), state.settings.secret_key)
    return (data or {}).get("inv") or OWNER_ADMIN


def require_auth(request: Request) -> None:
    if authorize(request) is None:
        raise HTTPException(status_code=401, detail="No autorizado")


def require_admin(request: Request) -> None:
    role = authorize(request)
    if role is None:
        raise HTTPException(status_code=401, detail="No autorizado")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Solo el administrador")


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
