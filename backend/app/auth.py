import base64
import hashlib
import secrets
import time
from datetime import timedelta
from collections import defaultdict, deque

from cryptography.fernet import Fernet, InvalidToken
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


def _fernet(secret_key: str) -> Fernet:
    digest = hashlib.sha256(("clipo-invite-tokens:" + secret_key).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def reveal_invite_token(invite: Invite, secret_key: str) -> str | None:
    """Token en claro, o None si es una invitación vieja o cambió SECRET_KEY."""
    if not invite.token_enc:
        return None
    try:
        return _fernet(secret_key).decrypt(invite.token_enc.encode()).decode()
    except InvalidToken:
        return None


def create_invite(engine, secret_key: str, label: str, days: float) -> tuple[Invite, str]:
    token = "clipo-" + secrets.token_urlsafe(12)
    invite = Invite(
        id=secrets.token_hex(6),
        label=label,
        token_hash=hash_invite_token(token),
        token_enc=_fernet(secret_key).encrypt(token.encode()).decode(),
        expires_at=utcnow() + timedelta(days=days),
    )
    with Session(engine) as session:
        session.add(invite)
        session.commit()
        session.refresh(invite)
    return invite, token


def invite_is_active(invite: Invite | None) -> bool:
    if invite is None or invite.revoked or invite.deleted:
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


def _header_invite(request: Request) -> Invite | None:
    """Invitación activa enviada en X-API-Key (el Atajo de un invitado). Se resuelve una vez por petición."""
    if not hasattr(request.state, "header_invite"):
        token = request.headers.get("x-api-key")
        invite = find_invite_by_token(request.app.state.engine, token) if token else None
        if invite:
            touch_invite(request.app.state.engine, invite.id)
        request.state.header_invite = invite
    return request.state.header_invite


def authorize(request: Request) -> str | None:
    """Devuelve 'admin' o 'guest' si la petición está autorizada, si no None."""
    state = request.app.state
    if token_matches(request.headers.get("x-api-key"), state.settings.api_token):
        return "admin"
    if request.headers.get("x-api-key"):
        return "guest" if _header_invite(request) else None
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
    if request.headers.get("x-api-key"):
        invite = _header_invite(request)
        if invite is None:
            raise HTTPException(status_code=401, detail="No autorizado")
        return invite.id
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
