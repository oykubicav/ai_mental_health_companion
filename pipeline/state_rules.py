"""Konuşma durumu için deterministik kural katmanı.

Güvenlik sınıflandırıcısıyla aynı gerekçe: bazı durumları kaçırmanın
maliyeti asimetrik, o yüzden karar LLM'e bırakılmıyor. Ölçümde üç koşunun
üçünde de düşük çıkan durumlar (technique_failed, ruminating,
reassurance_seeking) Türkçede belirleyici dilbilgisel işaretler taşıyor —
teyit sorusu, deneme+olumsuzluk, tekrar belirteci. Bunlar için model
gerekmiyor.

Sıra: kural eşleşirse o kazanır, eşleşmezse LLM'in kararı geçerli.

Kurallar tek tek eval cümlelerine değil dil işaretlerine yazıldı; yine de
eval seti üzerinde ayarlandıkları için ölçüm bir miktar iyimser. Yeni
cümlelerle doğrulanması gerekiyor.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional

_RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "conversation_state_rules.json"

_COMPILED: Optional[List[dict]] = None


def _compile() -> List[dict]:
    global _COMPILED
    if _COMPILED is not None:
        return _COMPILED

    if not _RULES_PATH.exists():
        _COMPILED = []
        return _COMPILED

    ham = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
    derlenmis = []
    for kural in ham.get("rules", []):
        derlenmis.append({
            "state": kural["state"],
            "why": kural.get("why", ""),
            # any: herhangi biri eşleşirse yeter
            "any": [re.compile(p, re.I) for p in kural.get("any", [])],
            # all: hepsi eşleşmeli (deneme + olumsuz sonuç gibi bileşik durumlar)
            "all": [re.compile(p, re.I) for p in kural.get("all", [])],
            # not: bunlardan biri varsa kural iptal
            "not": [re.compile(p, re.I) for p in kural.get("not", [])],
        })
    _COMPILED = derlenmis
    return _COMPILED


def reset_cache() -> None:
    global _COMPILED
    _COMPILED = None


def match(user_message: str) -> Optional[str]:
    """Mesaja uyan durumu döndürür, yoksa None.

    Birden fazla kural eşleşirse dosyadaki ilk kural kazanıyor; sıralama
    maliyet önceliğine göre yapıldı.
    """
    if not user_message:
        return None

    for kural in _compile():
        if any(p.search(user_message) for p in kural["not"]):
            continue
        if kural["all"] and not all(p.search(user_message) for p in kural["all"]):
            continue
        if kural["any"] and not any(p.search(user_message) for p in kural["any"]):
            continue
        if not kural["all"] and not kural["any"]:
            continue
        return kural["state"]

    return None


def covered_states() -> List[str]:
    return [k["state"] for k in _compile()]
