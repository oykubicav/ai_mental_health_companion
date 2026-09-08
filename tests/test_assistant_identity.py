"""Sistem promptundaki kimlik bloğu gerçekle uyumlu kalmalı.

Modele "uygulamada şunlar var" diye bir liste veriyoruz. Bir bölüm
kaldırılır ya da yeniden adlandırılırsa model olmayan bir yere
yönlendirmeye devam eder — kullanıcı için bu, hiç yönlendirmemekten kötü.
Bu test o sapmayı yakalar.
"""

from pathlib import Path

from pipeline.composer import SYSTEM_PROMPT_TR

BASE = Path(__file__).resolve().parent.parent
FRONTEND = BASE / "frontend/app"


def test_prompt_names_the_assistant():
    assert "Adın Neva" in SYSTEM_PROMPT_TR


def test_prompt_declares_it_is_ai():
    assert "yapay zekâ" in SYSTEM_PROMPT_TR


def test_promised_sections_exist_as_pages():
    """Kimlik bloğunda adı geçen her bölümün bir sayfası olmalı."""
    for bolum, sayfa in [
        ("Egzersizler", "egzersizler"),
        ("Günlük", "gunluk"),
        ("Gelişimim", "progress"),
        ("Konular", "cards"),
        ("Gizlilik", "gizlilik"),
    ]:
        assert bolum in SYSTEM_PROMPT_TR, f"{bolum} promptta anılmıyor"
        assert (FRONTEND / sayfa / "page.tsx").exists(), f"/{sayfa} sayfası yok"


def test_prompt_blocks_reading_the_journal():
    """Günlük modele hiç gelmiyor; 'günlüğüne bakalım' diyemez."""
    assert "günlüğü SEN OKUMUYORSUN" in SYSTEM_PROMPT_TR


def test_prompt_lists_absent_features():
    """Olmayan özellikler açıkça sayılmalı ki model uydurmasın."""
    for yok in ["Bildirim", "seri", "rozet"]:
        assert yok in SYSTEM_PROMPT_TR, f"'{yok}' yokluk listesinde değil"
