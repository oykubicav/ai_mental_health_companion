"""Sohbetteki egzersiz bağlantıları gerçek kartlara bağlı olmalı.

frontend/lib/exerciseLinks.ts kart kimliklerini elle listeliyor. Bir kart
yeniden adlandırılır ya da silinirse bağlantı sessizce ölür — kullanıcı
hiçbir şey görmez, biz de fark etmeyiz. Bu test onu yakalar.
"""

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LINKS = BASE / "frontend/lib/exerciseLinks.ts"


def _mapped_card_ids() -> list[str]:
    src = LINKS.read_text(encoding="utf-8")
    block = src.split("CARD_TO_TOOL: Record<string, ExerciseLink> = {", 1)[1]
    block = block.split("\n};", 1)[0]
    return re.findall(r"^\s*([a-z0-9_]+):", block, re.M)


def _card_ids() -> set[str]:
    return {
        json.loads(l)["id"]
        for l in open(BASE / "cards/cbt_cards.jsonl", encoding="utf-8")
        if l.strip()
    }


def test_every_mapped_card_exists():
    eksik = [c for c in _mapped_card_ids() if c not in _card_ids()]
    assert eksik == [], f"exerciseLinks.ts'te olmayan kart: {eksik}"


def test_mapping_is_not_empty_and_has_no_duplicates():
    ids = _mapped_card_ids()
    assert len(ids) > 20
    assert len(ids) == len(set(ids)), "aynı kart iki kez eşlenmiş"


def test_referenced_exercise_pages_exist():
    src = LINKS.read_text(encoding="utf-8")
    for yol in set(re.findall(r'href: "(/egzersizler/[a-z-]+)"', src)):
        sayfa = BASE / "frontend/app" / yol.lstrip("/") / "page.tsx"
        assert sayfa.exists(), f"{yol} sayfası yok"
