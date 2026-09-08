"""Session store — Postgres-backed via SQLAlchemy.

Public interface preserved:
    new_session() -> str
    ensure(session_id) -> str
    touch(session_id)
    append_turn(session_id, user_message, response, safety_route, intent_module,
                safety_json=None, intent_json=None, critic_json=None, timing_ms_json=None) -> str
    get_session(session_id) -> dict | None
    get_history(session_id) -> list[dict]
    delete(session_id) -> bool
    size() -> int

KVKK — saklama süresi kullanıcının kayıtlı olup olmamasına göre değişiyor:

- Anonim oturumlar: user_message geçici. _gc_expired() TTL dolan oturumları
  siliyor (varsayılan 1 saat), turn'ler cascade ile gidiyor. Turn satırında
  retention_ends_at doluyor.

- Kayıtlı kullanıcı oturumları: kullanıcı silene kadar duruyor. Geçmiş
  özelliği bunu gerektiriyor — bir saatte silinen sohbetin listelenecek hâli
  yok. Bu satırlarda retention_ends_at None kalıyor ve _gc_expired() onlara
  dokunmuyor. Silme yolları: DELETE /auth/sessions/{id} (tek sohbet),
  DELETE /auth/me (hesap ve bağlı her şey).

- user_hash her iki durumda da tutuluyor; user_message temizlense bile
  denetim ve tekrar tespiti için gerekli.

Bu ayrım /gizlilik sayfasında da anlatılıyor; biri değişirse diğeri de
değişmeli.
"""

from __future__ import annotations

import hashlib
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, func as sqlfunc, delete as sql_delete

from api.db import get_sessionmaker
from api.db.models import ChatSession, Turn


_HASH_SALT = os.environ.get("CBT_HASH_SALT", "cbt-mvp-salt-change-me")


def _hash_message(msg: str) -> str:
    return hashlib.sha256((msg + _HASH_SALT).encode("utf-8")).hexdigest()[:16]


def _now() -> datetime:
    return datetime.now(timezone.utc)
def _as_utc(dt: datetime) -> datetime:
    """SQLite naive datetime döndürebiliyor — karşılaştırma öncesi normalize et."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


# İki mesaj arasında bu kadar boşluk varsa yeni bir "oturuş" başlamış
# sayılıyor: seans yayı sıfırlanır, kullanıcı yeni bir sohbete girer.
SITTING_GAP_SECONDS = 6 * 3600


class DbSessionStore:
    """Postgres/SQLite-backed session store."""

    def __init__(self, ttl_seconds: int = 3600):
        self._ttl = ttl_seconds

    def _SessionLocal(self):
        return get_sessionmaker()

    # --------------------------------------------------------
    # Basic session lifecycle
    # --------------------------------------------------------

    def new_session(self) -> str:
        SessionLocal = self._SessionLocal()
        with SessionLocal() as s, s.begin():
            row = ChatSession()
            s.add(row)
            s.flush()
            sid = str(row.id)
        return sid

    def touch(self, session_id: str) -> None:
        SessionLocal = self._SessionLocal()
        with SessionLocal() as s, s.begin():
            row = s.get(ChatSession, uuid.UUID(session_id))
            if row is not None:
                row.last_active = _now()

    def ensure(self, session_id: Optional[str]) -> str:
        if session_id:
            try:
                _ = uuid.UUID(session_id)
            except (ValueError, TypeError):
                return self.new_session()
            SessionLocal = self._SessionLocal()
            with SessionLocal() as s, s.begin():
                row = s.get(ChatSession, uuid.UUID(session_id))
                if row is None:
                    row = ChatSession(id=uuid.UUID(session_id))
                    s.add(row)
                row.last_active = _now()
            return session_id
        return self.new_session()

    # --------------------------------------------------------
    # Turns
    # --------------------------------------------------------

    def append_turn(
        self,
        session_id: str,
        user_message: str,
        response: str,
        safety_route: str,
        intent_module: str,
        *,
        safety_json: dict | None = None,
        intent_json: dict | None = None,
        critic_json: dict | None = None,
        timing_ms_json: dict | None = None,
        boundary_state: str | None = None,
        model_version: str | None = None,
        retrieved_card_ids: list | None = None,
    ) -> str:
        SessionLocal = self._SessionLocal()
        with SessionLocal() as s, s.begin():
            # Ensure session exists
            sid_uuid = uuid.UUID(session_id)
            sess = s.get(ChatSession, sid_uuid)
            if sess is None:
                sess = ChatSession(id=sid_uuid)
                s.add(sess)
            sess.last_active = _now()

            turn = Turn(
                session_id=sid_uuid,
                user_hash=_hash_message(user_message),
                user_message=user_message,
                response=response,
                safety_route=safety_route,
                intent_module=intent_module,
                safety_json=safety_json,
                intent_json=intent_json,
                critic_json=critic_json,
                timing_ms_json=timing_ms_json,
                retention_ends_at=None if sess.user_id else _now() + timedelta(seconds=self._ttl),
                model_version=model_version,
                boundary_state=boundary_state,
                retrieved_card_ids=retrieved_card_ids,


            )
            s.add(turn)
            s.flush()
            tid = str(turn.id)
        self._gc_expired()
        return tid

    def get_session(self, session_id: str) -> Optional[dict]:
        try:
            sid_uuid = uuid.UUID(session_id)
        except (ValueError, TypeError):
            return None
        SessionLocal = self._SessionLocal()
        with SessionLocal() as s:
            row = s.get(ChatSession, sid_uuid)
            if row is None:
                return None
            turns = [
                {
                    "turn_id": str(t.id),
                    "ts": t.ts.timestamp() if t.ts else 0,
                    "user_hash": t.user_hash,
                    "user_message": t.user_message,
                    "response": t.response,
                    "safety_route": t.safety_route,
                    "intent_module": t.intent_module,
                }
                for t in row.turns
            ]
            return {
                "session_id": str(row.id),
                "created_at": row.created_at.timestamp() if row.created_at else 0,
                "last_active": row.last_active.timestamp() if row.last_active else 0,
                "turns": turns,
            }

    def get_history(self, session_id: str,limit:int=60 ) -> list[dict]:
        try:
            sid_uuid = uuid.UUID(session_id)
        except (ValueError, TypeError):
            return []
        SessionLocal = self._SessionLocal()
        with SessionLocal() as s:
            # Son `limit` turu kronolojik sırada döndür. Sıralamayı ters
            # çevirmek yerine sayıp kaydırıyoruz: ts kolonu SQLite'ta saniye
            # çözünürlüğünde ve aynı saniyedeki turlar eşit damga alıyor —
            # desc() böyle durumlarda ekleme sırasını bozuyor.
            total = s.execute(
                select(sqlfunc.count(Turn.id)).where(Turn.session_id == sid_uuid)
            ).scalar_one()
            rows = s.execute(
                select(Turn)
                .where(Turn.session_id == sid_uuid)
                .order_by(Turn.ts.asc())
                .offset(max(0, total - limit))
                .limit(limit)
            ).scalars().all()
            return [
                {"user_message": r.user_message or "", "response": r.response}
                for r in rows
            ]
    
    def sitting_turn_count(self, session_id: str, gap_seconds: int = SITTING_GAP_SECONDS) -> int:
        try:
            sid_uuid = uuid.UUID(session_id)
        except (ValueError, TypeError):
            return 0

        SessionLocal = self._SessionLocal()
        with SessionLocal() as s:
            stamps = s.execute(
                select(Turn.ts).where(Turn.session_id == sid_uuid).order_by(Turn.ts.asc())
            ).scalars().all()

        count = 0
        prev = None
        for ts in stamps:
            ts = _as_utc(ts)
            if prev is not None and (ts - prev).total_seconds() > gap_seconds:
                count = 0
            count += 1
            prev = ts

        if prev is not None and (_now() - prev).total_seconds() > gap_seconds:
            count = 0
        return count
    def delete(self, session_id: str) -> bool:
        try:
            sid_uuid = uuid.UUID(session_id)
        except (ValueError, TypeError):
            return False
        SessionLocal = self._SessionLocal()
        with SessionLocal() as s, s.begin():
            row = s.get(ChatSession, sid_uuid)
            if row is None:
                return False
            s.delete(row)  # cascade removes turns + feedback
        return True

    def size(self) -> int:
        SessionLocal = self._SessionLocal()
        with SessionLocal() as s:
            return s.execute(select(sqlfunc.count(ChatSession.id))).scalar_one()

    # --------------------------------------------------------
    # GC — remove expired sessions on best-effort basis
    # --------------------------------------------------------

    def _gc_expired(self) -> None:
        cutoff = _now() - timedelta(seconds=self._ttl)
        SessionLocal = self._SessionLocal()
        with SessionLocal() as s, s.begin():
            s.execute(sql_delete(ChatSession).where(ChatSession.last_active < cutoff,
                      ChatSession.user_id.is_(None),
                      )
            )
                        
     # only delete sessions with no user attached


    def attach_user(self, session_id: str, user_id: uuid.UUID) -> None:
        factory = self._SessionLocal()
        try:
            sid_uuid = uuid.UUID(session_id)
        except (ValueError, TypeError):
            return
        with factory() as s, s.begin():
            row = s.get(ChatSession, sid_uuid)
            if row is not None and row.user_id is None:
                row.user_id = user_id


# ============================================================
# Module-level singleton
# ============================================================

_STORE: Optional[DbSessionStore] = None


def get_store() -> DbSessionStore:
    global _STORE
    if _STORE is None:
        ttl = int(os.environ.get("CBT_SESSION_TTL_SECONDS", "3600"))
        _STORE = DbSessionStore(ttl_seconds=ttl)
    return _STORE


# Legacy attribute for imports written as `from api.session import session_store`
session_store = get_store()


# Backward-compat: some tests import InMemorySessionStore. Alias to Db.
InMemorySessionStore = DbSessionStore
