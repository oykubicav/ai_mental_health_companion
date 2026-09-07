"""Günlük — /journal.

Kullanıcının her gün doldurabildiği kısa kayıt: ruh hali, ne yaptı,
aklından ne geçti, iyi gelen bir şey. Gün başına tek satır; aynı güne
tekrar yazmak üstüne yazar.

Sohbetten bağımsız çalışır ve yapay zekâya gönderilmez. Hesap gerektirir:
anonim oturumda saklanacak yer yok.

Routes:
  PUT    /journal/{entry_date}   — o günü yaz ya da güncelle
  GET    /journal/{entry_date}   — tek gün
  GET    /journal                — son kayıtlar (yeniden eskiye)
  DELETE /journal/{entry_date}   — o günü sil
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from api.auth.dependencies import get_current_user
from api.db.models import JournalEntry, User
from api.deps import session_store_dep
from api.session import InMemorySessionStore

router = APIRouter(prefix="/journal", tags=["journal"])

MAX_FIELD = 2000
MAX_TAGS = 6

# Gün kartındaki hızlı etiketler. Serbest metin yazmak istemeyen ya da
# vakti olmayan kullanıcı yalnızca bunlara dokunup çıkabilsin diye var.
TAG_IDS = {
    "uyku_iyi", "uyku_kotu", "hareket", "disari_ciktim", "insanlarla",
    "yalniz_kaldim", "is_yogun", "dinlendim", "kaygi", "huzun", "ofke", "umut",
}


class JournalUpsert(BaseModel):
    mood: Optional[int] = Field(None, ge=1, le=5)
    did: Optional[str] = Field(None, max_length=MAX_FIELD)
    thoughts: Optional[str] = Field(None, max_length=MAX_FIELD)
    good: Optional[str] = Field(None, max_length=MAX_FIELD)
    tags: Optional[list[str]] = Field(None, max_length=MAX_TAGS)


class JournalView(BaseModel):
    entry_date: str
    mood: Optional[int] = None
    did: Optional[str] = None
    thoughts: Optional[str] = None
    good: Optional[str] = None
    tags: list[str] = []
    updated_at: str


class JournalList(BaseModel):
    entries: list[JournalView]


def _view(row: JournalEntry) -> JournalView:
    return JournalView(
        entry_date=row.entry_date.isoformat(),
        mood=row.mood,
        did=row.did,
        thoughts=row.thoughts,
        good=row.good,
        tags=row.tags or [],
        updated_at=row.updated_at.isoformat() if row.updated_at else "",
    )


def _parse_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise HTTPException(status_code=422, detail="Tarih YYYY-AA-GG olmalı")


def _temiz(deger: Optional[str]) -> Optional[str]:
    if deger is None:
        return None
    kirpik = deger.strip()
    return kirpik[:MAX_FIELD] or None


@router.put("/{entry_date}", response_model=JournalView)
async def upsert_entry(
    entry_date: str,
    req: JournalUpsert,
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """O günü yazar. Kayıt varsa gönderilen alanları günceller.

    Gelecek bir tarihe yazılamaz — günlük olan biteni tutuyor, plan değil.
    """
    gun = _parse_date(entry_date)
    if gun > datetime.utcnow().date():
        raise HTTPException(status_code=422, detail="İleri bir tarihe yazamazsın")

    factory = store._SessionLocal()
    with factory() as db, db.begin():
        row = db.execute(
            select(JournalEntry).where(
                JournalEntry.user_id == user.id, JournalEntry.entry_date == gun
            )
        ).scalar_one_or_none()

        if row is None:
            row = JournalEntry(user_id=user.id, entry_date=gun)
            db.add(row)

        if req.mood is not None:
            row.mood = req.mood
        if req.did is not None:
            row.did = _temiz(req.did)
        if req.thoughts is not None:
            row.thoughts = _temiz(req.thoughts)
        if req.good is not None:
            row.good = _temiz(req.good)
        if req.tags is not None:
            row.tags = [t for t in req.tags if t in TAG_IDS][:MAX_TAGS]

        db.flush()
        db.refresh(row)
        return _view(row)


@router.get("", response_model=JournalList)
async def list_entries(
    limit: int = Query(30, ge=1, le=120),
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    factory = store._SessionLocal()
    with factory() as db:
        rows = db.execute(
            select(JournalEntry)
            .where(JournalEntry.user_id == user.id)
            .order_by(JournalEntry.entry_date.desc())
            .limit(limit)
        ).scalars().all()
        return JournalList(entries=[_view(r) for r in rows])


@router.get("/{entry_date}", response_model=JournalView)
async def get_entry(
    entry_date: str,
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    gun = _parse_date(entry_date)
    factory = store._SessionLocal()
    with factory() as db:
        row = db.execute(
            select(JournalEntry).where(
                JournalEntry.user_id == user.id, JournalEntry.entry_date == gun
            )
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="O güne ait kayıt yok")
        return _view(row)


@router.delete("/{entry_date}")
async def delete_entry(
    entry_date: str,
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    gun = _parse_date(entry_date)
    factory = store._SessionLocal()
    with factory() as db, db.begin():
        row = db.execute(
            select(JournalEntry).where(
                JournalEntry.user_id == user.id, JournalEntry.entry_date == gun
            )
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="O güne ait kayıt yok")
        db.delete(row)
    return {"status": "deleted"}
