"""Transparency endpoint — AI Act traceability.

GET /transparency/{turn_id}
Kullanıcı ya da klinisyen: bu cevap nasıl üretildi?

KVKK: user_message SHOW EDİLMEZ (ephemeral, TTL sonrası purged).
Sadece user_hash + response + trace döner.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.db.models import Turn
from api.deps import session_store_dep
from api.session import InMemorySessionStore

router = APIRouter(prefix="/transparency", tags=["transparency"])

class TransparencyView(BaseModel):
    turn_id: str
    session_id: str
    timestamp: str
    response: str
    model_version: Optional[str]
    boundary_state: Optional[str]
    retrieved_card_ids: Optional[list]
    safety: Optional[dict]
    # intent bloğu conversation_state ve process_card_ids alanlarını da
    # taşıyor — cevabın "nasıl" yazıldığını belirleyen süreç katmanı.
    intent: Optional[dict]
    critic: Optional[dict]
    timing_ms: Optional[dict]

@router.get("/{turn_id}", response_model=TransparencyView)
async def get_transparency(
    turn_id: str,
    store: InMemorySessionStore = Depends(session_store_dep),
):
    # 1. Gelen turn_id'nin geçerli bir UUID olup olmadığını kontrol ediyoruz
    try:
        turn_uuid = uuid.UUID(turn_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid turn_id")

    session_local = store._SessionLocal()
    with session_local() as db:
        # 2. Veritabanından kaydı çekiyoruz
        row = db.get(Turn, turn_uuid)
        
        # 3. Kayıt yoksa db.get() None döneceği için 404 hatası veriyoruz
        if not row:
            raise HTTPException(status_code=404, detail="Turn not found")

        # 4. Kayıt bulunduysa veriyi dönüyoruz (Girintiler düzeltildi)
        return TransparencyView(
            turn_id=str(row.id),
            session_id=str(row.session_id),
            timestamp=row.ts.isoformat(),
            response=row.response,
            model_version=row.model_version,
            boundary_state=row.boundary_state,
            retrieved_card_ids=row.retrieved_card_ids,
            safety=row.safety_json,
            intent=row.intent_json,
            critic=row.critic_json,
            timing_ms=row.timing_ms_json
        )


    








