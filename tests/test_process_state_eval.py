"""Konuşma durumu eval setinin ve koşucusunun kendisi.

Eval koşusu gerçek Haiku çağrısı yapıyor; burada onu çalıştırmıyoruz.
Test edilen şey ölçüm aracının kendisi: set doğru mu kurulmuş, raporlama
doğru mu sayıyor. Bozuk bir ölçüm aracı, ölçüm yapmamaktan kötüdür —
yanlış bir güven verir.
"""

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))

from pipeline.intent_classifier import CONVERSATION_STATES  # noqa: E402

SET_PATH = BASE / "evals" / "process_state_test_set.jsonl"


def _cases():
    with open(SET_PATH, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


# ---------------------------------------------------------------- set

def test_set_exists_and_is_substantial():
    assert len(_cases()) >= 80


def test_ids_unique():
    ids = [c["test_id"] for c in _cases()]
    assert len(ids) == len(set(ids))


def test_schema():
    for c in _cases():
        assert c["test_id"]
        assert c["user_message_tr"].strip()
        assert isinstance(c.get("history_tr", []), list)
        assert isinstance(c.get("hard_case", False), bool)


def test_expected_states_are_producible():
    """Beklenen etiket sınıflandırıcının üretebildiği bir değer olmalı.

    Aksi hâlde test hiçbir zaman geçemez ve isabet oranı yapay olarak
    düşük görünür.
    """
    for c in _cases():
        assert c["expected_state"] in CONVERSATION_STATES, (
            f"{c['test_id']} → üretilemez etiket {c['expected_state']}"
        )


def test_every_state_is_covered():
    """Ölçülmeyen bir durum, körlüğün sürmesi demek."""
    kapsanan = {c["expected_state"] for c in _cases()}
    for durum in CONVERSATION_STATES:
        assert durum in kapsanan, f"{durum} için örnek yok"


def test_each_state_has_enough_examples():
    """Tek örnekle ölçülen durumda isabet ya %0 ya %100 çıkar — bilgi vermez."""
    sayim = Counter(c["expected_state"] for c in _cases())
    for durum, n in sayim.items():
        assert n >= 4, f"{durum} yalnızca {n} örnek"


def test_hard_cases_are_marked_and_few():
    """Zor vakalar ayrı raporlanıyor; çoğunluk olurlarsa oran yanıltır."""
    zor = [c for c in _cases() if c.get("hard_case")]
    assert zor, "hiç zor vaka işaretlenmemiş"
    assert len(zor) < len(_cases()) * 0.25


def test_hard_cases_have_notes():
    """Zor vaka neden zor — sonradan bakan bilsin."""
    for c in _cases():
        if c.get("hard_case"):
            assert c.get("notes", "").strip(), f"{c['test_id']} gerekçesiz"


def test_messages_are_distinct():
    mesajlar = [c["user_message_tr"] for c in _cases()]
    assert len(mesajlar) == len(set(mesajlar))


# ---------------------------------------------------------------- koşucu

def test_report_counts_correctly(capsys):
    from eval_process_state import report

    sonuclar = [
        {"test_id": "a", "beklenen": "vague", "uretilen": "vague",
         "dogru": True, "hard_case": False, "mesaj": "x", "hata": None},
        {"test_id": "b", "beklenen": "vague", "uretilen": "neutral",
         "dogru": False, "hard_case": False, "mesaj": "y", "hata": None},
        {"test_id": "c", "beklenen": "skeptical", "uretilen": "ambivalent",
         "dogru": False, "hard_case": True, "mesaj": "z", "hata": None},
    ]
    isabet = report(sonuclar)
    assert abs(isabet - 1 / 3) < 1e-9

    cikti = capsys.readouterr().out
    assert "1/3" in cikti
    assert "vague" in cikti and "skeptical" in cikti
    # Karışan çift ve neutral'a kaçış ayrıca raporlanmalı
    assert "neutral'a kaçan: 1" in cikti


def test_report_survives_all_correct(capsys):
    from eval_process_state import report

    sonuclar = [
        {"test_id": "a", "beklenen": "vague", "uretilen": "vague",
         "dogru": True, "hard_case": False, "mesaj": "x", "hata": None},
    ]
    assert report(sonuclar) == 1.0
    assert "Karışan çiftler" not in capsys.readouterr().out


def test_runner_refuses_mock_provider(monkeypatch):
    """Mock sağlayıcıyla ölçüm sahte sonuç üretirdi."""
    import eval_process_state as ev

    monkeypatch.setenv("CBT_LLM_PROVIDER", "mock")
    monkeypatch.setattr(sys, "argv", ["eval_process_state.py"])
    assert ev.main() == 2


def test_runner_refuses_without_api_key(monkeypatch):
    import eval_process_state as ev

    monkeypatch.delenv("CBT_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["eval_process_state.py"])
    assert ev.main() == 2


# ---------------------------------------------------------------- prompt bütünlüğü

def _prompt():
    from pipeline.intent_classifier import _INTENT_SYSTEM_TR
    return _INTENT_SYSTEM_TR


def test_every_fewshot_example_carries_conversation_state():
    """Şemaya alan eklemek yetmiyor; model örnekleri taklit ediyor.

    İlk ölçümde bu tam olarak böyle kırıldı: alan şemadaydı ama 41
    örneğin hiçbirinde yoktu, model alanı hiç üretmedi, ayrıştırıcı
    eksik alanı "neutral" saydı ve 87 örneğin 25'i sessizce düştü.
    """
    import re

    ornekler = [
        satir for satir in re.findall(r'^\{"primary_module".*$', _prompt(), re.M)
        if '"..."' not in satir  # şema satırı örnek değil
    ]
    assert ornekler, "hiç örnek bulunamadı"
    eksik = [o for o in ornekler if "conversation_state" not in o]
    assert not eksik, f"{len(eksik)} örnekte conversation_state yok"


def test_every_state_has_a_full_json_example():
    """Tanım listesinde geçmek yetmiyor; model çıktı örneklerini taklit ediyor.

    İlk kurulumda 41 örneğin 39'u neutral'dı ve 14 durumun tek bir tam
    çıktı örneği yoktu. Model tanımları okusa da üst üste "neutral"
    gördüğü için oraya kaçıyordu; neutral'a kaçış da hiç kart gelmemesi
    demek, yani en pahalı hata.
    """
    import re

    ornekler = [
        s for s in re.findall(r'^\{"primary_module".*$', _prompt(), re.M)
        if '"..."' not in s
    ]
    kapsanan = {
        re.search(r'"conversation_state":\s*"([^"]+)"', o).group(1) for o in ornekler
    }
    eksik = [d for d in CONVERSATION_STATES if d not in kapsanan]
    assert not eksik, f"tam çıktı örneği olmayan durum: {eksik}"


def test_example_values_are_in_vocabulary():
    """Sözlük dışı bir değer örnekte geçerse model onu üretmeyi öğrenir."""
    import json as _json
    import re

    from pipeline.intent_classifier import MODULES, SUBINTENTS

    for satir in re.findall(r'^\{"primary_module".*$', _prompt(), re.M):
        if '"..."' in satir:
            continue
        d = _json.loads(satir)
        assert d["primary_module"] in MODULES, satir
        assert d["subintent"] in SUBINTENTS, satir
        assert d["conversation_state"] in CONVERSATION_STATES, satir
        assert all(m in MODULES for m in d["secondary_modules"]), satir


def test_failing_states_have_dedicated_examples():
    """İlk ölçümde 0/5 alan durumların prompt'ta örneği olmalı."""
    prompt = _prompt()
    for durum in ["ruminating", "skeptical", "reporting_progress", "returning"]:
        assert prompt.count(durum) >= 2, f"{durum} için örnek yetersiz"


def test_eval_messages_do_not_leak_into_the_prompt():
    """Eval cümlesi few-shot örneği olursa ölçüm kendi kendini kandırır.

    Alt dizge değil, tırnak içinde birebir eşleşme aranıyor: "yani"
    gibi kısa parçalar doğal olarak başka cümlelerin içinde geçer.
    """
    import re

    tirnakli = set(re.findall(r'"([^"\n]{2,})"', _prompt()))
    sizan = [c["user_message_tr"] for c in _cases() if c["user_message_tr"] in tirnakli]
    assert not sizan, f"eval cümlesi prompt'a sızmış: {sizan}"


# ---------------------------------------------------------------- maliyet

def test_cost_model_flags_neutral_as_high():
    """neutral'a kaçış her zaman yüksek maliyetli: hiç kart gelmiyor."""
    from eval_process_state import _maliyet

    assert _maliyet("ruminating", "neutral") == "yuksek"
    assert _maliyet("vague", "neutral") == "yuksek"


def test_cost_model_knows_adjacent_pairs():
    """Komşu kartlar benzer hamle yaptırıyor; bu karışma davranışı bozmuyor."""
    from eval_process_state import _maliyet

    assert _maliyet("own_evidence", "formulating") == "dusuk"
    assert _maliyet("winding_down", "withdrawn") == "dusuk"


def test_cost_model_protects_clinically_costly_states():
    """Güvence arayışı kaçırılırsa güvence verilir ve döngü beslenir."""
    from eval_process_state import _maliyet

    assert _maliyet("reassurance_seeking", "vague") == "yuksek"
    assert _maliyet("technique_failed", "skeptical") == "yuksek"


def test_high_cost_states_all_have_cards():
    """Maliyetli sayılan durumun karşılığında kart yoksa etiket boşa çıkar."""
    from eval_process_state import YUKSEK_MALIYET
    from pipeline import process_cards as pc

    pc.reset_cache()
    kapsanan = {c.state for c in pc.all_cards()}
    for durum in YUKSEK_MALIYET:
        assert durum in kapsanan, f"{durum} yüksek maliyetli ama kartı yok"


def test_corrected_label_is_documented():
    """Sonucu gördükten sonra değiştirilen etiket iz bırakmalı.

    Aksi hâlde ölçüm sonrası etiket düzenlemek fark edilmez ve oran
    sessizce şişer.
    """
    duzeltilmis = [c for c in _cases() if "DÜZELTME" in c.get("notes", "")]
    assert duzeltilmis, "düzeltilen etiket işaretlenmemiş"
    for c in duzeltilmis:
        assert "önce" in c["notes"], f"{c['test_id']} eski etiketi yazmıyor"
