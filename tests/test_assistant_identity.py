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


# ---------------------------------------------------------------- süreç katmanı

def test_safety_rules_stay_in_the_prompt():
    """Güvenlik kuralları veri katmanına taşınmadı ve taşınmamalı.

    Konuşma tekniği duruma göre seçiliyor; "tanı koyma, ilaç önerme"
    seçilecek bir şey değil. Süreç katmanı kapatılsa bile bunlar
    yerinde durmalı.
    """
    for kural in ["Tanı KOYMA", "İlaç önerme", "112"]:
        assert kural in SYSTEM_PROMPT_TR, f"güvenlik kuralı prompt'tan düşmüş: {kural}"


def test_behaviour_rules_are_condensed_not_duplicated():
    """Süreç kartlarına taşınan bloklar prompt'ta özet hâlde kalmalı.

    Tamamen silinseydi CBT_PROCESS_CARDS=0 ile katman kapatıldığında
    kural da kaybolurdu; uzun hâlleriyle kalsaydı kartlarla çift olurdu.
    Ölçüt: blok var ama kısa.
    """

    for baslik in [
        "SORU SORMA DENGESİ",
        "KISA CEVAPLARI OLDUĞU GİBİ KABUL ET",
        "GÜVENLİK KONTROL SORUSU REDDEDİLDİYSE",
    ]:
        i = SYSTEM_PROMPT_TR.index(baslik)
        blok = SYSTEM_PROMPT_TR[i:i + 600].split("\n\n")[0]
        assert len(blok.split("\n")) <= 7, f"{baslik} bloğu hâlâ uzun"


def test_question_frequency_rule_is_stated_once():
    """Aynı kural iki başlık altında tekrarlanmamalı."""
    assert "SORU SIKLIĞI" not in SYSTEM_PROMPT_TR
    assert SYSTEM_PROMPT_TR.count("SORU SORMA DENGESİ") == 1


def test_prompt_has_no_editing_notes():
    """Prompt'a düzenleme notu sızmamalı.

    "# _COMPOSER_SYSTEM_TR içinde uygun bir yere ekle:" satırı üç tırnağın
    içinde kalmıştı ve her turda modele gidiyordu — üstelik o adda bir
    değişken yok. Modele kendi kaynak kodundan bahsetmek en iyi ihtimalle
    gürültü, en kötüsünde sisteme dair sızdırılabilir bilgi.
    """
    from pipeline.composer import SYSTEM_PROMPT_TR

    for satir in SYSTEM_PROMPT_TR.splitlines():
        s = satir.strip()
        assert not s.startswith("#"), f"prompt'ta kod yorumu: {s}"
    for terim in ["_COMPOSER_SYSTEM_TR", "SYSTEM_PROMPT_TR", "TODO", "FIXME"]:
        assert terim not in SYSTEM_PROMPT_TR, f"prompt'ta iç referans: {terim}"
