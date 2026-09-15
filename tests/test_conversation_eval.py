"""Konuşma eval'inin kendisi.

Koşu gerçek LLM çağrısı yapıyor; burada onu çalıştırmıyoruz. Test edilen şey
kontrollerin doğru şeyi yakalayıp yakalamadığı. Yanlış alarm üreten bir kusur
tarayıcısı, hiç taramamaktan kötüdür: bir süre sonra kimse bakmaz.
"""

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))

SET_PATH = BASE / "evals" / "conversation_scenarios.jsonl"


def _senaryolar():
    with open(SET_PATH, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


# ---------------------------------------------------------------- senaryolar

def test_scenarios_exist():
    assert len(_senaryolar()) >= 5


def test_ids_unique():
    ids = [s["id"] for s in _senaryolar()]
    assert len(ids) == len(set(ids))


def test_every_scenario_is_multi_turn():
    """Tek turluk senaryo bu eval'in varlık sebebini boşa çıkarır."""
    for s in _senaryolar():
        assert len(s["turlar"]) >= 4, s["id"]


def test_every_scenario_declares_expectations():
    from eval_conversation import _kontroller

    bilinen = set(_kontroller(["a b c d e f g h", "i j k l m n o p"]))
    for s in _senaryolar():
        assert s["beklenen"], s["id"]
        for k in s["beklenen"]:
            assert k in bilinen, f"{s['id']} → tanımsız kontrol {k}"


def test_every_scenario_explains_itself():
    """Senaryo neden var — sonradan bakan bilsin."""
    for s in _senaryolar():
        assert s.get("aciklama", "").strip(), s["id"]


# ---------------------------------------------------------------- kontroller

def test_repetition_is_caught():
    from eval_conversation import _kontroller

    ayni = (
        "Dikkatin sürekli bölünmesi yorucudur çünkü beyin her geçişte yeniden "
        "yön bulmak zorunda kalır ve bu enerji tüketir."
    )
    b = _kontroller([ayni, ayni + " Bunu biraz açayım."])
    assert b["tekrar_yok"] is False


def test_different_turns_are_not_flagged_as_repetition():
    from eval_conversation import _kontroller

    b = _kontroller([
        "Bugün ne olduğunu biraz anlatır mısın, hangi saatte başladı bu.",
        "Listenin tamamı yerine tek bir satırla başlamak çoğu zaman yeterli olur.",
    ])
    assert b["tekrar_yok"] is True


def test_early_closing_is_caught():
    from eval_conversation import _kontroller

    b = _kontroller(["Merhaba.", "İstersen burada durabiliriz, yorgun bir gün olmuş."])
    assert b["erken_kapanis_yok"] is False


def test_closing_after_the_early_window_is_allowed():
    """Konuşma ilerlediyse kapanış teklifi kusur değil."""
    from eval_conversation import _kontroller

    cevaplar = ["bir", "iki", "üç", "dört", "İstersen burada durabiliriz."]
    assert _kontroller(cevaplar)["erken_kapanis_yok"] is True


def test_offer_then_retract_is_caught():
    from eval_conversation import _kontroller

    b = _kontroller([
        "Bunu değiştirmenin bir yolu var, ama bugün bunu konuşmak "
        "isteyip istemediğini bilmiyorum."
    ])
    assert b["oner_geri_cekme_yok"] is False


def test_offer_without_retraction_is_fine():
    from eval_conversation import _kontroller

    b = _kontroller(["Yarın sabah tek bir satır yazmayı deneyebiliriz."])
    assert b["oner_geri_cekme_yok"] is True


def test_retraction_before_offer_is_not_flagged():
    """Sıra önemli: geri çekme ifadesi önerinin ÖNÜNDE ise kusur değil."""
    from eval_conversation import _kontroller

    b = _kontroller(["İstersen şunu deneyebiliriz: akşam tek bir satır yaz."])
    assert b["oner_geri_cekme_yok"] is True


def test_question_every_turn_is_caught():
    from eval_conversation import _kontroller

    b = _kontroller(["Ne oldu?", "Ne zaman başladı?", "Yanında kim vardı?"])
    assert b["her_tur_soru_yok"] is False


def test_some_questions_are_fine():
    """Soru sormak kusur değil; turların çoğunu soruya çevirmek kusur."""
    from eval_conversation import _kontroller

    b = _kontroller([
        "Ne oldu?",
        "Bu tablo tanıdık geliyor.",
        "Peki ya sabahları?",
        "Anlattığından çıkan şey şu.",
    ])
    assert b["her_tur_soru_yok"] is True


def test_reassurance_is_caught():
    from eval_conversation import _kontroller

    b = _kontroller(["Merak etme, ciddi bir şey değil."])
    assert b["guvence_verme_yok"] is False


def test_neutral_text_is_not_flagged_as_reassurance():
    from eval_conversation import _kontroller

    b = _kontroller(["Kalbinin hızlanması panikte sık görülen bir tepkidir."])
    assert b["guvence_verme_yok"] is True


def test_empty_conversation_does_not_crash():
    from eval_conversation import _kontroller

    b = _kontroller([])
    assert b["tekrar_yok"] is True


# ---------------------------------------------------------------- koşucu

def test_runner_refuses_mock_provider(monkeypatch):
    import eval_conversation as ev

    monkeypatch.setenv("CBT_LLM_PROVIDER", "mock")
    monkeypatch.setattr(sys, "argv", ["eval_conversation.py"])
    assert ev.main() == 2


def test_runner_refuses_without_api_key(monkeypatch):
    import eval_conversation as ev

    monkeypatch.delenv("CBT_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["eval_conversation.py"])
    assert ev.main() == 2


def test_semantic_repetition_reports_its_backend():
    """Kontrolün güvenilirliği hangi gömme backend'inin kullanıldığına bağlı.

    sentence-transformers yoksa TF-IDF karakter n-gramına düşüyor ve o da
    esasen sözcüksel; paraphrase'i görmez, kontrol sessizce geçer. Raporun
    bunu söylemesi gerekiyor, aksi hâlde geçen bir kontrol yanlış güven verir.
    """
    from eval_conversation import _kontroller

    uzun_a = " ".join(["dikkat", "bölünmesi", "yorucudur", "çünkü", "beyin"] * 5)
    uzun_b = " ".join(["görev", "değişimi", "enerji", "tüketir", "sürekli"] * 5)
    b = _kontroller([uzun_a, uzun_b])
    assert "anlam_tekrari_yok" in b
    assert b["anlam_tekrari_backend"] in ("sentence-transformers", "tfidf-char-ngram")
    if b["anlam_tekrari_backend"] != "sentence-transformers":
        assert "fallback" in b["anlam_tekrari_detay"]


def test_quoting_a_reassurance_phrase_to_refuse_it_is_not_a_violation():
    """Kartın doğru uygulandığı an, ihlal olarak raporlanmamalı.

    İlk A/B koşusunda kartlı sürüm tam olarak proc_reassurance_001'in
    istediğini yaptı — kalıbı alıntılayıp neden söylemeyeceğini açıkladı —
    ve kontrol bunu güvence verme saydı. Ölçüm, düzelttiği davranışı
    cezalandırıyordu.
    """
    from eval_conversation import _kontroller

    b = _kontroller([
        'Sana "tehlikeli değil" desem birkaç dakika rahatlar, '
        "sonra aynı soru geri gelirdi."
    ])
    assert b["guvence_verme_yok"] is True


def test_actual_reassurance_is_still_caught():
    from eval_conversation import _kontroller

    assert _kontroller(["Merak etme, tehlikeli değil bu."])["guvence_verme_yok"] is False


def test_interrogation_is_a_rate_not_an_absolute():
    """Beş turun dördünde soru sormak da sorgudur.

    İlk sürüm yalnızca 5/5'i yakalıyordu ve kartsız koşudaki 4/5 sessizce
    geçmişti — ölçüm, kartların engellediği davranışı görmüyordu.
    """
    from eval_conversation import _kontroller

    assert _kontroller(["a?", "b?", "c?", "d?", "gözlem."])["her_tur_soru_yok"] is False
    assert _kontroller(["a?", "b?", "c.", "d.", "e."])["her_tur_soru_yok"] is True
