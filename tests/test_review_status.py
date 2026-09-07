"""Klinisyen onayı sürüme bağlı — içerik değişince onay düşmeli.

Bu test yayın kapısı: kartlardan biri onaylandığı hâlinden farklıysa ya da
onaysızsa suite kırmızı. Bir kartı bilerek değiştirdiysen review_status'u
needs_review yap; klinisyen tekrar okuyunca hash güncellenir.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from audit_review_status import audit  # noqa: E402


def test_every_card_is_clinician_reviewed():
    _, onaysiz, _, _ = audit()
    assert onaysiz == [], f"Onaysız kartlar: {onaysiz}"


def test_no_card_changed_after_review():
    suruklenmis, _, _, _ = audit()
    assert suruklenmis == [], (
        f"Onaydan sonra değişmiş kartlar: {suruklenmis}. "
        "review_status'u needs_review yap ve yeniden inceleme iste."
    )


def test_card_counts_match_privacy_page():
    """/gizlilik sayfası '180 bilgi kartı ve 19 güvenlik kartı' diyor."""
    _, _, n_cbt, n_saf = audit()
    assert n_cbt == 180
    assert n_saf == 19
