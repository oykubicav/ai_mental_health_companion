"""Modül eval setinin ve koşucusunun kendisi.

Koşu gerçek Haiku çağrısı yapıyor; burada onu çalıştırmıyoruz. Test edilen
şey ölçüm aracı: set doğru mu kurulmuş, maliyet modeli doğru mu ayırıyor.
Bozuk bir ölçüm aracı ölçüm yapmamaktan kötüdür, yanlış güven verir.
"""

import json
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))

from pipeline.intent_classifier import MODULES, SUBINTENTS  # noqa: E402

SET_PATH = BASE / "evals" / "module_test_set.jsonl"


def _cases():
    with open(SET_PATH, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


# ---------------------------------------------------------------- set

def test_set_exists_and_is_substantial():
    assert len(_cases()) >= 80


def test_ids_unique():
    ids = [c["test_id"] for c in _cases()]
    assert len(ids) == len(set(ids))


def test_messages_are_distinct():
    m = [c["user_message_tr"] for c in _cases()]
    assert len(m) == len(set(m))


def test_schema():
    for c in _cases():
        assert c["test_id"]
        assert c["user_message_tr"].strip()
        assert isinstance(c.get("hard_case", False), bool)


def test_labels_are_producible():
    """Sınıflandırıcının üretemediği etiket, hiç geçilemeyecek test demek."""
    for c in _cases():
        assert c["expected_module"] in MODULES, c["test_id"]
        assert c["expected_subintent"] in SUBINTENTS, c["test_id"]


def test_every_module_is_covered():
    """Ölçülmeyen modül, körlüğün sürmesi demek."""
    kapsanan = {c["expected_module"] for c in _cases()}
    eksik = [m for m in MODULES if m not in kapsanan]
    assert not eksik, f"örneği olmayan modül: {eksik}"


def test_every_subintent_is_covered():
    kapsanan = {c["expected_subintent"] for c in _cases()}
    eksik = [s for s in SUBINTENTS if s not in kapsanan]
    assert not eksik, f"örneği olmayan subintent: {eksik}"


def test_each_module_has_enough_examples():
    """Tek örnekle ölçülen modülde isabet ya %0 ya %100 — bilgi vermez."""
    sayim = Counter(c["expected_module"] for c in _cases())
    for modul, n in sayim.items():
        assert n >= 4, f"{modul} yalnızca {n} örnek"


def test_hard_cases_are_marked_and_few():
    zor = [c for c in _cases() if c.get("hard_case")]
    assert zor, "hiç zor vaka işaretlenmemiş"
    assert len(zor) < len(_cases()) * 0.25


def test_hard_cases_have_notes():
    for c in _cases():
        if c.get("hard_case"):
            assert c.get("notes", "").strip(), f"{c['test_id']} gerekçesiz"


def test_no_leak_into_the_prompt():
    """Eval cümlesi few-shot örneği olursa ölçüm kendi kendini kandırır."""
    import re

    from pipeline.intent_classifier import _INTENT_SYSTEM_TR

    tirnakli = set(re.findall(r'"([^"\n]{2,})"', _INTENT_SYSTEM_TR))
    sizan = [c["user_message_tr"] for c in _cases() if c["user_message_tr"] in tirnakli]
    assert not sizan, f"prompt'a sızmış: {sizan}"


def test_no_overlap_with_the_state_set():
    """İki set ayrı kalsın; aynı cümle iki eksende ölçüm bağımsızlığını bozar."""
    yol = BASE / "evals" / "process_state_test_set.jsonl"
    durum = {json.loads(l)["user_message_tr"] for l in open(yol, encoding="utf-8") if l.strip()}
    ortak = [c["user_message_tr"] for c in _cases() if c["user_message_tr"] in durum]
    assert not ortak, f"iki sette birden: {ortak}"


# ---------------------------------------------------------------- maliyet

def test_missing_safety_is_the_worst_error():
    """Kriz mesajını sıradan bir CBT konusu sanmak kategorik olarak farklı."""
    from eval_module import _maliyet

    assert _maliyet("safety", "depression") == "yuksek"
    assert _maliyet("safety", "unknown") == "yuksek"


def test_missing_boundary_is_high_cost():
    """Tanı ya da ilaç sorusuna CBT cevabı vermek sınır ihlali."""
    from eval_module import _maliyet

    assert _maliyet("boundary", "gad") == "yuksek"


def test_boundary_routed_to_safety_is_not_a_high_cost_miss():
    """Sınır sorusunun kriz yoluna düşmesi aşırı temkin, kaçırma değil.

    İlk ölçümde "ilacımın dozunu kendim artırsam olur mu" → safety çıktı ve
    maliyet modeli bunu yüksek saydı. İki yol da cevabı reddedip hekime
    yönlendiriyor; pahalı olan şey sorunun CBT içeriğiyle cevaplanmasıydı,
    o da olmuyor. Sıralama hatasıydı, düzeltildi.
    """
    from eval_module import _maliyet

    assert _maliyet("boundary", "safety") == "orta"
    assert _maliyet("boundary", "depression") == "yuksek"
    # Ters yön hâlâ en pahalısı: kriz mesajı sınır sanılırsa 112 hiç geçmez.
    assert _maliyet("safety", "boundary") == "yuksek"


def test_false_safety_is_not_as_costly_as_missing_it():
    """Gereksiz 112 rahatsız edici ama tehlikeli değil — asimetri korunmalı."""
    from eval_module import _maliyet

    assert _maliyet("insomnia", "safety") == "orta"
    assert _maliyet("safety", "insomnia") == "yuksek"


def test_unknown_escape_is_medium_not_high():
    """neutral'dan farklı: modül bilinmezse retrieval filtresiz çalışır.

    conversation_state neutral olduğunda süreç kartı hiç gelmiyordu; burada
    katman kapanmıyor, yalnızca daralmıyor. Maliyet modeli bu farkı bilmezse
    iki eksen yanlış biçimde aynı sayılır.
    """
    from eval_module import _maliyet

    assert _maliyet("panic", "unknown") == "orta"


def test_clinical_neighbours_are_low_cost():
    from eval_module import _maliyet

    assert _maliyet("panic", "health_anxiety") == "dusuk"
    assert _maliyet("depression", "low_self_esteem") == "dusuk"


def test_neighbour_pairs_are_real_modules():
    from eval_module import KOMSU

    for cift in KOMSU:
        for m in cift:
            assert m in MODULES, f"tanımsız modül komşulukta: {m}"


# ---------------------------------------------------------------- koşucu

def test_report_counts_correctly(capsys):
    from eval_module import report

    sonuclar = [
        {"test_id": "a", "beklenen": "panic", "uretilen": "panic", "dogru": True,
         "beklenen_subintent": "crisis", "uretilen_subintent": "crisis",
         "subintent_dogru": True, "guven": 0.9, "hard_case": False,
         "mesaj": "x", "hata": None},
        {"test_id": "b", "beklenen": "safety", "uretilen": "depression", "dogru": False,
         "beklenen_subintent": "crisis", "uretilen_subintent": "ambiguous_symptom",
         "subintent_dogru": False, "guven": 0.4, "hard_case": False,
         "mesaj": "y", "hata": None},
    ]
    isabet = report(sonuclar)
    assert abs(isabet - 0.5) < 1e-9

    cikti = capsys.readouterr().out
    assert "1/2" in cikti
    assert "yüksek" in cikti


def test_runner_refuses_mock_provider(monkeypatch):
    import eval_module as ev

    monkeypatch.setenv("CBT_LLM_PROVIDER", "mock")
    monkeypatch.setattr(sys, "argv", ["eval_module.py"])
    assert ev.main() == 2


def test_runner_refuses_without_api_key(monkeypatch):
    import eval_module as ev

    monkeypatch.delenv("CBT_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["eval_module.py"])
    assert ev.main() == 2


def test_corrected_label_is_documented():
    """Sonucu gördükten sonra değiştirilen etiket iz bırakmalı.

    Aksi hâlde ölçüm sonrası etiket düzenlemek fark edilmez ve oran
    sessizce şişer. Durum setinde de aynı kural işliyor.
    """
    duzeltilmis = [c for c in _cases() if "DÜZELTME" in c.get("notes", "")]
    assert duzeltilmis, "düzeltilen etiket işaretlenmemiş"
    for c in duzeltilmis:
        assert "önce" in c["notes"], f"{c['test_id']} eski etiketi yazmıyor"
