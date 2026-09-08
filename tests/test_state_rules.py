"""Konuşma durumu kural katmanı.

Güvenlik sınıflandırıcısıyla aynı gerekçeyle var: bazı durumları
kaçırmanın maliyeti asimetrik. Ölçümde LLM üç ayrı koşuda da bunlarda
düşük kaldığı için karar modelden alınıp kurala verildi.

Kurallar deterministik — bu testler API çağırmıyor ve koşudan koşuya
değişmiyor. Katmanın bütün değeri de bu.
"""

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))

from pipeline import state_rules as sr  # noqa: E402
from pipeline.intent_classifier import CONVERSATION_STATES  # noqa: E402


def _cases():
    yol = BASE / "evals" / "process_state_test_set.jsonl"
    return [json.loads(l) for l in open(yol, encoding="utf-8") if l.strip()]


def setup_function():
    sr.reset_cache()


# ---------------------------------------------------------------- yapı

def test_rules_load():
    assert sr.covered_states()


def test_covered_states_are_real():
    for durum in sr.covered_states():
        assert durum in CONVERSATION_STATES, f"tanımsız durum: {durum}"


def test_rules_cover_the_costly_states():
    """Kural katmanının varlık sebebi bu dört durum."""
    from eval_process_state import YUKSEK_MALIYET

    kapsanan = set(sr.covered_states())
    for durum in YUKSEK_MALIYET:
        assert durum in kapsanan, f"{durum} yüksek maliyetli ama kuralı yok"


# ---------------------------------------------------------------- eşleşme

def test_reassurance_tag_questions():
    """Teyit sorusu — kaçırılırsa güvence verilir, döngü beslenir."""
    for m in [
        "sence ciddi bir şey değil mi",
        "bu geçer di mi",
        "emin misin gerçekten",
        "tehlikeli bir şey mi acaba",
    ]:
        assert sr.match(m) == "reassurance_seeking", m


def test_reported_tag_question_is_not_reassurance():
    """'... değil mi diye düşündüm' kullanıcının kendi sorusu değil."""
    assert sr.match("hava güzel değil mi diye düşündüm") is None


def test_technique_failed_needs_attempt_and_negative_outcome():
    assert sr.match("o egzersizi yaptım ama hiçbir şey olmadı") == "technique_failed"
    assert sr.match("iki hafta denedim, değişmedi") == "technique_failed"
    # Deneme yok — yalnızca olumsuz sonuç
    assert sr.match("hiçbir şey olmadı") is None


def test_noun_does_not_trigger_attempt_verb():
    """'uygulamalar' ile 'uyguladım' karışmamalı — kelime sınırı.

    Bu gerçek bir yanlış pozitifti: "bu tür uygulamalar bir işe
    yaramıyor bence" şüphe ifadesiydi, technique_failed sayılmıştı.
    """
    assert sr.match("bu tür uygulamalar bir işe yaramıyor bence") != "technique_failed"


def test_ruminating_needs_a_thinking_verb():
    assert sr.match("kafamda o konuşmayı çeviriyorum") == "ruminating"
    assert sr.match("neden hep bana oluyor") == "ruminating"


def test_world_pattern_is_not_rumination():
    """'hep aynı saatte oluyor' örüntü fark etmek, ruminasyon değil.

    İlk sürümde 'hep aynı' tek başına tetikliyordu ve formülasyon
    anlarını ruminasyon sayıyordu.
    """
    assert sr.match("her sabah aynı saatte uyanıyorum") is None
    assert sr.match("şimdi düşününce hep aynı saatte oluyor bu") != "ruminating"


def test_misunderstood_signals():
    for m in ["alakası yok, ben onu demedim", "beni yanlış anladın galiba"]:
        assert sr.match(m) == "misunderstood", m


def test_neutral_messages_do_not_match():
    for m in ["panik atak nedir", "annemle konuştum, iyi geçti", "merhaba"]:
        assert sr.match(m) is None, m


def test_empty_input_is_safe():
    assert sr.match("") is None
    assert sr.match(None) is None


# ---------------------------------------------------------------- eval seti

def test_no_false_positives_on_the_eval_set():
    """Kural LLM'i eziyor; yanlış dayatma en pahalı hata türü."""
    yanlis = []
    for c in _cases():
        eslesme = sr.match(c["user_message_tr"])
        if eslesme is not None and eslesme != c["expected_state"]:
            yanlis.append((c["test_id"], c["expected_state"], eslesme))
    assert not yanlis, f"yanlış pozitif: {yanlis}"


def test_covered_states_are_fully_caught():
    """Kapsanan durumda kaçak kalırsa katman işini yapmıyor demektir."""
    kapsanan = set(sr.covered_states())
    kacan = [
        c["test_id"] for c in _cases()
        if c["expected_state"] in kapsanan and sr.match(c["user_message_tr"]) is None
    ]
    assert not kacan, f"kural kaçırdı: {kacan}"


# ---------------------------------------------------------------- entegrasyon

def test_rule_overrides_llm_in_classifier(monkeypatch):
    """Kural eşleşirse modelin dediği değil kural geçerli olmalı."""
    from pipeline import intent_classifier as ic

    # LLM'i devre dışı bırak: erken dönüş yolunda bile kural işlemeli.
    intent = ic.classify("bu geçer di mi", None, enable_llm=False)
    assert getattr(intent, "conversation_state") == "reassurance_seeking"


def test_no_rule_leaves_llm_answer_alone(monkeypatch):
    from pipeline import intent_classifier as ic

    intent = ic.classify("panik atak nedir", None, enable_llm=False)
    assert getattr(intent, "conversation_state") == "neutral"
