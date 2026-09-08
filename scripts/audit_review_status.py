"""Klinisyen onayının içerik sürümüne bağlı kalmasını denetler.

Her kartta onaylanan içeriğin hash'i saklanıyor (reviewed_content_hash).
Kart metni sonradan değiştiyse hash tutmaz ve onay geçersizdir — kart
"onaylı" görünmeye devam etse bile. Bu script o sürüklenmeyi yakalar.

Kullanım:
    python scripts/audit_review_status.py            # raporla
    python scripts/audit_review_status.py --strict   # sürüklenme varsa 1 ile çık (CI)

Bir kartı bilerek değiştirdiysen onayı düşür:
    review_status: "needs_review", clinician_reviewed_at: null
ve klinisyen yeniden okuduğunda hash'i güncelle.
"""

import hashlib
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _cbt_hash(card: dict) -> str:
    return _h(card["title_tr"] + "\n" + card["content_tr"])


def _process_hash(card: dict) -> str:
    return _h(
        card["title_tr"]
        + "\n"
        + card["principle_tr"]
        + "\n"
        + "\n".join(card.get("do_tr", []))
        + "\n"
        + "\n".join(card.get("avoid_tr", []))
    )


def _safety_hash(card: dict) -> str:
    return _h(
        card["must_do_tr"]
        + "\n"
        + "\n".join(card["must_not_do_tr"])
        + "\n"
        + card["safe_response_template_tr"]
    )


def audit() -> tuple[list[str], list[str], int, int]:
    """(sürüklenmiş, onaysız, toplam_cbt, toplam_safety) döner.

    Süreç kartları burada yok: onlar henüz klinisyen incelemesinden
    geçmedi ve yayın kapısını kırmamalılar. Durumları audit_process()
    ile ayrıca raporlanıyor.
    """
    suruklenmis: list[str] = []
    onaysiz: list[str] = []

    cbt = [json.loads(l) for l in open(BASE / "cards/cbt_cards.jsonl", encoding="utf-8") if l.strip()]
    for c in cbt:
        if c.get("review_status") != "clinician_reviewed" or not c.get("clinician_reviewed_at"):
            onaysiz.append(c["id"])
        elif c.get("reviewed_content_hash") != _cbt_hash(c):
            suruklenmis.append(c["id"])

    saf = [json.loads(l) for l in open(BASE / "cards/safety_cards.jsonl", encoding="utf-8") if l.strip()]
    for c in saf:
        if c.get("review_status") != "clinician_reviewed" or not c.get("clinician_reviewed_at"):
            onaysiz.append(c["card_id"])
        elif c.get("reviewed_content_hash") != _safety_hash(c):
            suruklenmis.append(c["card_id"])

    return suruklenmis, onaysiz, len(cbt), len(saf)


def audit_process() -> tuple[list[str], list[str], int]:
    """Süreç kartları — (sürüklenmiş, onaysız, toplam).

    42 kartın tamamı incelemeden geçtiği için (2026-09-08) bu kartlar
    artık içerik kartlarıyla aynı yayın kapısına tabi: onaysız bir kart
    da, onaydan sonra değişmiş bir kart da yayını durdurur.
    """
    yol = BASE / "cards/process_cards.jsonl"
    if not yol.exists():
        return [], [], 0

    kartlar = [json.loads(l) for l in open(yol, encoding="utf-8") if l.strip()]
    suruklenmis: list[str] = []
    onaysiz: list[str] = []

    for c in kartlar:
        if c.get("review_status") != "clinician_reviewed" or not c.get("clinician_reviewed_at"):
            onaysiz.append(c["id"])
        elif c.get("reviewed_content_hash") != _process_hash(c):
            suruklenmis.append(c["id"])

    return suruklenmis, onaysiz, len(kartlar)


def main() -> int:
    strict = "--strict" in sys.argv
    suruklenmis, onaysiz, n_cbt, n_saf = audit()

    print(f"Kart: {n_cbt} CBT + {n_saf} güvenlik")
    print(f"Onaydan sonra değişmiş (hash tutmuyor): {len(suruklenmis)}")
    for cid in suruklenmis:
        print(f"  DEĞİŞMİŞ  {cid}")
    print(f"Onaysız: {len(onaysiz)}")
    for cid in onaysiz:
        print(f"  ONAYSIZ   {cid}")

    p_suruklenmis, p_onaysiz, n_proc = audit_process()
    if n_proc:
        print(f"\nSüreç kartı: {n_proc}")
        for cid in p_suruklenmis:
            print(f"  DEĞİŞMİŞ  {cid}")
        for cid in p_onaysiz:
            print(f"  ONAYSIZ   {cid}")

    sorun = bool(suruklenmis or onaysiz or p_suruklenmis or p_onaysiz)
    if not sorun:
        print("\n✓ Bütün kartlar onaylı ve onaylandığı hâliyle duruyor.")
        return 0
    if strict:
        print("\n✗ Onay sürüklenmesi var — bu hâliyle yayına çıkılmamalı.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
