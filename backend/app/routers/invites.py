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


def _out(invite: Invite) -> dict:
    return {
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
    invite, token = auth.create_invite(request.app.state.engine, body.label.strip(), body.days)
    # El token solo se muestra aquí; en la base solo queda su hash.
    return {**_out(invite), "token": token}


@router.get("")
def list_invites(request: Request):
    with Session(request.app.state.engine) as session:
        invites = session.exec(select(Invite).order_by(Invite.created_at.desc())).all()
    return [_out(invite) for invite in invites]


@router.delete("/{invite_id}", status_code=204)
def revoke(invite_id: str, request: Request):
    with Session(request.app.state.engine) as session:
        invite = session.get(Invite, invite_id)
        if invite is None:
            raise HTTPException(status_code=404, detail="Invitación no encontrada")
        invite.revoked = True
        session.add(invite)
        session.commit()
