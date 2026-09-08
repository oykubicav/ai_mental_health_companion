from pydantic import BaseModel, Field, constr
from typing import Optional, List, Literal, Dict, Any

class ChatOptions(BaseModel):
    enable_llm_critic: bool = True
    enable_intent: bool = True
    max_rewrites: int = Field(1, ge=0, le=3)
    top_k: int = Field(6, ge=1, le=20)
    temperature: float = Field(0.3, ge=0.0, le=1.0)

class ChatRequest(BaseModel):
    user_message: constr(min_length=1, max_length=4000)
    session_id: Optional[str] = None
    options: ChatOptions = ChatOptions()
    # Kullanıcı kontrol sorusuna "evet" dediğinde gönderilir; tam kriz
    # yanıtına geçilir, yeniden tespit beklenmez.
    crisis_confirmed: bool = False

class SafetyView(BaseModel):
    route: str
    allow_cbt: bool
    highest_risk: str
    matched_card_ids: List[str]
    # Cevap bir kontrol sorusuysa arayüz onay kartını gösterir.
    needs_confirmation: bool = False
    # Destekleyici ama egzersizsiz yol. Arayüz bu turda egzersiz
    # bağlantısı önermez.
    blocks_exercise: bool = False

class IntentView(BaseModel):
    module: str
    subintent: str
    confidence: float
    # Konuşmanın nasıl gittiği ve bu turda kullanılan süreç kartları.
    # İçerik kartlarından (retrieved_card_ids) ayrı tutuluyor.
    conversation_state: str = "neutral"
    process_card_ids: List[str] = Field(default_factory=list)

class CriticView(BaseModel):
    passed: bool
    rewrites: int
    used_fallback: bool
    findings_summary: Optional[List[str]] = None  # debug'da açık

class ChatResponse(BaseModel):
    turn_id: str
    session_id: str
    response: str
    safety: SafetyView
    intent: IntentView
    retrieved_card_ids: List[str]
    critic: CriticView
    timing_ms: Dict[str, float] = Field(default_factory=dict)
    boundary_state: str = "normal"
    turn_count: int = 0

class FeedbackRequest(BaseModel):
    turn_id: str
    session_id: Optional[str] = None
    verdict: Literal["thumbs_up", "thumbs_down", "flag"]
    comment: Optional[constr(max_length=1000)] = None

class FeedbackResponse(BaseModel):
    received: bool = True
    feedback_id: str


class ConsentRequest(BaseModel):
    policy_version: constr(min_length=1, max_length=16)
    session_id: Optional[str] = None


class ConsentResponse(BaseModel):
    session_id: str
    consent_id: str
    policy_version: str

class EvalRunRequest(BaseModel):
    which: Literal["structural", "response"]
    filter: Optional[str] = None
    top_k: int = Field(8, ge=1, le=20)
    no_llm_critic: bool = False
    label: str = "api"

class EvalRunResponse(BaseModel):
    run_id: str
    status: Literal["queued", "running", "done", "error"]

class EvalStatusResponse(BaseModel):
    run_id: str
    status: Literal["queued", "running", "done", "error"]
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    ok: bool = True
    version: str

class ReadyzResponse(BaseModel):
    ok: bool
    checks: Dict[str, bool]
    details: Dict[str, str] = Field(default_factory=dict)



class CBTCardOut(BaseModel):
    """Response modeli — cbt_cards.jsonl formatına birebir.

    NOT: topic ve type plain str — kart ontology zamanla genişleyebilir
    (ör. 'in_attack' tipi eklenmiş). Query paramlarında Literal ile
    kısıtlıyoruz, response'ta değil.
    """
    id: str
    topic: str
    type: str
    title_tr: str
    content_tr: str
    safety_notes: Optional[str] = None
    source_refs: List[str] = Field(default_factory=list)
    review_status: str = "needs_review"


class CBTCardSummary(BaseModel):
    """Liste view'ı — content_tr olmadan, hafif."""
    id: str
    topic: str
    type: str
    title_tr: str
    review_status: str


class CBTCardListResponse(BaseModel):
    cards: List[CBTCardSummary]
    total: int             # filtre uygulandıktan sonraki toplam
    limit: int
    offset: int


class SafetyCardOut(BaseModel):
    """Safety kartı — CBT'den farklı schema. Admin-only endpoint."""
    card_id: str
    module: str
    card_type: str
    title: str
    risk_level: Literal["low", "medium", "high", "critical"]
    route: str
    allow_cbt: bool
    blocks_exercise: bool
    must_do_tr: str
    must_not_do_tr: List[str]
    safe_response_template_tr: str
    concept_ids: List[str] = Field(default_factory=list)
    review_status: str


class SafetyCardListResponse(BaseModel):
    cards: List[SafetyCardOut]
    total: int


class TopicInfo(BaseModel):
    topic: str
    count: int
    display_name_tr: str


class TopicsResponse(BaseModel):
    topics: List[TopicInfo]