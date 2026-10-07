from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app import auth
from app.models import Invite, utcnow

router = APIRouter(prefix="/api/invites", tags=["invites"], dependencies=[Depends(auth.require_admin)])


class InviteCreate(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    days: float = Field(default=7, gt=0, le=365)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() + "Z" if value else None


def _out(invite: Invite, secret_key: str) -> dict:
    return {
        "token": auth.reveal_invite_token(invite, secret_key),
        "id": invite.id,
        "label": invite.label,
        "created_at": _iso(invite.created_at),
        "expires_at": _iso(invite.expires_at),
        "last_used_at": _iso(invite.last_used_at),
        "active": auth.invite_is_active(invite),
        "revoked": invite.revoked,
    }


@router.post("", status_code=201)
def create(body: InviteCreate, request: Request):
    secret_key = request.app.state.settings.secret_key
    invite, _ = auth.create_invite(request.app.state.engine, secret_key, body.label.strip(), body.days)
    return _out(invite, secret_key)


@router.get("")
def list_invites(request: Request):
    with Session(request.app.state.engine) as session:
        invites = session.exec(
            select(Invite).where(Invite.deleted == False).order_by(Invite.created_at.desc())  # noqa: E712
        ).all()
    secret_key = request.app.state.settings.secret_key
    return [_out(invite, secret_key) for invite in invites]


@router.delete("/{invite_id}", status_code=204)
def revoke(invite_id: str, request: Request):
    with Session(request.app.state.engine) as session:
        invite = session.get(Invite, invite_id)
        if invite is None:
            raise HTTPException(status_code=404, detail="Invitación no encontrada")
        invite.revoked = True
        session.add(invite)
        session.commit()


@router.delete("/{invite_id}/purge", status_code=204)
def delete(invite_id: str, request: Request):
    """Quita de la lista una invitación ya revocada o expirada."""
    with Session(request.app.state.engine) as session:
        invite = session.get(Invite, invite_id)
        if invite is None or invite.deleted:
            raise HTTPException(status_code=404, detail="Invitación no encontrada")
        if auth.invite_is_active(invite):
            raise HTTPException(status_code=409, detail="Revócala antes de borrarla")
        invite.deleted = True
        session.add(invite)
        session.commit()


@router.delete("", status_code=200)
def delete_inactive(request: Request):
    """Quita de la lista todas las invitaciones revocadas o expiradas."""
    with Session(request.app.state.engine) as session:
        invites = session.exec(select(Invite).where(Invite.deleted == False)).all()  # noqa: E712
        targets = [invite for invite in invites if not auth.invite_is_active(invite)]
        for invite in targets:
            invite.deleted = True
            session.add(invite)
        session.commit()
    return {"removed": len(targets)}
