"""orchestrator.py — End-to-end pipeline with critic + rewrite loop.

Wires together:
    safety_classifier  ->  retriever  ->  composer  ->  output_critic
    (optional rewrite  ->  final safety-template fallback)

Public API:
    respond(user_message) -> Turn

KVKK note:
- redact_pii runs inside llm_adapter before any LLM call.
- This module never persists user text. Persistence is the caller's job.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Optional, Dict, Any

from . import config
from . import safety_classifier
from . import intent_classifier
from . import retriever
from . import composer
from . import output_critic
from .types import SafetyDecision, RetrievedCard, IntentDecision
from .composer import _BOUNDARY_HARD, _BOUNDARY_CLOSING_START

# Intent sınıflandırıcısı kriz dediğinde güvenlik rotasına geçmek için gereken
# asgari güven. Düşük güvenli tahminler yanlış alarma yol açmasın diye eşik var.
_INTENT_ESCALATION_CONFIDENCE = 0.7



# Safety-template fallback loader
from . import cards as _cards
_HARD_CLOSE_TEMPLATE_TR = (
    "Bugün için epey iyi bir noktadayız — biraz aradan sonra devam etmen "
    "sürecin doğal bir parçası. Bugün konuştuklarımızı hatırlayacağım. "
    "Acil bir durum varsa 112'yi ara. Yarın burada olacağım."
)


def _safety_template_fallback(safety: SafetyDecision) -> str:
    """Return the exact safe_response_template_tr from the dominant safety card.

    Used as last-resort when composer + rewrite both fail critic. This
    guarantees a safe (if boilerplate) response even if the LLM misbehaves.
    """
    cards = _cards.safety_cards_by_id()
    for card_id in safety.safety_card_ids:
        c = cards.get(card_id)
        if c:
            return c.get("safe_response_template_tr", "")
    return (
        "Anlattıklarını ciddiye alıyorum. Şu an güvende olman en önemli şey. "
        "Türkiye'de acil bir durum varsa 112'yi ara. Uzman değerlendirmesi için "
        "aile hekimine başvurabilir ya da doğrudan psikiyatri veya klinik psikolog "
        "randevusu alabilirsin. Bu chatbot uzman değerlendirmesinin yerine geçmez."
    )



# Turn container

@dataclass
class Turn:
    user_message: str
    response_text: str
    safety: SafetyDecision
    intent: Optional[IntentDecision]
    retrieved: List[RetrievedCard]
    critic: Dict[str, Any]                # CritiqueResult.to_dict() of FINAL critic
    critic_history: List[Dict[str, Any]] = field(default_factory=list)
    rewrite_count: int = 0
    used_fallback: bool = False
    timing_ms: Dict[str, float] = field(default_factory=dict)
    branch: str = ""
    model: str = ""
    provider: str = ""
    # Konuşmanın nasıl yürütüleceğini belirleyen süreç kartları — içerik
    # kartlarından ayrı tutuluyor, şeffaflık panelinde de ayrı gösteriliyor.
    process_card_ids: List[str] = field(default_factory=list)
    conversation_state: str = "neutral"

    def summary(self) -> str:
        lines = []
        lines.append(f"USER: {self.user_message}")
        lines.append(f"SAFETY: route={self.safety.final_route} allow_cbt={self.safety.allow_cbt} "
                     f"risk={self.safety.highest_risk} cards={self.safety.safety_card_ids or '[]'}")
        if self.intent is not None:
            sub = getattr(self.intent, "subintent", "?")
            lines.append(f"INTENT: module={self.intent.primary_module}  subintent={sub}  "
                         f"conf={self.intent.confidence:.2f}  ({self.intent.rationale})")
        if self.process_card_ids:
            lines.append(f"PROCESS: state={self.conversation_state} "
                         f"cards={', '.join(self.process_card_ids)}")
        if self.retrieved:
            top = ", ".join(f"{r.card_id}({r.score:.2f})" for r in self.retrieved[:5])
            lines.append(f"RETRIEVED (top 5): {top}")
        cstat = "PASS" if self.critic.get("passed") else "FAIL"
        lines.append(f"CRITIC ({self.critic.get('method')}): {cstat}  "
                     f"rewrites={self.rewrite_count}  fallback={self.used_fallback}")
        if not self.critic.get("passed"):
            for f in self.critic.get("findings", [])[:6]:
                lines.append(f"  - [{f['layer']}/{f['severity']}] {f['check_id']}: {f['message']}")
        lines.append(f"BRANCH: {self.branch}   MODEL: {self.model}   PROVIDER: {self.provider}")
        lines.append("-" * 60)
        lines.append("RESPONSE:")
        lines.append(self.response_text)
        return "\n".join(lines)



# Public API

_MIN_QUERY_CHARS = 25
_MIN_QUERY_WORDS = 4


def _retrieval_query(user_message: str, history: Optional[List[dict]]) -> str:
    """Kart araması için kullanılacak metni seç.

    "tamam", "evet", "hayır öyle değil" gibi kısa yanıtlar tek başına arandığında
    alakasız kart getiriyor — "hayır" sözcüğü sınır koyma kartlarıyla eşleşiyor
    örneğin. Bu durumda konuşmadaki son anlamlı kullanıcı mesajı kullanılır;
    konu orada tanımlanmıştır.
    """
    text = user_message.strip()
    if len(text) >= _MIN_QUERY_CHARS or len(text.split()) >= _MIN_QUERY_WORDS:
        return user_message

    for turn in reversed(history or []):
        previous = (turn.get("user_message") or "").strip()
        if len(previous) >= _MIN_QUERY_CHARS or len(previous.split()) >= _MIN_QUERY_WORDS:
            return previous

    return user_message


def respond(
    user_message: str,
    *,
    history: Optional[List[dict]] = None,
    profile_summary: Optional[str] = None,
      turn_count: int = 0,
    top_k: int = 6,
    temperature: float = 0.3,
    enable_llm_critic: bool = True,
    enable_intent: bool = True,
    max_rewrites: int = 1,
    crisis_confirmed: bool = False,
) -> Turn:
    """End-to-end: safety -> intent -> retrieve -> compose -> critique
    (-> optional rewrite -> optional safety-template fallback).

    Args:
        history: prior conversation as list of {user_message, response} dicts
                 (oldest first). Composer includes them in its prompt so the
                 assistant remembers prior turns.
        profile_summary: structured user profile summary from profile_extractor.
                 Composer injects into system prompt. api layer builds this via
                 profile_store.get_summary_for_composer().
    """
    t = {}

    # 1. Safety
    t0 = time.time()
    safety = safety_classifier.classify(user_message, enable_layer3=True)
    t["safety_ms"] = (time.time() - t0) * 1000

    # Kullanıcı kontrol sorusunu onayladı: artık çıkarım değil, beyan.
    # Tam kriz yanıtına geç, yeniden tespit bekleme.
    if crisis_confirmed:
        safety = safety_classifier.escalate_from_intent(safety)
        safety.needs_confirmation = False



    # 2. Intent (real Haiku classifier; short-circuits on safety hard-stop)
    t0 = time.time()
    intent = intent_classifier.classify(user_message, safety, enable_llm=enable_intent)
    t["intent_ms"] = (time.time() - t0) * 1000

    # Kural ve embedding katmanları önceden yazılmış ifadelere bakıyor. İkisi de
    # kaçırdığında son kontrol burada: intent sınıflandırıcısı zaten her mesajda
    # çağrılan bir LLM ve kriz tanımı prompt'unda yazılı.
    if (
        safety.allow_cbt
        and intent.primary_module == "safety"
        and intent.confidence >= _INTENT_ESCALATION_CONFIDENCE
    ):
        safety = safety_classifier.escalate_from_intent(safety)

    module_filter = intent_classifier.module_filter_from_intent(intent) if safety.allow_cbt else None

    # 3. Retrieve (safety hard-stop honored inside retriever; module bias
    # when intent classifier is confident)
    t0 = time.time()
    retrieved = retriever.hybrid_retrieve(
        _retrieval_query(user_message, history),
        top_k=top_k,
        safety_card_ids=safety.safety_card_ids or None,
        allow_cbt=safety.allow_cbt,
        module_filter=module_filter,
    )
    t["retrieve_ms"] = (time.time() - t0) * 1000

    # 4. Compose (with conversation history + longitudinal profile for coherence)
    t0 = time.time()
    conv_state = getattr(intent, "conversation_state", "neutral") if intent else "neutral"
    composed = composer.compose(
        user_message, safety, retrieved,
        intent=intent,
        history=history,
        profile_summary=profile_summary,
        turn_count=turn_count,
        conversation_state=conv_state,
        temperature=temperature,
    )
    t["compose_ms"] = (time.time() - t0) * 1000
    response_text = composed.text
    branch = composed.branch

    # 5. Critique (rule + LLM)
    t0 = time.time()
    crit = output_critic.critique(response_text, safety, user_message, enable_llm=enable_llm_critic)
    t["critic_ms"] = (time.time() - t0) * 1000
    critic_history = [crit.to_dict()]
    rewrite_count = 0
    used_fallback = False

    # 6. Rewrite loop
    while (not crit.passed) and rewrite_count < max_rewrites:
        rewrite_count += 1
        t0 = time.time()
        response_text = _rewrite_via_composer(
            user_message, safety, retrieved, response_text, crit,
            temperature=temperature,
            intent=intent,
            history=history,
            profile_summary=profile_summary,
        )
        t.setdefault("rewrite_ms", 0.0)
        t["rewrite_ms"] += (time.time() - t0) * 1000

        t0 = time.time()
        crit = output_critic.critique(response_text, safety, user_message, enable_llm=enable_llm_critic)
        t["critic_ms"] += (time.time() - t0) * 1000
        critic_history.append(crit.to_dict())

    # 7. Safety-template fallback (only when safety hard-stop still failing)
    if not crit.passed and not safety.allow_cbt:
        response_text = _safety_template_fallback(safety)
        used_fallback = True
        # Re-critique the template to record final verdict
        crit = output_critic.critique(response_text, safety, user_message, enable_llm=False)
        critic_history.append(crit.to_dict())

    return Turn(
        user_message=user_message,
        response_text=response_text,
        safety=safety,
        intent=intent,
        retrieved=retrieved,
        critic=crit.to_dict(),
        critic_history=critic_history,
        rewrite_count=rewrite_count,
        used_fallback=used_fallback,
        timing_ms=t,
        branch=branch,
        model=composed.model,
        provider=composed.provider,
        process_card_ids=list(composed.process_card_ids),
        conversation_state=conv_state,
    )



# Rewrite helper

def _rewrite_via_composer(
    user_message: str,
    safety: SafetyDecision,
    retrieved: List[RetrievedCard],
    previous_response: str,
    crit: output_critic.CritiqueResult,
    *,
    temperature: float,
    intent=None,
    history: Optional[List[dict]] = None,
    profile_summary: Optional[str] = None,
) -> str:
    """Ask the composer to rewrite, passing critic findings.

    Implementation: we hijack the composer's prompt builder and append an
    additional REWRITE section listing the issues.
    """
    findings_block = output_critic.summarize_findings_for_rewrite(crit.findings)
    base_user_prompt = composer._build_user_prompt(
        user_message, safety, retrieved,
        intent=intent, history=history, profile_summary=profile_summary,
    )
    rewrite_addendum = (
        f"\n\n---\n"
        f"YENIDEN YAZMA GEREKÇESİ:\n"
        f"Önceki cevap aşağıdaki kural ihlalleri nedeniyle reddedildi:\n"
        f"{findings_block}\n\n"
        f"ÖNCEKİ CEVAP:\n"
        f"\"\"\"{previous_response}\"\"\"\n\n"
        f"ŞİMDİ: Aynı KULLANICI MESAJI'na, yukarıdaki ihlallerin HİÇBİRİNİ tekrar etmeyecek "
        f"şekilde YENİDEN yaz. Sadece son cevabı yaz — açıklama ekleme."
    )
    from . import llm_adapter
    resp = llm_adapter.llm_complete(
        system=composer.SYSTEM_PROMPT_TR,
        user=base_user_prompt + rewrite_addendum,
        model=config.LLM_MODEL_COMPOSER,
        max_tokens=1024,
        temperature=temperature,
        redact=True,
    )
    return resp.text.strip()


# CLI smoke test


if __name__ == "__main__":
    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("(No ANTHROPIC_API_KEY set — using mock composer)")
        os.environ["CBT_LLM_PROVIDER"] = "mock"
        composer.register_composer_mocks()

    examples = [
        "Sürekli nabzımı kontrol ediyorum, kalbim hızlı atıyor.",
        "Ölmek istiyorum, kendime zarar vermeyi düşünüyorum.",
        "Antidepresan dozumu artırayım mı?",
    ]
    for ex in examples:
        turn = respond(ex, enable_llm_critic=False)  # rule-only critic in smoke
        print(turn.summary())
        print()
