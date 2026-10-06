from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app import auth
from app.models import utcnow
from app.schemas import LoginRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response):
    settings = request.app.state.settings
    limiter: auth.LoginLimiter = request.app.state.login_limiter
    client = request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "unknown")

    if limiter.blocked(client):
        raise HTTPException(status_code=429, detail="Demasiados intentos, espera unos minutos")

    invite_id = None
    max_age = auth.COOKIE_MAX_AGE
    if not auth.token_matches(body.token, settings.api_token):
        engine = request.app.state.engine
        invite = auth.find_invite_by_token(engine, body.token)
        if invite is None:
            limiter.register_failure(client)
            raise HTTPException(status_code=401, detail="Token incorrecto o expirado")
        invite_id = invite.id
        max_age = max(1, int((invite.expires_at.replace(tzinfo=None) - utcnow()).total_seconds()))
        auth.touch_invite(engine, invite.id)

    limiter.reset(client)
    response.set_cookie(
        auth.COOKIE_NAME,
        auth.make_session_cookie(settings.secret_key, invite_id),
        max_age=max_age,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        path="/",
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(auth.COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", dependencies=[Depends(auth.require_auth)])
def me(request: Request):
    return {"ok": True, "role": auth.authorize(request)}
