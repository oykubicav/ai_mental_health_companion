"""Egzersiz araçlarının kayıtları — /exercises.

Araçlar (nefes, düşünce kaydı, küçük adım) tarayıcıda çalışır ve LLM
çağırmaz. Burası yalnızca hesabı olan kullanıcının yazdıklarını saklar;
anonim istek 401 alır, araç yine çalışır ama kayıt tutulmaz.

Routes:
  POST   /exercises            — kayıt ekle
  GET    /exercises?kind=      — kullanıcının kayıtları (yeniden eskiye)
  DELETE /exercises/{id}       — tek kayıt sil
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.auth.dependencies import get_current_user
from api.db.models import ExerciseEntry, User
from api.deps import session_store_dep
from api.session import InMemorySessionStore

router = APIRouter(prefix="/exercises", tags=["exercises"])

KINDS = {"thought_record", "small_step", "breathing"}
MAX_PAYLOAD_CHARS = 6000


class ExerciseCreate(BaseModel):
    kind: str = Field(..., pattern="^(thought_record|small_step|breathing)$")
    payload: dict[str, Any]


class ExerciseView(BaseModel):
    id: str
    kind: str
    payload: dict[str, Any]
    created_at: str


class ExerciseList(BaseModel):
    entries: list[ExerciseView]


def _view(row: ExerciseEntry) -> ExerciseView:
    return ExerciseView(
        id=str(row.id),
        kind=row.kind,
        payload=row.payload,
        created_at=row.created_at.isoformat(),
    )


def _payload_size(payload: dict[str, Any]) -> int:
    return sum(len(str(k)) + len(str(v)) for k, v in payload.items())


@router.post("", response_model=ExerciseView, status_code=201)
async def create_entry(
    req: ExerciseCreate,
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    if _payload_size(req.payload) > MAX_PAYLOAD_CHARS:
        raise HTTPException(status_code=413, detail="Kayıt çok uzun")

    factory = store._SessionLocal()
    with factory() as db, db.begin():
        row = ExerciseEntry(user_id=user.id, kind=req.kind, payload=req.payload)
        db.add(row)
        db.flush()
        db.refresh(row)
        view = _view(row)
    return view


@router.get("", response_model=ExerciseList)
async def list_entries(
    kind: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    factory = store._SessionLocal()
    with factory() as db:
        q = select(ExerciseEntry).where(ExerciseEntry.user_id == user.id)
        if kind:
            q = q.where(ExerciseEntry.kind == kind)
        rows = db.execute(
            q.order_by(ExerciseEntry.created_at.desc(), ExerciseEntry.id.desc()).limit(limit)
        ).scalars().all()
        return ExerciseList(entries=[_view(r) for r in rows])


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: str,
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    try:
        eid = uuid.UUID(entry_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı")

    factory = store._SessionLocal()
    with factory() as db, db.begin():
        row = db.get(ExerciseEntry, eid)
        # Başkasının kaydı da "yok" görünür; varlığını sızdırmayalım.
        if row is None or row.user_id != user.id:
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı")
        db.delete(row)
    return {"status": "deleted"}
