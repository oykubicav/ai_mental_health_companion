# api/routes/chat.py
"""POST /chat — main endpoint. Wires the orchestrator behind HTTP.

Contract:
  - Never returns 5xx from the happy path. If the orchestrator raises,
    we degrade gracefully with a safety fallback response and 200 OK.
  - session_id is optional; if omitted, we create one and return it.
  - Response is exhaustively typed by schemas.ChatResponse.
"""

from __future__ import annotations

import logging
import uuid
from typing import List
from typing import Optional


from fastapi import APIRouter, Depends, Request, BackgroundTasks, HTTPException

from api.schemas import (
    ChatRequest, ChatResponse,
    SafetyView, IntentView, CriticView,
)
from api.deps import session_store_dep
from api.session import InMemorySessionStore
from api import profile_store
from pipeline import orchestrator
from pipeline.profile_extractor import extract_profile_patch
from pipeline.composer import get_boundary_state
from pipeline.llm_adapter import llm_complete
from pipeline import config as pipeline_config
from api.auth.dependencies import get_current_user_optional
from api.db.models import User

router = APIRouter(prefix="/chat", tags=["chat"])
log = logging.getLogger(__name__)


def _background_profile_update(
    session_id_str: str,
    user_message: str,
    response_text: str,
    session_local_factory,
) -> None:
    """Haiku extract + Postgres apply. Fully background — never blocks the
    response. Sessiz-fail: her hata log'lanır, cevap zaten kullanıcıya gitti.
    """
    try:
        session_id = uuid.UUID(session_id_str)
    except Exception:
        return

    try:
        # Kendi kısa özetini referans olarak ver (Haiku daha iyi context'e sahip olur)
        with session_local_factory() as db:
            current_summary = profile_store.get_summary_for_composer(db, session_id)

        patch = extract_profile_patch(
            user_message=user_message,
            response_text=response_text,
            current_profile_summary=current_summary if current_summary else None,
        )

        with session_local_factory() as db:
            profile_store.apply_patch(db, session_id, patch)

        log.info(
            "profile_update",
            extra={
                "session_id": session_id_str,
                "triggers_added": len(patch.add_triggers),
                "themes_added": len(patch.add_themes),
                "coping_added": len(patch.coping_updates),
            },
        )
    except Exception as e:
        log.warning(
            "background_profile_update_failed",
            extra={"session_id": session_id_str, "error": str(e)},
        )


SAFE_FALLBACK_TEXT = (
    "Şu an sistemsel bir hata nedeniyle sana normal yanıt üretemiyorum. "
    "Eğer bir kriz durumundaysan lütfen 112'yi ara ya da en yakın acil servise git. "
    "Uzman desteği için aile hekimine başvurabilir ya da doğrudan psikiyatri veya "
    "klinik psikolog randevusu alabilirsin. Bu chatbot uzman değerlendirmesinin "
    "yerine geçmez."
)


def _findings_summary(critic_dict: dict) -> List[str]:
    """Compact findings for the client — check_id + short message only."""
    out = []
    for f in critic_dict.get("findings", [])[:6]:
        out.append(f"{f.get('check_id', '?')}: {f.get('message', '')}")
    return out


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    store: InMemorySessionStore = Depends(session_store_dep),
    user: Optional[User] = Depends(get_current_user_optional),  
):
    session_id = store.ensure(req.session_id)
    if user is not None:
        store.attach_user(session_id, user.id)
    

    request_id = getattr(request.state, "request_id", None)

    # Prior conversation for multi-turn context. If session is new or empty,
    # get_history returns [] and pipeline behaves exactly as single-turn.
    history = store.get_history(session_id)
    turn_count = store.sitting_turn_count(session_id) + 1

    # Longitudinal profile — arka planda güncellenen yapılandırılmış özet.
    # İlk turn'de boş; sonraki turnlerde composer'a "hatırlıyorum" hissi verir.
    profile_summary = ""
    try:
        session_local = store._SessionLocal()
        with session_local() as db:
            profile_summary = profile_store.get_summary_for_composer(
                db, uuid.UUID(str(session_id))
            )
    except Exception as e:
        log.warning(f"profile_summary_fetch_failed: {e}")

    try:
        turn = orchestrator.respond(
            req.user_message,
            history=history,
            profile_summary=profile_summary if profile_summary else None,
            turn_count=turn_count,
            top_k=req.options.top_k,
            enable_llm_critic=req.options.enable_llm_critic,
            enable_intent=req.options.enable_intent,
            max_rewrites=req.options.max_rewrites,
            temperature=req.options.temperature,
            crisis_confirmed=req.crisis_confirmed,
        )
    except Exception as e:
        log.exception(
            "orchestrator failed",
            extra={"request_id": request_id, "session_id": session_id,
                   "route": "/chat"},
        )
        # 200 with safety fallback rather than 500
        return ChatResponse(
            turn_id="err-" + uuid.uuid4().hex,
            session_id=session_id,
            response=SAFE_FALLBACK_TEXT,
            safety=SafetyView(
                route="cbt_support", allow_cbt=True, highest_risk="low",
                matched_card_ids=[],
            ),
            intent=IntentView(module="unknown", subintent="unknown", confidence=0.0),
            retrieved_card_ids=[],
            critic=CriticView(passed=False, rewrites=0, used_fallback=True,
                              findings_summary=[f"internal_error: {type(e).__name__}"]),
            timing_ms={"error": 1.0},
        )

    intent_module = turn.intent.primary_module if turn.intent else "unknown"
    intent_subintent = getattr(turn.intent, "subintent", "unknown") if turn.intent else "unknown"
    intent_conf = turn.intent.confidence if turn.intent else 0.0

    turn_id = store.append_turn(
        session_id=session_id,
        user_message=req.user_message,
        response=turn.response_text,
        safety_route=turn.safety.final_route,
        intent_module=intent_module,
        safety_json={
            "route": turn.safety.final_route,
            "allow_cbt": turn.safety.allow_cbt,
            "highest_risk": turn.safety.highest_risk,
            "matched_card_ids": turn.safety.safety_card_ids,
        },
        intent_json={
            "module": intent_module,
            "subintent": intent_subintent,
            "confidence": intent_conf,
            # Süreç katmanı: konuşmanın nasıl gittiği ve o tur hangi
            # süreç kartlarının kullanıldığı. Ayrı kolon açmak yerine
            # burada — ikisi de sınıflandırmanın çıktısı.
            "conversation_state": getattr(turn, "conversation_state", "neutral"),
            "process_card_ids": list(getattr(turn, "process_card_ids", [])),
        },
        critic_json=turn.critic,
        timing_ms_json=turn.timing_ms,
        model_version=turn.model,
        boundary_state=get_boundary_state(turn_count),
        retrieved_card_ids=[r.card_id for r in turn.retrieved],

    )

    # Background: Haiku ile profil extract + Postgres apply. Cevap yollandıktan
    # sonra async çalışır — kullanıcı beklemez. Faz 2 Deliverable #3 kararı A/A/A/A.
    background_tasks.add_task(
        _background_profile_update,
        session_id_str=str(session_id),
        user_message=req.user_message,
        response_text=turn.response_text,
        session_local_factory=store._SessionLocal(),
    )

    log.info(
        "chat_completed",
        extra={
            "request_id": request_id,
            "session_id": session_id,
            "turn_id": turn_id,
            "route": "/chat",
            "safety_route": turn.safety.final_route,
            "intent_module": intent_module,
            "rewrites": turn.rewrite_count,
            "used_fallback": turn.used_fallback,
            "critic_passed": turn.critic.get("passed"),
        },
    )

    return ChatResponse(
        turn_id=turn_id,
        session_id=session_id,
        response=turn.response_text,
        safety=SafetyView(
            route=turn.safety.final_route,
            allow_cbt=turn.safety.allow_cbt,
            highest_risk=turn.safety.highest_risk,
            matched_card_ids=turn.safety.safety_card_ids,
            needs_confirmation=getattr(turn.safety, "needs_confirmation", False),
            blocks_exercise=getattr(turn.safety, "blocks_exercise", False),
        ),
        intent=IntentView(
            module=intent_module,
            subintent=intent_subintent,
            confidence=intent_conf,
            conversation_state=getattr(turn, "conversation_state", "neutral"),
            process_card_ids=list(getattr(turn, "process_card_ids", [])),
        ),
        retrieved_card_ids=[r.card_id for r in turn.retrieved],
        critic=CriticView(
            passed=turn.critic.get("passed", False),
            rewrites=turn.rewrite_count,
            used_fallback=turn.used_fallback,
            findings_summary=_findings_summary(turn.critic),
        ),
        timing_ms=turn.timing_ms,
        boundary_state=get_boundary_state(turn_count),
        turn_count=turn_count,    

    )


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """KVKK — kullanıcı silme talebi endpoint'i."""
    deleted = store.delete(session_id)
    return {"deleted": deleted, "session_id": session_id}


@router.get("/session/{session_id}/recap")
async def session_recap(
    session_id: str,
    store: InMemorySessionStore = Depends(session_store_dep),
):
    """Oturum sonu özeti — kullanıcıya gösterilmek üzere."""
    history = store.get_history(session_id)
    if len(history) < 3:
        raise HTTPException(status_code=400, detail="Özet için yeterli konuşma yok")

    transcript = "\n\n".join(
        f"Kullanıcı: {h.get('user_message', '')}\nNeva: {h.get('response', '')}"
        for h in history[-30:]
    )

    system = (
        "Bir CBT destek konuşmasının sonunda kullanıcıya gösterilecek kısa bir "
        "kapanış notu yazıyorsun. Doğrudan kullanıcıya, ikinci tekil şahısla "
        "Türkçe yaz.\n\n"
        "Üç bölüm olsun, her biri başlıksız ve kısa:\n"
        "1. Bugün konuştuklarınızın iki-üç cümlelik özeti.\n"
        "2. Konuşmada beliren örüntüyü tek cümlede adlandır. Tanı koyma, "
        "kategorize etme, kişilik yorumu yapma.\n"
        "3. Denemesi için tek bir küçük, somut adım. Konuşmada zaten "
        "konuştuysanız onu hatırlat; yoksa uygun olan bir tane öner.\n\n"
        "Kurallar: Tanı koyma. Övgü yapma. 'Harikasın', 'çok güçlüsün' gibi "
        "boş cümleler kurma. Madde işareti ve başlık kullanma, akıcı paragraflar "
        "yaz. Toplam 120 kelimeyi geçme."
    )

    try:
        resp = llm_complete(
            system=system,
            user=transcript,
            model=pipeline_config.LLM_MODEL_COMPOSER,
            max_tokens=400,
            temperature=0.3,
            redact=True,
        )
        return {"session_id": session_id, "recap": resp.text.strip()}
    except Exception:
        log.exception("session recap failed")
        raise HTTPException(status_code=503, detail="Özet şu an oluşturulamadı")








