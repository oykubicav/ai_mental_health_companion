"""Süreç kartları — konuşmanın nasıl yürütüleceği.

İçerik kartları "panik hakkında ne söylenir" sorusunu cevaplıyor. Bunlar
"kullanıcı direniyorken ne yapılır" sorusunu cevaplıyor. Konuya göre değil,
konuşma durumuna göre getiriliyorlar.

Bu ayrımın sebebi şu: seans davranışı bugüne kadar system prompt'ta elle
yazılmış kurallardı — kaynaksız, klinisyen onayından geçmemiş, denetlenemez.
Kartlara taşınınca aynı sürüm kilidi (reviewed_content_hash) burada da işliyor.

Kartların bir kısmı klinisyen onayından geçti, bir kısmı beklemede
(scripts/audit_review_status.py ikisini ayrı raporluyor). Onay durumu ne
olursa olsun bu katmanın güvenlik kararlarına etkisi yok: kriz yolunda
hiç devreye girmiyor ve CBT_PROCESS_CARDS=0 ile tamamen kapatılabiliyor.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

_CARDS_PATH = Path(__file__).resolve().parent.parent / "cards" / "process_cards.jsonl"

# Duruma özel kartın yanında her zaman geçerli duruş kartlarından da
# bir tane veriliyor; bunlar "any" durumunda tutuluyor.
_ANY = "any"
_NEUTRAL = "neutral"
# Konuşma durumundan bağımsız: güvenlik kapısı egzersizi kapattığında
# devreye giren kartlar. Sınıflandırıcı ne derse desin bunlar öne geçiyor.
_DISTRESS = "distress_no_exercise"

# Bir turda composer'a en fazla kaç süreç kartı girer. Az tutuluyor:
# prompt'un yarısı davranış talimatı olursa içerik kartları bastırılıyor.
MAX_PER_TURN = 2


@dataclass
class ProcessCard:
    id: str
    state: str
    title_tr: str
    principle_tr: str
    do_tr: List[str]
    avoid_tr: List[str]
    example_tr: str
    source_refs: List[str]
    review_status: str


_BY_STATE: Optional[Dict[str, List[ProcessCard]]] = None


def _load() -> Dict[str, List[ProcessCard]]:
    global _BY_STATE
    if _BY_STATE is not None:
        return _BY_STATE

    by_state: Dict[str, List[ProcessCard]] = {}
    if _CARDS_PATH.exists():
        with open(_CARDS_PATH, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                card = ProcessCard(
                    id=d["id"],
                    state=d["state"],
                    title_tr=d["title_tr"],
                    principle_tr=d["principle_tr"],
                    do_tr=d.get("do_tr", []),
                    avoid_tr=d.get("avoid_tr", []),
                    example_tr=d.get("example_tr", ""),
                    source_refs=d.get("source_refs", []),
                    review_status=d.get("review_status", "needs_review"),
                )
                by_state.setdefault(card.state, []).append(card)

    _BY_STATE = by_state
    return _BY_STATE


def reset_cache() -> None:
    """Testler kart dosyasını değiştirdiğinde çağrılır."""
    global _BY_STATE
    _BY_STATE = None


def all_cards() -> List[ProcessCard]:
    return [c for cards in _load().values() for c in cards]


def _rotating(cards: List[ProcessCard], turn_index: int) -> Optional[ProcessCard]:
    """Aynı durum tekrar ettiğinde farklı kart ver.

    Tek kart sabitlenirse model aynı hamleyi tekrarlıyor ve konuşma
    yerinde sayıyor; bu zaten en sık şikâyet edilen davranış.
    """
    if not cards:
        return None
    return cards[turn_index % len(cards)]


def select(
    conversation_state: Optional[str],
    turn_index: int = 0,
    allow_cbt: bool = True,
    blocks_exercise: bool = False,
) -> List[ProcessCard]:
    """Bu tur için süreç kartlarını seçer.

    Kriz yolunda (allow_cbt=False) hiçbir şey dönmüyor: orada cevabı
    güvenlik şablonu belirliyor, konuşma tekniği devrede değil.

    blocks_exercise=True — destekleyici ama egzersizsiz yol. Burada
    sınıflandırıcının bulduğu duruma bakılmıyor: teknik önermemek
    konuşma tercihi değil, güvenlik kararı.
    """
    if not allow_cbt:
        return []

    by_state = _load()
    secilen: List[ProcessCard] = []

    if blocks_exercise:
        kart = _rotating(by_state.get(_DISTRESS, []), turn_index)
        if kart is not None:
            secilen.append(kart)
    else:
        durum = conversation_state or _NEUTRAL
        if durum not in (_NEUTRAL, _ANY, _DISTRESS):
            ozel = _rotating(by_state.get(durum, []), turn_index)
            if ozel is not None:
                secilen.append(ozel)

    genel = _rotating(by_state.get(_ANY, []), turn_index)
    if genel is not None:
        secilen.append(genel)

    return secilen[:MAX_PER_TURN]


def format_for_prompt(cards: List[ProcessCard]) -> str:
    """Composer prompt'una giren blok. Kart kimliği yazılmıyor."""
    if not cards:
        return ""

    parcalar = ["KONUŞMA DURUMU — bu tur için yaklaşım:"]
    for c in cards:
        parcalar.append(f"\n[{c.title_tr}]")
        parcalar.append(c.principle_tr)
        if c.do_tr:
            parcalar.append("Yap: " + " ".join(f"({i+1}) {x}" for i, x in enumerate(c.do_tr)))
        if c.avoid_tr:
            parcalar.append("Yapma: " + " ".join(f"({i+1}) {x}" for i, x in enumerate(c.avoid_tr)))
        if c.example_tr:
            parcalar.append(f"Örnek ton: {c.example_tr}")

    parcalar.append(
        "\nBu blok bir davranış yönergesidir, kullanıcıya anlatılacak içerik değildir. "
        "Örnek cümleyi olduğu gibi kopyalama."
    )
    return "\n".join(parcalar)


def enabled() -> bool:
    """Süreç katmanı kapatılabilir olmalı.

    Kartlar henüz klinisyen onayından geçmedi; sorun çıkarsa tek bir
    ortam değişkeniyle devre dışı bırakılabiliyor.
    """
    return os.environ.get("CBT_PROCESS_CARDS", "1") != "0"
