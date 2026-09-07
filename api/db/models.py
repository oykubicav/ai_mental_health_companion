"""SQLAlchemy 2.0 ORM models.

Schema:
  users              — future auth, mostly empty at MVP
  consent_records    — KVKK audit trail (accept ts + policy version)
  sessions           — chat sessions; user_id nullable (anon allowed)
  turns              — one row per user↔assistant exchange
  feedback           — thumbs_up / down / flag on a specific turn

KVKK notes on turns.user_message:
- Nullable text column. Stored EPHEMERALLY for multi-turn context.
- retention_ends_at column signals when a purge job should NULL it out.
- Session TTL (~1h default) is the practical purge trigger — expired
  sessions cascade-delete their turns.
- Permanent audit id = turns.user_hash (sha256).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, TypeDecorator, CHAR


# ============================================================
# UUID column that works on both Postgres and SQLite
# ============================================================

class GUID(TypeDecorator):
    """Portable UUID: uses Postgres UUID when available, CHAR(36) elsewhere."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PgUUID
            return dialect.type_descriptor(PgUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value if dialect.name == "postgresql" else str(value)
        try:
            return uuid.UUID(str(value)) if dialect.name == "postgresql" else str(uuid.UUID(str(value)))
        except (ValueError, AttributeError):
            return None

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


# ============================================================
# JSON column that works everywhere (JSONB on PG, TEXT on SQLite)
# ============================================================

class PortableJSON(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


# ============================================================
# Base
# ============================================================

class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# ============================================================
# users — future magic link auth
# ============================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_token: Mapped[str | None] = mapped_column(String(64), nullable=True)   # verify link için
    reset_token: Mapped[str | None] = mapped_column(String(64), nullable=True)          # password reset link için
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Onboarding tercihleri. Cihazda değil hesapta duruyor: localStorage'daki
    # hali cihaz değişince kayboluyor ve çıkış-giriş döngüsünde siliniyordu.
    display_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    focus_topics: Mapped[list | None] = mapped_column(PortableJSON, nullable=True)
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Seçilen konular karşılamada yalnızca bir kez anılır. Cihazda tutulunca
    # her çıkış-giriş sıfırlanıyor ve aynı cümle tekrar tekrar kuruluyordu.
    focus_greeted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # none | some | ongoing — bir uzmanla görüşen kullanıcıya Neva'nın
    # tamamlayıcı olduğunu hatırlatmak için.
    therapy_experience: Mapped[str | None] = mapped_column(String(16), nullable=True)

    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        cascade="all, delete-orphan"
    )




# ============================================================
# consent_records — KVKK audit
# ============================================================

class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    policy_version: Mapped[str] = mapped_column(String(16), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


# ============================================================
# sessions
# ============================================================

class ChatSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    consent_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("consent_records.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User | None] = relationship(back_populates="sessions")
    turns: Mapped[list["Turn"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="Turn.ts"
    )


# ============================================================
# turns
# ============================================================

class Turn(Base):
    __tablename__ = "turns"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_message: Mapped[str | None] = mapped_column(Text, nullable=True)  # ephemeral
    response: Mapped[str] = mapped_column(Text, nullable=False)
    safety_route: Mapped[str] = mapped_column(String(64), nullable=False)
    intent_module: Mapped[str] = mapped_column(String(32), nullable=False)
    safety_json: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    intent_json: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    critic_json: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    timing_ms_json: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    retention_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # AI Act transparency — hangi model + boundary state
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    boundary_state: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Retrieved cards (transparency panel için)
    retrieved_card_ids: Mapped[list | None] = mapped_column(PortableJSON, nullable=True)

    session: Mapped["ChatSession"] = relationship(back_populates="turns")
    feedback_items: Mapped[list["Feedback"]] = relationship(
        back_populates="turn", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_turns_session_id", "session_id"),
        Index("idx_turns_ts", "ts"),
    )


# ============================================================
# feedback
# ============================================================

class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    turn_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("turns.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    turn: Mapped["Turn"] = relationship(back_populates="feedback_items")

    __table_args__ = (
        Index("idx_feedback_turn_id", "turn_id"),
        Index("idx_feedback_verdict", "verdict"),
    )


# ============================================================
# user_profiles — longitudinal structured memory
# ============================================================
# Anon-friendly: session_id ile bağlı, user_id opsiyonel (auth geldiğinde
# merge edilir). Session CASCADE'i profili de siler (KVKK unutulma hakkı).
#
# Design intent:
# - triggers: kullanıcının belirttiği somut tetikleyiciler ("iş toplantısı",
#   "annemle görüşme")
# - themes: tekrarlayan psikolojik temalar ("yalnızlık", "kontrolsüzlük")
# - coping_tried: dict {"technique_id": "yararlı"|"yararsız"|"denenmedi"}
# - modules_engaged: konuşmada geçen modüller
# - progress_notes: klinisyen-tarzı ilerleme özeti (Haiku üretir)
# - last_summary: composer'a inject edilen kısa özet (200-400 char)

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True,
    )

    turn_count: Mapped[int] = mapped_column(default=0, nullable=False)
    triggers: Mapped[list | None] = mapped_column(PortableJSON, nullable=True)
    themes: Mapped[list | None] = mapped_column(PortableJSON, nullable=True)
    coping_tried: Mapped[dict | None] = mapped_column(PortableJSON, nullable=True)
    modules_engaged: Mapped[list | None] = mapped_column(PortableJSON, nullable=True)
    progress_notes: Mapped[list | None] = mapped_column(PortableJSON, nullable=True)
    last_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_user_profiles_session_id", "session_id"),
    )

# ============================================================
# assessments — PHQ-9 / GAD-7 clinical measurement
# ============================================================
# Kanıta dayalı outcome tracking. Kullanıcı opt-in.
# PHQ-9: Kroenke 2001 — 9 madde, 0-27, thresholds 5/10/15/20
# GAD-7: Spitzer 2006 — 7 madde, 0-21, thresholds 5/10/15
#
# suicide_flag: PHQ-9 item 9 > 0 ise True. Klinik acil dikkat sinyali,
# total puan hafif olsa bile.
#
# KVKK: session cascade delete profil gibi burayı da temizler.

class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True,
    )
    kind: Mapped[str] = mapped_column(String(8), nullable=False)  # "phq9" | "gad7"
    answers: Mapped[list] = mapped_column(PortableJSON, nullable=False)
    total_score: Mapped[int] = mapped_column(nullable=False)
    severity: Mapped[str] = mapped_column(String(24), nullable=False)
    suicide_flag: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    __table_args__ = (
        Index("idx_assessments_session_id", "session_id"),
        Index("idx_assessments_kind", "kind"),
        Index("idx_assessments_taken_at", "taken_at"),
    )
class ExerciseEntry(Base):
    """Egzersiz sayfasındaki araçlarda kullanıcının yazdıkları.

    Yalnızca hesabı olanlar için; anonim kullanıcı aracı kullanır ama
    kayıt tutulmaz. Sohbetle aynı saklama kuralı: kullanıcı silene kadar.
    Bu tablo LLM'e gitmez.
    """
    __tablename__ = "exercise_entries"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # thought_record | small_step | breathing
    payload: Mapped[dict] = mapped_column(PortableJSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    __table_args__ = (
        Index("idx_exercise_entries_user_created", "user_id", "created_at"),
    )


class JournalEntry(Base):
    """Günlük — kullanıcının kendi tuttuğu gün kaydı.

    Gün başına tek kayıt (user_id + entry_date benzersiz); aynı güne
    tekrar yazmak üstüne yazar, yeni satır açmaz. Tarihi istemci
    gönderiyor çünkü "bugün" kullanıcının saat diliminde belirleniyor;
    sunucu UTC'ye göre karar verirse gece yazanlar bir sonraki güne düşer.

    Sohbetten bağımsız: LLM'e gitmez, profil çıkarımına girmez.
    """
    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
    )
    entry_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    mood: Mapped[int | None] = mapped_column(nullable=True)          # 1-5
    did: Mapped[str | None] = mapped_column(Text, nullable=True)      # bugün ne yaptım
    thoughts: Mapped[str | None] = mapped_column(Text, nullable=True)  # aklımdan ne geçti
    good: Mapped[str | None] = mapped_column(Text, nullable=True)     # iyi gelen bir şey
    tags: Mapped[list | None] = mapped_column(PortableJSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "entry_date", name="uq_journal_user_date"),
        Index("idx_journal_user_date", "user_id", "entry_date"),
    )


class RefreshToken(Base):
    """Oturum başına bir satır. Ham token saklanmıyor, SHA-256 hash'i tutuluyor —
    veritabanı sızarsa oturumlar ele geçirilemesin.

    Rotasyon: her yenilemede eski satır revoked_at ile kapanır, replaced_by
    yenisini gösterir. Bu zincir sayesinde iptal edilmiş bir token tekrar
    kullanılırsa (çalıntı demektir) kullanıcının tüm oturumları düşürülebilir.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), nullable=True)

    # Kullanıcıya "hangi cihazlar açık" gösterebilmek için. Ham UA saklanmıyor,
    # kısaltılmış hali yeterli.
    user_agent: Mapped[str | None] = mapped_column(String(200), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_refresh_tokens_user_id", "user_id"),
        Index("idx_refresh_tokens_hash", "token_hash"),
    )