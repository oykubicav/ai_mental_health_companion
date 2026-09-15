"""Güvenlik katmanı gömme bayrağını dinlememeli.

CBT_PREFER_ST=1 ile ölçüm (2026-09-09, 73 vakalık retrieval seti):

    retrieval_hit_rate   80.0% → 87.7%   (+7.7)
    safety_recall        88.2% → 61.4%  (-26.8)

Sebep, eşiklerin ölçeğe bağlı olması. TF-IDF karakter n-gramı benzerlikleri
0.05–0.20 aralığında toplanıyor; sentence-transformers 0.3–0.9 civarında
üretiyor. Layer 3 eşikleri TF-IDF dağılımına göre ayarlandığı için ST'ye
geçince aynı sayı başka bir anlama geliyor ve riskli mesajlar eşiğin altında
kalıyor — 57 riskli vakanın 22'si.

Retriever'ın eşiği yok, yalnızca sıralıyor; orada daha iyi gömme kazanç.
İki taraf bu yüzden ayrıldı. Bu testler ayrımın kazara kapanmasını
engelliyor: birinin bayrağı diğerine bağlaması sessiz bir güvenlik
gerilemesi olurdu.
"""

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from pipeline import config  # noqa: E402


def test_safety_is_pinned_to_tfidf():
    assert config.PREFER_ST_SAFETY is False


def test_retrieval_follows_the_flag():
    assert config.PREFER_ST_RETRIEVAL == config.PREFER_SENTENCE_TRANSFORMERS


def test_the_two_settings_are_independent():
    """Güvenlik ayarı retriever ayarına bağlanmamalı.

    `PREFER_ST_SAFETY = PREFER_ST_RETRIEVAL` yazmak testi geçirir gibi
    görünürdü ama bayrak açıldığında güvenlik de ST'ye geçerdi.
    """
    import inspect

    kaynak = inspect.getsource(config)
    satir = [
        s.strip() for s in kaynak.splitlines()
        if s.strip().startswith("PREFER_ST_SAFETY")
    ]
    assert satir == ["PREFER_ST_SAFETY = False"], satir


def test_safety_classifier_asks_for_the_safety_backend():
    import inspect

    from pipeline import safety_classifier

    kaynak = inspect.getsource(safety_classifier)
    assert "PREFER_ST_SAFETY" in kaynak
    assert "get_backend()" not in kaynak, "bayrağı atlayan çağrı kalmış"


def test_retriever_asks_for_the_retrieval_backend():
    import inspect

    from pipeline import retriever

    kaynak = inspect.getsource(retriever)
    assert "PREFER_ST_RETRIEVAL" in kaynak
    assert "get_backend()" not in kaynak, "bayrağı atlayan çağrı kalmış"


def test_backend_factory_honours_an_explicit_false(monkeypatch):
    """Bayrak açıkken bile açıkça False istenirse TF-IDF gelmeli."""
    from pipeline import embedding_backend as eb

    monkeypatch.setattr(config, "PREFER_SENTENCE_TRANSFORMERS", True)
    assert eb.get_backend(prefer_st=False).name == "tfidf-char-ngram"
