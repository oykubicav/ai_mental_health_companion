"""Süreç kartları — konuşmanın nasıl yürütüleceği.

Bu kartlar seans davranışını belirliyor ve içerik kartlarından farklı bir
risk taşıyorlar: yanlış bir süreç kartı yanlış bilgi vermez, ama kullanıcıyı
sorgulanıyormuş gibi hissettirebilir ya da sahte bir yakınlık kurdurabilir.
O yüzden yapıları ve kaynak bağları burada sabitleniyor.

42 kartın tamamı 2026-09-08'de klinisyen incelemesinden geçti, dolayısıyla
artık içerik kartlarıyla aynı yayın kapısına tabiler.
"""

import csv
import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))

from pipeline import process_cards as pc  # noqa: E402
from pipeline.intent_classifier import CONVERSATION_STATES, DISTRESS_STATE  # noqa: E402


def _ham():
    yol = BASE / "cards/process_cards.jsonl"
    return [json.loads(l) for l in open(yol, encoding="utf-8") if l.strip()]


def _kaynaklar():
    with open(BASE / "registry/source_registry.csv", encoding="utf-8") as f:
        return {r["source_id"] for r in csv.DictReader(f)}


def test_cards_load():
    assert len(_ham()) >= 40


def test_ids_unique():
    ids = [c["id"] for c in _ham()]
    assert len(ids) == len(set(ids))


def test_schema_complete():
    for c in _ham():
        for alan in ("id", "state", "title_tr", "principle_tr", "do_tr", "avoid_tr", "source_refs"):
            assert c.get(alan) not in (None, "", []), f"{c['id']} → {alan} boş"


def test_every_card_cites_a_real_source():
    kaynaklar = _kaynaklar()
    for c in _ham():
        for ref in c["source_refs"]:
            assert ref in kaynaklar, f"{c['id']} → kayıtsız kaynak {ref}"


def test_states_are_known():
    gecerli = set(CONVERSATION_STATES) | {"any", DISTRESS_STATE}
    for c in _ham():
        assert c["state"] in gecerli, f"{c['id']} → tanımsız durum {c['state']}"


def test_every_state_has_a_card():
    """Sınıflandırıcının üretebildiği her durumun karşılığı olmalı.

    Karşılığı olmayan bir durum sessizce boş dönerdi: sınıflandırma
    doğru çalışsa bile davranış değişmezdi.
    """
    kapsanan = {c["state"] for c in _ham()}
    for durum in CONVERSATION_STATES:
        if durum == "neutral":
            continue  # nötr durumda yalnızca genel duruş kartları veriliyor
        assert durum in kapsanan, f"{durum} durumu için kart yok"


def test_distress_cards_exist():
    """Egzersiz kapatıldığında devreye girecek kartlar olmalı."""
    assert len([c for c in _ham() if c["state"] == DISTRESS_STATE]) >= 2


def test_blocks_exercise_overrides_conversation_state():
    """Teknik önermemek konuşma tercihi değil, güvenlik kararı.

    Sınıflandırıcı "kullanıcı yön istiyor" dese bile, güvenlik kapısı
    egzersizi kapattıysa yön veren kart değil sıkıntı kartı gelmeli.
    """
    pc.reset_cache()
    secim = pc.select("directive_request", turn_index=0, blocks_exercise=True)
    assert secim[0].state == DISTRESS_STATE
    assert all(c.state != "directive_request" for c in secim)


def test_distress_state_not_selectable_from_classifier():
    """Sınıflandırıcı bu durumu üretemez; yalnızca güvenlik kapısı açar."""
    assert DISTRESS_STATE not in CONVERSATION_STATES
    pc.reset_cache()
    secim = pc.select(DISTRESS_STATE, turn_index=0, blocks_exercise=False)
    assert all(c.state == "any" for c in secim)


def test_stance_cards_exist():
    """Her turda geçerli duruş kartları olmalı — nötr durumun tek dayanağı."""
    assert len([c for c in _ham() if c["state"] == "any"]) >= 3


# ---------------------------------------------------------------- seçim

def test_select_returns_state_card_and_stance():
    pc.reset_cache()
    secim = pc.select("self_critical", turn_index=0)
    assert len(secim) == 2
    assert secim[0].state == "self_critical"
    assert secim[1].state == "any"


def test_select_neutral_gives_only_stance():
    pc.reset_cache()
    secim = pc.select("neutral", turn_index=0)
    assert [c.state for c in secim] == ["any"]


def test_select_rotates_within_state():
    """Aynı durum tekrar ederse kart değişmeli.

    Sabit kalsaydı model aynı hamleyi tekrarlar, konuşma yerinde sayardı.
    """
    pc.reset_cache()
    ilk = pc.select("ambivalent", turn_index=0)[0]
    ikinci = pc.select("ambivalent", turn_index=1)[0]
    assert ilk.id != ikinci.id


def test_crisis_route_gets_no_process_cards():
    """Kriz yolunda cevabı güvenlik şablonu belirliyor."""
    pc.reset_cache()
    assert pc.select("self_critical", turn_index=0, allow_cbt=False) == []


def test_unknown_state_falls_back_to_stance():
    pc.reset_cache()
    secim = pc.select("boyle_bir_durum_yok", turn_index=0)
    assert [c.state for c in secim] == ["any"]


def test_none_state_is_safe():
    pc.reset_cache()
    assert all(c.state == "any" for c in pc.select(None))


def test_prompt_block_has_no_card_ids():
    """Kart kimliği prompt'a sızmamalı — modelin tekrarlaması riski var."""
    pc.reset_cache()
    metin = pc.format_for_prompt(pc.select("withdrawn", turn_index=0))
    assert metin
    for c in pc.all_cards():
        assert c.id not in metin


def test_prompt_block_empty_when_no_cards():
    assert pc.format_for_prompt([]) == ""


def test_layer_can_be_disabled(monkeypatch):
    """Kartlar onaysız; sorun çıkarsa tek değişkenle kapanabilmeli."""
    monkeypatch.setenv("CBT_PROCESS_CARDS", "0")
    assert pc.enabled() is False
    monkeypatch.setenv("CBT_PROCESS_CARDS", "1")
    assert pc.enabled() is True


# ---------------------------------------------------------------- denetim

def test_audit_tracks_process_cards():
    from audit_review_status import audit_process

    suruklenmis, onaysiz, toplam = audit_process()
    assert toplam == len(_ham())
    assert suruklenmis == [], f"onaydan sonra değişmiş süreç kartı: {suruklenmis}"
    assert onaysiz == [], f"onaysız süreç kartı: {onaysiz}"


def test_process_cards_are_in_the_release_gate():
    """Onaysız bir süreç kartı yayını durdurmalı.

    İnceleme tamamlanana kadar bu kartlar kapının dışındaydı. Artık
    içerdeler; kapı gerçekten kapanıyor mu diye bakılıyor, çünkü
    unutulan bir muafiyet sessizce onaysız kart geçirir.
    """
    import audit_review_status as a

    _, onaysiz, _ = a.audit_process()
    assert onaysiz == []
    assert a.main() == 0


def test_process_cards_do_not_break_release_gate():
    """Onaysız süreç kartları içerik kartlarının yayın kapısını kırmamalı."""
    from audit_review_status import audit

    _, onaysiz, n_cbt, n_saf = audit()
    assert onaysiz == []
    assert (n_cbt, n_saf) == (180, 19)
