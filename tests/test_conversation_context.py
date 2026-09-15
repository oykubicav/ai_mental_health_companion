"""Konuşma geçmişinin sınıflandırıcıya ve kritiğe ulaşması.

Uzun süre iki bileşen de konuşmayı tek mesaj üzerinden değerlendiriyordu.
"yani?" gibi bir mesajın tek başına anlamı yok — hangi modüle ait olduğu da,
hangi durumu gösterdiği de önceki turda. Aynı şekilde kritik, önceki asistan
turlarını görmediği için tekrarı yapısal olarak fark edemiyordu.

Bu testler bağlantının kurulu kaldığını sabitliyor. Kopması sessiz bir
gerileme olurdu: her şey çalışmaya devam eder, yalnızca kalite düşerdi.
"""

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from pipeline import intent_classifier as ic  # noqa: E402
from pipeline import output_critic as oc  # noqa: E402
from pipeline.types import SafetyDecision  # noqa: E402


GECMIS = [
    {"user_message": "yorucu bi gündü", "response": "Ne tür bir yorgunluk?"},
    {
        "user_message": "zihinsel, çok fazla işi aynı anda yapmaya çalıştım",
        "response": "Dikkatin sürekli bölünmesi tek başına yorucudur. " * 8,
    },
]


# ---------------------------------------------------------------- sınıflandırıcı

def test_history_block_is_empty_without_history():
    assert ic._history_block(None) == ""
    assert ic._history_block([]) == ""


def test_history_block_contains_both_sides():
    blok = ic._history_block(GECMIS)
    assert "yorucu bi gündü" in blok
    assert "Neva:" in blok
    assert "Kullanıcı:" in blok


def test_history_block_marks_which_message_is_being_classified():
    """Model bağlamı sınıflandırılacak mesaj sanmamalı."""
    blok = ic._history_block(GECMIS)
    assert "sınıflandırılacak mesaj bu değil" in blok


def test_history_block_truncates_assistant_replies():
    """Kırpılmasa her sınıflandırma çağrısı composer kadar uzun olurdu."""
    blok = ic._history_block(GECMIS)
    assert "…" in blok
    assert len(blok) < 1200


def test_history_block_respects_the_turn_window():
    cok = [
        {"user_message": f"mesaj {i}", "response": "cevap"}
        for i in range(10)
    ]
    blok = ic._history_block(cok)
    assert "mesaj 9" in blok
    assert "mesaj 0" not in blok


def test_history_block_survives_missing_fields():
    """Boş ya da eksik tur satırı patlatmamalı."""
    assert ic._history_block([{}]) == ""
    blok = ic._history_block([{"user_message": "selam"}])
    assert "selam" in blok


def test_classify_accepts_history_without_llm():
    """Geçmiş, LLM kapalıyken de kabul edilmeli — imza her yolda aynı."""
    intent = ic.classify("yani?", None, history=GECMIS, enable_llm=False)
    assert intent.primary_module == "unknown"


# ---------------------------------------------------------------- tekrar kontrolü

def _safety(allow=True) -> SafetyDecision:
    return SafetyDecision(
        matches=[],
        final_route="cbt" if allow else "safety",
        allow_cbt=allow,
        blocks_exercise=False,
        highest_risk="low",
        safety_card_ids=[],
        needs_confirmation=False,
    )


UZUN = (
    "Dikkatin sürekli bölünmesi tek başına yorucudur çünkü beyin her geçişte "
    "yeniden yön bulmak zorunda kalır ve bu geçişlerin kendisi enerji tüketir, "
    "iş bitmemiş olsa bile yorgunluk birikir diye düşünebiliriz."
)


def test_repetition_is_flagged():
    gecmis = [{"user_message": "peki", "response": UZUN}]
    bulgular = oc._repetition_pass(UZUN + " Ayrıca bir şey daha var.", gecmis)
    assert bulgular
    assert bulgular[0].check_id == "R12_repetition"


def test_repetition_is_soft_not_hard():
    """Tekrar rahatsız edici ama tehlikeli değil.

    Sert yapmak, meşru biçimde bir şeyi netleştiren cevapları da
    reddederdi — yeniden yazdırma bütçesi güvenlik için duruyor.
    """
    gecmis = [{"user_message": "peki", "response": UZUN}]
    bulgular = oc._repetition_pass(UZUN, gecmis)
    assert bulgular and bulgular[0].severity == "soft"


def test_different_content_is_not_flagged():
    gecmis = [{"user_message": "peki", "response": UZUN}]
    farkli = (
        "Bugün hangi işin gerçekten bugüne ait olduğunu ayırmayı deneyebiliriz. "
        "Listenin tamamı yerine tek bir satırla başlamak çoğu zaman yeterli olur."
    )
    assert oc._repetition_pass(farkli, gecmis) == []


def test_short_replies_are_not_measured():
    """Kısa cevaplarda örtüşme doğal — ölçmek yanlış alarm üretir."""
    gecmis = [{"user_message": "peki", "response": "Bunu biraz açar mısın?"}]
    assert oc._repetition_pass("Bunu biraz açar mısın?", gecmis) == []


def test_no_history_means_no_repetition_check():
    assert oc._repetition_pass(UZUN, None) == []
    assert oc._repetition_pass(UZUN, []) == []


def test_only_recent_turns_are_compared():
    """Konuşmanın başındaki bir cümleye dönmek tekrar sayılmamalı."""
    gecmis = [{"user_message": "a", "response": UZUN}] + [
        {"user_message": "b", "response": "Farklı bir cevap."},
        {"user_message": "c", "response": "Başka bir cevap daha."},
    ]
    assert oc._repetition_pass(UZUN, gecmis) == []


def test_critique_runs_repetition_when_history_given():
    gecmis = [{"user_message": "peki", "response": UZUN}]
    sonuc = oc.critique(UZUN, _safety(), "peki", history=gecmis, enable_llm=False)
    assert any(f.check_id == "R12_repetition" for f in sonuc.findings)
    # Yumuşak bulgu yeniden yazdırma tetiklememeli
    assert sonuc.passed


def test_critique_without_history_still_works():
    """Geçmiş isteğe bağlı; verilmezse kritik eskisi gibi çalışmalı."""
    sonuc = oc.critique(UZUN, _safety(), "peki", enable_llm=False)
    assert all(f.check_id != "R12_repetition" for f in sonuc.findings)


# ---------------------------------------------------------------- kimlik sızıntısı

def test_card_id_leak_pattern_covers_every_prefix():
    """Kart kimliği kontrolü bütün kart ailelerini tanımalı.

    Elle yazılmış liste 19 önekten yalnızca 6'sını içeriyordu (ha, pa, ga,
    dep, lse, safety). 13 modülün kimliği cevaba sızsa kontrol görmezden
    gelirdi. Yeni modül eklendikçe liste sessizce eskiyordu; artık kart
    verisinden türetiliyor ve eskiyemez.
    """
    import json as _json
    from pathlib import Path as _P

    from pipeline.output_critic import _card_id_leak_pattern

    kok = _P(__file__).resolve().parent.parent
    kimlikler = []
    for satir in open(kok / "cards/cbt_cards.jsonl", encoding="utf-8"):
        if satir.strip():
            kimlikler.append(_json.loads(satir)["id"])
    for satir in open(kok / "cards/safety_cards.jsonl", encoding="utf-8"):
        if satir.strip():
            kimlikler.append(_json.loads(satir)["card_id"])

    desen = _card_id_leak_pattern()
    kacan = [k for k in kimlikler if not desen.search(f"şu {k} kartına göre")]
    assert not kacan, f"sızıntı kontrolü tanımıyor: {kacan[:8]}"


def test_card_id_leak_pattern_does_not_flag_normal_turkish():
    from pipeline.output_critic import _card_id_leak_pattern

    desen = _card_id_leak_pattern()
    for cumle in [
        "Bugün biraz daha iyi geçmiş olması önemli.",
        "Nefesini yavaşlatmayı deneyebiliriz.",
        "Uyku düzeni ve kaygı birbirini besliyor.",
    ]:
        assert not desen.search(cumle), cumle
