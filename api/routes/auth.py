"""Auth endpoints — email + password, magic verification, JWT tokens.

Endpoints:
  POST   /auth/register        — email + password, verify email yollar
  POST   /auth/verify          — verify token → email_verified=True
  POST   /auth/login           — email + password → JWT
  POST   /auth/forgot-password — email → reset link
  POST   /auth/reset-password  — token + new_password → success
  GET    /auth/me              — current user (auth required)
  DELETE /auth/me              — hesap + cascade delete (auth required)

KVKK: DELETE /me tüm user data'yı cascade siler (sessions, turns, profiles, assessments).
"""
from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Query
from sqlalchemy import select, func as sqlfunc
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from api.auth.dependencies import get_current_user
from api.auth.email import send_verification_email, send_password_reset_email
from api.auth.jwt_utils import encode_token
from api.auth.passwords import hash_password, verify_password
from api.auth import refresh_tokens as rt
from api.auth.cookies import (
    set_refresh_cookie,
    clear_refresh_cookie,
    get_refresh_cookie,
    require_client_header,
)
from api.db.models import User,ChatSession, Turn
from api.deps import session_store_dep
from api.session import InMemorySessionStore

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)

class RegisterRequest(BaseModel):
    email:EmailStr
    password: str = Field(..., min_length=8, max_length=128)
class LoginRequest(BaseModel):
    email:EmailStr
    password: str
class VerifyRequest(BaseModel):
    token:str
class ForgotRequest(BaseModel):
    email:EmailStr
class ResetRequest(BaseModel):
    token:str
    new_password: str = Field(..., min_length=8, max_length=128)
class UserView(BaseModel):
    id:str
    email:str
    email_verified:bool
    created_at: str
    display_name: Optional[str] = None
    focus_topics: list[str] = []
    onboarded_at: Optional[str] = None
    focus_greeted_at: Optional[str] = None
    therapy_experience: Optional[str] = None


class ProfileUpdate(BaseModel):
    """Onboarding ekranından gelen tercihler. Hepsi isteğe bağlı —
    kullanıcı adı boş bırakıp yalnızca konu seçebilir ya da tümünü atlayabilir.

    focus_greeted: karşılamada konular anıldığında bir kez True gönderilir,
    sonraki sohbetlerde aynı cümle kurulmasın diye.
    """
    display_name: Optional[str] = Field(None, max_length=60)
    focus_topics: Optional[list[str]] = Field(None, max_length=10)
    focus_greeted: Optional[bool] = None
    therapy_experience: Optional[str] = None
class TokenResponse(BaseModel):
    access_token:str
    token_type:str = "bearer"
    user: UserView
class RegisterResponse(BaseModel):
    user: UserView
    email_sent: bool
class ResendVerifyRequest(BaseModel):
    email: EmailStr
class SessionSummary(BaseModel):
    session_id: str
    title: str
    created_at: str
    last_active: str
    turn_count: int

class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]
    total: int
class SessionTurnView(BaseModel):
    turn_id: str
    ts: str
    user_message: Optional[str]
    response: str
class SessionDetail(BaseModel):
    session_id: str
    title: str
    created_at: str
    last_active: str
    turns: list[SessionTurnView]

def _session_title(first_message: Optional[str], created_at: datetime) -> str:
    """Başlık ilk kullanıcı mesajından türetiliyor — ayrı bir kolon yok.
    Mesaj silinmişse tarihe düşüyor."""
    if first_message:
        t = " ".join(first_message.split())
        return t[:57] + "…" if len(t) > 60 else t
    return created_at.strftime("%d.%m.%Y") + " sohbeti"
def _iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """Her zaman saat dilimi bilgisiyle döndür.

    SQLite tz bilgisini saklamıyor, Postgres saklıyor. Normalize etmezsek
    aynı alan ortama göre farklı biçimde çıkıyor ve istemci naive değeri
    yerel saat sanabiliyor.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _to_user_view(user: User) -> UserView:
    return UserView(
        id=str(user.id),
        email=user.email,
        email_verified=user.email_verified,
        created_at=_iso_utc(user.created_at),
        display_name=user.display_name,
        focus_topics=user.focus_topics or [],
        onboarded_at=_iso_utc(user.onboarded_at),
        focus_greeted_at=_iso_utc(user.focus_greeted_at),
        therapy_experience=user.therapy_experience,
    )


@router.post("/register", response_model=RegisterResponse)
async def register(
    req: RegisterRequest,
    store: InMemorySessionStore = Depends(session_store_dep),
):
    factory = store._SessionLocal()
    verify_token = secrets.token_urlsafe(32)

    try:
        with factory() as db:
            with db.begin():
                existing = db.query(User).filter_by(email=req.email).one_or_none()
                if existing:
                    raise HTTPException(status_code=409, detail="Bu e-posta zaten kayıtlı")

                user = User(
                    email=req.email,
                    password_hash=hash_password(req.password),
                    email_verified=False,
                    verification_token=verify_token,
                )
                db.add(user)

            db.refresh(user)
            view = _to_user_view(user)

        # DB kapandı — email
        sent = send_verification_email(req.email, verify_token)
        return RegisterResponse(user=view, email_sent=sent)

    except HTTPException:
        raise
    except Exception:
        log.exception("register failed")
        raise HTTPException(status_code=500, detail="Kayıt sırasında bir hata oluştu")
        
@router.post("/verify")
async def verify_email(
    req: VerifyRequest,
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """Verification token → email_verified=True. Idempotent."""
    factory = store._SessionLocal()
    
    with factory() as db:
        # TODO 1: Token ile user bul
        user = db.query(User).filter_by(verification_token=req.token).one_or_none()
        
        # TODO 2: Yoksa 404 "invalid token"
        if not user:
            raise HTTPException(status_code=404, detail="invalid token")
        
        # TODO 3: email_verified=True + verification_token=None (tek kullanımlık)
        try:
            user.email_verified = True
            user.verification_token = None
            db.commit()
        except Exception:
            db.rollback()
            log.exception("email verification failed")
            raise HTTPException(status_code=500, detail="Doğrulama işlemi sırasında bir hata oluştu")
            
        # TODO 4: {"status": "verified"} dön
        return {"status": "verified"}
@router.post("/resend-verify")
async def resend_verify(
    req: ResendVerifyRequest,
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """Verify email kaybolduysa tekrar yolla. Timing-attack koruması için
    var/yok her durumda 200 dön."""
    factory = store._SessionLocal()
    new_token = secrets.token_urlsafe(32)

    with factory() as db:
        with db.begin():
            user = db.query(User).filter_by(email=req.email).one_or_none()
            if user and not user.email_verified:
                user.verification_token = new_token

    # DB dışına çıktıktan sonra email atıyoruz
    if user and not user.email_verified:
        send_verification_email(req.email, new_token)

    return {"status": "ok"}
    



@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    store: InMemorySessionStore = Depends(session_store_dep),
):
    factory = store._SessionLocal()
    with factory() as db, db.begin():
        user = db.query(User).filter_by(email=req.email).one_or_none()
        if not user or not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="E-posta ya da şifre hatalı")
        if user.deleted_at is not None:
            raise HTTPException(status_code=401, detail="E-posta ya da şifre hatalı")
        if not user.email_verified:
            raise HTTPException(
                status_code=403,
                detail="Önce e-posta adresini doğrula. Kayıt sırasında gönderilen linke tıkla.",
            )

        raw_refresh = rt.issue(
            db, user.id, user_agent=request.headers.get("user-agent")
        )
        token = encode_token(user.id)
        view = _to_user_view(user)

    set_refresh_cookie(response, raw_refresh)
    return TokenResponse(access_token=token, user=view)

        
@router.get("/me", response_model=UserView)
async def get_me(
    user: User = Depends(get_current_user),
):
    """Current user info. Auth required (401 if no token)."""
    return _to_user_view(user)

_FOCUS_IDS = {
    "anxiety", "mood", "sleep", "self", "work",
    "relationships", "loss", "change", "panic", "unsure",
}

_THERAPY_EXPERIENCE = {"none", "some", "ongoing"}

# graph/migrate.py'deki TECHNIQUE_PATTERNS ile aynı id'ler. Kullanıcıya
# "thought_record" göstermek anlamsız.
_TECHNIQUE_LABELS = {
    "thought_record": "Düşünce kaydı",
    "cognitive_reframing": "Düşünceyi yeniden değerlendirme",
    "behavioural_activation": "Davranışsal aktivasyon",
    "exposure_gradual": "Kademeli maruz kalma",
    "interoceptive_exposure": "Bedensel duyuma alışma",
    "grounding": "Anı yakalama (grounding)",
    "diaphragm_breathing": "Diyafram nefesi",
    "progressive_muscle_relaxation": "Aşamalı kas gevşetme",
    "worry_time": "Endişe zamanı",
    "problem_solving": "Adım adım problem çözme",
    "self_compassion": "Öz-şefkat",
    "assertiveness": "Sınır koyma ve hayır diyebilme",
    "four_horsemen_antidotes": "İlişkide yıpratıcı kalıpları fark etme",
    "repair_attempt": "Tartışma sonrası onarım",
    "continuing_bonds": "Bağı sürdürme",
    "stimulus_control": "Uyaran kontrolü",
    "sleep_restriction": "Uyku kısıtlaması",
    "sleep_hygiene": "Uyku hijyeni",
    "values_clarification": "Değer haritası",
    "job_crafting": "İşi yeniden şekillendirme",
    "boundary_setting": "Sınır koyma",
    "microbreak": "Mikro molalar",
}
@router.patch("/me/profile", response_model=UserView)
async def update_my_profile(
    req: ProfileUpdate,
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """Onboarding tercihlerini kaydeder ve onboarded_at'i damgalar.

    Boş gövdeyle çağrılması geçerli: kullanıcı adı da konu da vermeden
    "şimdilik geç" dediğinde tekrar sorulmaması için damga yine atılır.
    """
    factory = store._SessionLocal()
    with factory() as db, db.begin():
        row = db.get(User, user.id)
        if row is None:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

        if req.display_name is not None:
            temiz = req.display_name.strip()
            row.display_name = temiz[:60] or None

        if req.focus_topics is not None:
            row.focus_topics = [t for t in req.focus_topics if t in _FOCUS_IDS]

        if req.therapy_experience is not None:
            row.therapy_experience = (
                req.therapy_experience if req.therapy_experience in _THERAPY_EXPERIENCE else None
            )

        # Bir kez damgalanır; sonraki istekler tarihi ileri taşımaz.
        if req.focus_greeted and row.focus_greeted_at is None:
            row.focus_greeted_at = datetime.now(timezone.utc)

        if row.onboarded_at is None:
            row.onboarded_at = datetime.now(timezone.utc)

        db.flush()
        view = _to_user_view(row)

    return view


@router.delete("/me")
async def delete_me(
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """KVKK: hesap + tüm ilgili data (sessions/turns/profiles/assessments) cascade siliniyor."""
    factory = store._SessionLocal()
    with factory() as db, db.begin():
        db.delete(db.get(User, user.id))
    return {"status": "deleted"}


@router.post("/forgot-password")
async def forgot_password(
    req: ForgotRequest,
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """Reset email yolla. Timing-attack koruması için var/yok her durumda 200 dön."""
    factory = store._SessionLocal()

    email_payload: tuple[str, str] | None = None

    with factory() as db:
        user = db.query(User).filter_by(email=req.email).one_or_none()
        if user and user.deleted_at is None:
            reset_token = secrets.token_urlsafe(32)
            reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            try:
                user.reset_token = reset_token
                user.reset_token_expires_at = reset_token_expires_at
                db.commit()
                email_payload = (req.email, reset_token)
            except Exception:
                db.rollback()
                log.exception("forgot-password db update failed")

    if email_payload:
        email, token = email_payload
        send_password_reset_email(email, token)

    return {"status": "ok", "message": "Eğer e-posta kayıtlı ise reset linki gönderildi"}

@router.post("/reset-password")
async def reset_password(
    req: ResetRequest,
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """Token + new_password → success. Token tek kullanımlık, 1 saat geçerli."""
    factory = store._SessionLocal()

    with factory() as db:
        user = db.query(User).filter_by(reset_token=req.token).one_or_none()
        if not user or user.deleted_at is not None:
            raise HTTPException(status_code=404, detail="invalid token")
        # SQLite tz-naive datetime döner; Postgres tz-aware. Karşılaştırma için normalize.
        expires_at = user.reset_token_expires_at
        if not expires_at:
            raise HTTPException(status_code=400, detail="token expired")
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=400, detail="token expired")

        try:
            user.password_hash = hash_password(req.new_password)
            user.reset_token = None
            user.reset_token_expires_at = None
            db.commit()
        except Exception:
            db.rollback()
            log.exception("reset-password db update failed")
            raise HTTPException(status_code=500, detail="Şifre sıfırlama sırasında bir hata oluştu")

    return {"status": "ok", "message": "Şifre başarıyla sıfırlandı"}

@router.get("/sessions", response_model=SessionListResponse)
async def list_my_sessions(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    factory = store._SessionLocal()
    with factory() as db:
        total = db.execute(
            select(sqlfunc.count(ChatSession.id)).where(ChatSession.user_id == user.id)
        ).scalar_one()
        rows= db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user.id)
            .order_by(ChatSession.last_active.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        ids = [s.id for s in rows]
        counts,firsts = {},{}
        if ids:
            counts=dict(db.execute(
                select(Turn.session_id, sqlfunc.count(Turn.id))
                .where(Turn.session_id.in_(ids))
                .group_by(Turn.session_id)
            ).all())
            for sid,msg in db.execute(
                select(Turn.session_id, Turn.user_message)
                .where(Turn.session_id.in_(ids))
                .order_by(Turn.ts.asc())
            ).all():
                firsts.setdefault(sid,msg)
        out =[
            SessionSummary(
                session_id=str(s.id),
                title=_session_title(firsts.get(s.id), s.created_at),
                created_at=s.created_at.isoformat(),
                last_active=s.last_active.isoformat(),
                turn_count=counts.get(s.id, 0),
            )
            for s in rows
            if counts.get(s.id, 0) > 0  # only include sessions with at least one turn
        ]
        return SessionListResponse(sessions=out, total=total)

    



@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_my_session(
    session_id:str,
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    try:
        sid=uuid.UUID(session_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Sohbet bulunamadı")
    factory = store._SessionLocal()
    with factory() as db:
        sess= db.get(ChatSession, sid)
        if sess is None or sess.user_id != user.id:
            raise HTTPException(status_code=404, detail="Sohbet bulunamadı")
        rows = db.execute(
            select(Turn).where(Turn.session_id == sid).order_by(Turn.ts.asc())
        ).scalars().all()
        return SessionDetail(
            session_id=str(sess.id),
            title=_session_title(rows[0].user_message if rows else None, sess.created_at),
            created_at=sess.created_at.isoformat(),
            last_active=sess.last_active.isoformat(),
            turns=[
                SessionTurnView(
                    turn_id=str(t.id),
                    ts=t.ts.isoformat(),
                    user_message=t.user_message,
                    response=t.response,
                )
                for t in rows
            ],
        )
@router.delete("/sessions/{session_id}")
async def delete_my_session(
    session_id: str,
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    try:
        sid = uuid.UUID(session_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Sohbet bulunamadı")

    factory = store._SessionLocal()
    with factory() as db, db.begin():
        sess = db.get(ChatSession, sid)
        if sess is None or sess.user_id != user.id:
            raise HTTPException(status_code=404, detail="Sohbet bulunamadı")
        db.delete(sess)
    return {"status": "deleted"}
    
    

class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserView




    
@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    _: None = Depends(require_client_header),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """Refresh çerezini yeni bir access token'a çevirir ve çerezi döndürür.

    Access token İSTEMİYOR — zaten süresi dolduğu için buraya geliniyor.
    Kimlik doğrulaması tamamen çerezden.
    """
    raw = get_refresh_cookie(request)
    if not raw:
        raise HTTPException(status_code=401, detail="Oturum bulunamadı")

    factory = store._SessionLocal()
    with factory() as db, db.begin():
        sonuc, user_id, yeni_raw = rt.rotate(
            db, raw, user_agent=request.headers.get("user-agent")
        )
        view = None
        access = None
        if sonuc == rt.RefreshOutcome.OK:
            user = db.get(User, user_id)
            if user is None or user.deleted_at is not None:
                sonuc = rt.RefreshOutcome.INVALID
            else:
                access = encode_token(user.id)
                view = _to_user_view(user)

    # Hata dallarını transaction DIŞINDA fırlatıyoruz. İçeride fırlatsaydık
    # rotate()'in REUSE durumunda yaptığı "tüm oturumları kapat" işlemi geri
    # alınırdı — yani güvenlik tepkisi sessizce kaybolurdu.
    if sonuc == rt.RefreshOutcome.RACE:
        # Çerezi SİLMİYORUZ — tarayıcıdaki çerez zaten yenisiyle değişti,
        # silersek çalışan oturumu kendi elimizle koparırız.
        raise HTTPException(status_code=409, detail="Yenileme çakıştı, tekrar dene")

    if sonuc != rt.RefreshOutcome.OK:
        clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Oturum geçersiz")

    set_refresh_cookie(response, yeni_raw)
    return RefreshResponse(access_token=access, user=view)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    _: None = Depends(require_client_header),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """Bu cihazın oturumunu kapatır.

    Access token istemiyor: süresi dolmuş bir kullanıcı da çıkış
    yapabilmeli. Çerez zaten kimliği taşıyor.
    """
    raw = get_refresh_cookie(request)
    if raw:
        factory = store._SessionLocal()
        with factory() as db, db.begin():
            rt.revoke_one(db, raw)

    clear_refresh_cookie(response)
    return {"status": "logged_out"}


@router.post("/logout-all")
async def logout_all(
    response: Response,
    user: User = Depends(get_current_user),
    _: None = Depends(require_client_header),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """Tüm cihazlardan çıkış. Geçerli access token gerektiriyor —
    hesabı ele geçirilen kişinin başvuracağı yer burası."""
    factory = store._SessionLocal()
    with factory() as db, db.begin():
        kapanan = rt.revoke_all_for_user(db, user.id)

    clear_refresh_cookie(response)
    return {"status": "logged_out_all", "sessions_closed": kapanan}


class ThemeCount(BaseModel):
    label: str
    sessions: int


class CopingItem(BaseModel):
    technique: str
    label: str
    verdict: str          # yararlı | yararsız | denenmedi | deneyecek


class Milestone(BaseModel):
    kind: str             # first_session | first_assessment | first_technique | first_helped | first_exercise | first_journal | first_referral
    at: str
    detail: Optional[str] = None


class InsightsResponse(BaseModel):
    themes: list[ThemeCount]
    coping: list[CopingItem]
    triggers: list[str]
    session_count: int
    first_session_at: Optional[str] = None
    milestones: list[Milestone] = []


_REFERRAL_ROUTES = {
    "crisis_referral",
    "medical_emergency_referral",
    "professional_or_emergency_referral",
    "medical_professional_referral",
    "abuse_safety_referral",
    "professional_referral_supportive",
}


def _milestones(db: Session, user_id) -> list[Milestone]:
    """Sayı değil, ilk'ler: ilk konuşma, ilk ölçüm, ilk denenen teknik,
    ilk işe yarayan teknik, ilk uzmana yönlendirme. Sıralı döner.

    Yönlendirme saklanmıyor: kullanıcı o anı da görsün, "her şey
    yolundaydı" resmi çizmek istemiyoruz.
    """
    from api.db.models import Assessment, UserProfile

    out: list[Milestone] = []

    ilk_sohbet = db.execute(
        select(sqlfunc.min(ChatSession.created_at)).where(ChatSession.user_id == user_id)
    ).scalar_one_or_none()
    if ilk_sohbet:
        out.append(Milestone(kind="first_session", at=_iso_utc(ilk_sohbet)))

    ilk_olcum = db.execute(
        select(Assessment.taken_at, Assessment.kind)
        .where(Assessment.user_id == user_id)
        .order_by(Assessment.taken_at.asc())
        .limit(1)
    ).first()
    if ilk_olcum:
        out.append(
            Milestone(kind="first_assessment", at=_iso_utc(ilk_olcum[0]), detail=ilk_olcum[1].upper())
        )

    profiller = db.execute(
        select(UserProfile)
        .join(ChatSession, UserProfile.session_id == ChatSession.id)
        .where(ChatSession.user_id == user_id)
        .order_by(UserProfile.created_at.asc())
    ).scalars().all()
    denenen = None
    yarayan = None
    for pr in profiller:
        for teknik, karar in (pr.coping_tried or {}).items():
            etiket = _TECHNIQUE_LABELS.get(teknik, teknik.replace("_", " "))
            if denenen is None and karar in ("yararlı", "yararsız"):
                denenen = (pr.updated_at or pr.created_at, etiket)
            if yarayan is None and karar == "yararlı":
                yarayan = (pr.updated_at or pr.created_at, etiket)
        if denenen and yarayan:
            break
    if denenen:
        out.append(Milestone(kind="first_technique", at=_iso_utc(denenen[0]), detail=denenen[1]))
    if yarayan:
        out.append(Milestone(kind="first_helped", at=_iso_utc(yarayan[0]), detail=yarayan[1]))

    from api.db.models import ExerciseEntry
    ilk_egzersiz = db.execute(
        select(ExerciseEntry.created_at, ExerciseEntry.kind)
        .where(ExerciseEntry.user_id == user_id)
        .order_by(ExerciseEntry.created_at.asc())
        .limit(1)
    ).first()
    if ilk_egzersiz:
        out.append(
            Milestone(kind="first_exercise", at=_iso_utc(ilk_egzersiz[0]), detail=ilk_egzersiz[1])
        )

    from api.db.models import JournalEntry
    ilk_gunluk = db.execute(
        select(sqlfunc.min(JournalEntry.created_at)).where(JournalEntry.user_id == user_id)
    ).scalar_one_or_none()
    if ilk_gunluk:
        out.append(Milestone(kind="first_journal", at=_iso_utc(ilk_gunluk)))

    ilk_yonlendirme = db.execute(
        select(sqlfunc.min(Turn.ts))
        .join(ChatSession, Turn.session_id == ChatSession.id)
        .where(ChatSession.user_id == user_id, Turn.safety_route.in_(_REFERRAL_ROUTES))
    ).scalar_one_or_none()
    if ilk_yonlendirme:
        out.append(Milestone(kind="first_referral", at=_iso_utc(ilk_yonlendirme)))

    out.sort(key=lambda m: m.at)
    return out

@router.get("/me/insights", response_model=InsightsResponse)
async def my_insights(
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """Konuşmalardan çıkarılmış sinyallerin hesap düzeyinde toplanmış hali.

    UserProfile oturum başına tutuluyor; burada kullanıcının bütün
    oturumlarındaki satırlar birleştiriliyor. Ayrı bir tablo açmak yerine
    okuma anında topluyoruz — veri zaten orada ve hacim küçük.

    progress_notes bilerek dışarıda: klinisyen sesiyle yazılmış notlar
    ("... bildirdi") kullanıcıya dosya gibi görünüyor.
    """
    from api.db.models import UserProfile

    factory = store._SessionLocal()
    with factory() as db:
        rows = db.execute(
            select(UserProfile)
            .join(ChatSession, UserProfile.session_id == ChatSession.id)
            .where(ChatSession.user_id == user.id)
        ).scalars().all()

        ilk = db.execute(
            select(sqlfunc.min(ChatSession.created_at)).where(
                ChatSession.user_id == user.id
            )
        ).scalar_one_or_none()

        kilometre_taslari = _milestones(db, user.id)

        tema_sayaci: dict[str, int] = {}
        coping: dict[str, str] = {}
        tetikleyici: list[str] = []

        for r in rows:
            for t in (r.themes or []):
                tema_sayaci[t] = tema_sayaci.get(t, 0) + 1
            # Sonraki oturum öncekini eziyor: en güncel değerlendirme geçerli.
            for teknik, karar in (r.coping_tried or {}).items():
                coping[teknik] = karar
            for tg in (r.triggers or []):
                if tg not in tetikleyici:
                    tetikleyici.append(tg)

    temalar = [
        ThemeCount(label=k, sessions=v)
        for k, v in sorted(tema_sayaci.items(), key=lambda x: (-x[1], x[0]))
    ]
    teknikler = [
        CopingItem(
            technique=k,
            label=_TECHNIQUE_LABELS.get(k, k.replace("_", " ")),
            verdict=v,
        )
        for k, v in sorted(coping.items())
    ]

    return InsightsResponse(
        themes=temalar,
        coping=teknikler,
        triggers=tetikleyici[:20],
        session_count=len(rows),
        first_session_at=_iso_utc(ilk),
        milestones=kilometre_taslari,
    )


@router.delete("/me/insights")
async def delete_my_insights(
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """Çıkarılmış sinyalleri siler, sohbetlere dokunmaz.

    KVKK açısından gerekli: kullanıcı hakkında çıkarım yapıyorsak onu
    silebilmesi de gerekiyor. Sohbetin kendisi ayrı bir karar.
    """
    from api.db.models import UserProfile

    factory = store._SessionLocal()
    with factory() as db, db.begin():
        rows = db.execute(
            select(UserProfile)
            .join(ChatSession, UserProfile.session_id == ChatSession.id)
            .where(ChatSession.user_id == user.id)
        ).scalars().all()
        for r in rows:
            r.themes = None
            r.triggers = None
            r.coping_tried = None
            r.progress_notes = None
            r.last_summary = None

    return {"status": "cleared", "profiles": len(rows)}

class DeviceView(BaseModel):
    id: str
    user_agent: Optional[str] = None
    created_at: str
    last_used_at: Optional[str] = None
    current: bool

@router.get("/devices", response_model=list[DeviceView])
async def my_devices(
    request: Request,
    user: User = Depends(get_current_user),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """Açık oturumlar. Hangisinin bu cihaz olduğu çerezden anlaşılıyor.

    "Bu cihaz" işaretlemesi olmadan "tüm cihazlardan çık" düğmesi korkutucu
    oluyor — kullanıcı kendini de atacağını bilmiyor.
    """
    from api.db.models import RefreshToken

    raw = get_refresh_cookie(request)
    su_anki_hash = rt.hash_token(raw) if raw else None

    factory = store._SessionLocal()
    with factory() as db:
        rows = db.execute(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
            .order_by(RefreshToken.created_at.desc())
        ).scalars().all()

        return [
            DeviceView(
                id=str(r.id),
                user_agent=r.user_agent,
                created_at=_iso_utc(r.created_at),
                last_used_at=_iso_utc(r.last_used_at),
                current=(r.token_hash == su_anki_hash),
            )
            for r in rows
        ]


@router.delete("/devices/{device_id}")
async def revoke_device(
    device_id: str,
    user: User = Depends(get_current_user),
    _: None = Depends(require_client_header),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """Tek bir cihazın oturumunu kapat."""
    from api.db.models import RefreshToken

    try:
        did = uuid.UUID(device_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Cihaz bulunamadı")

    factory = store._SessionLocal()
    with factory() as db, db.begin():
        row = db.get(RefreshToken, did)
        # Sahiplik kontrolü: başkasının oturumunu kapatamamalı. 403 değil 404,
        # id denemesiyle başkasının cihaz sayısı çıkarılmasın.
        if row is None or row.user_id != user.id:
            raise HTTPException(status_code=404, detail="Cihaz bulunamadı")
        if row.revoked_at is None:
            row.revoked_at = rt._now()

    return {"status": "revoked"}

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/me/password")
async def change_password(
    req: PasswordChange,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    _: None = Depends(require_client_header),
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """Giriş yapmış kullanıcının şifresini değiştirir.

    Mevcut şifre isteniyor: access token çalınmış olabilir, onunla şifre
    değiştirilip hesap tamamen ele geçirilmesin.

    Değişiklikten sonra diğer bütün oturumlar kapanıyor. Şifre değiştirmenin
    en yaygın sebebi "hesabıma birinin eriştiğinden şüpheleniyorum" —
    o kişinin oturumu açık kalırsa işlem anlamsız olur.
    """
    factory = store._SessionLocal()
    with factory() as db, db.begin():
        row = db.get(User, user.id)
        if row is None:
            raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")

        if not verify_password(req.current_password, row.password_hash):
            raise HTTPException(status_code=401, detail="Mevcut şifren hatalı")

        if req.current_password == req.new_password:
            raise HTTPException(
                status_code=400, detail="Yeni şifre eskisiyle aynı olamaz"
            )

        row.password_hash = hash_password(req.new_password)

        # Diğer cihazları düşür, bu cihaza yeni bir oturum aç. Kullanıcı
        # kendi tarayıcısından atılmasın ama başkaları çıksın.
        rt.revoke_all_for_user(db, row.id)
        yeni_refresh = rt.issue(
            db, row.id, user_agent=request.headers.get("user-agent")
        )
        yeni_access = encode_token(row.id)

    set_refresh_cookie(response, yeni_refresh)
    return {"status": "changed", "access_token": yeni_access}