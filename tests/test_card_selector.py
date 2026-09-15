"""Kartı modelin seçmesi — deneysel yol.

Gömme sıralamasının ayırt etme gücü ölçülüp düşük bulunduktan sonra eklendi
(medyan tepe skor 0.093, tepe/son oranı 1.58x). Bu testler LLM çağırmıyor;
test edilen şey çevresi: bayrak, doğrulama, geri düşme.

En kritik davranış halüsinasyon savunması. Model olmayan bir kart kimliği
uydurursa o kimlik atılmalı — sessizce yanlış içerik göstermektense hiç
göstermemek yeğ.
"""

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from pipeline import card_selector as cs  # noqa: E402
from pipeline import retriever  # noqa: E402


def setup_function():
    cs.reset_cache()


# ---------------------------------------------------------------- bayrak

def test_enabled_by_default(monkeypatch):
    """2026-09-15'te ölçüm sonrası açıldı.

    Net vakalarda iki yöntem eşit (38/41 vs 39/41); fark n-gram'ın battığı
    12 tuzak vakasında (5/12 vs 10/12). Haiku'nun kendine özgü kaçırması yok.
    """
    monkeypatch.delenv("CBT_LLM_RETRIEVAL", raising=False)
    assert cs.enabled() is True


def test_can_be_switched_off(monkeypatch):
    """Geri dönüş yolu deploy gerektirmemeli — tek değişken yetmeli."""
    monkeypatch.setenv("CBT_LLM_RETRIEVAL", "0")
    assert cs.enabled() is False


# ---------------------------------------------------------------- katalog

def test_catalogue_lists_every_card():
    from pipeline import cards as _cards

    katalog, gecerli = cs._katalog()
    kartlar = _cards.all_cbt_cards()
    assert len(gecerli) == len(kartlar)
    for c in kartlar[:5]:
        assert c["id"] in katalog
        assert c["title_tr"] in katalog


def test_catalogue_stays_small_enough_to_send():
    """Bütün başlıkları her çağrıda göndermek maliyet kararı — sınır konsun."""
    katalog, _ = cs._katalog()
    assert len(katalog) < 20000, f"katalog {len(katalog)} karakter"


# ---------------------------------------------------------------- doğrulama

def test_crisis_route_never_selects_cbt_cards():
    """allow_cbt=False iken CBT kartı yüzeye çıkmamalı — çağrı bile yapılmaz."""
    assert cs.select("yaşamak istemiyorum", allow_cbt=False) is None


def test_empty_message_returns_none():
    assert cs.select("") is None
    assert cs.select("   ") is None


def test_hallucinated_ids_are_dropped(monkeypatch):
    """Model uydurma kimlik döndürürse o kimlik atılmalı."""
    from pipeline import cards as _cards

    gercek = _cards.all_cbt_cards()[0]["id"]

    class _Resp:
        text = (
            '{"card_ids": ["' + gercek + '", "boyle_bir_kart_yok_001"], '
            '"rationale": "test"}'
        )

    monkeypatch.setattr(cs.llm_adapter, "llm_complete", lambda **k: _Resp())
    assert cs.select("panik atak geçiriyorum") == [gercek]


def test_all_invalid_returns_empty_not_none(monkeypatch):
    """Boş liste ile None farklı: biri 'uyan kart yok', diğeri 'seçemedim'.

    Çağıran bu farkı kullanıyor — None gömme sıralamasına düşmek demek.
    """
    class _Resp:
        text = '{"card_ids": ["yok_001", "yok_002"], "rationale": "x"}'

    monkeypatch.setattr(cs.llm_adapter, "llm_complete", lambda **k: _Resp())
    assert cs.select("merhaba") == []


def test_llm_error_falls_back_to_none(monkeypatch):
    def _patla(**k):
        raise RuntimeError("ağ hatası")

    monkeypatch.setattr(cs.llm_adapter, "llm_complete", _patla)
    assert cs.select("panik atak") is None


def test_broken_json_falls_back_to_none(monkeypatch):
    class _Resp:
        text = "burada json yok"

    monkeypatch.setattr(cs.llm_adapter, "llm_complete", lambda **k: _Resp())
    assert cs.select("panik atak") is None


def test_selection_is_capped(monkeypatch):
    from pipeline import cards as _cards

    hepsi = [c["id"] for c in _cards.all_cbt_cards()[:10]]

    class _Resp:
        import json as _j
        text = _j.dumps({"card_ids": hepsi, "rationale": "x"})

    monkeypatch.setattr(cs.llm_adapter, "llm_complete", lambda **k: _Resp())
    assert len(cs.select("bir şey", max_cards=2)) == 2


def test_duplicates_are_removed(monkeypatch):
    from pipeline import cards as _cards

    cid = _cards.all_cbt_cards()[0]["id"]

    class _Resp:
        text = '{"card_ids": ["%s", "%s"], "rationale": "x"}' % (cid, cid)

    monkeypatch.setattr(cs.llm_adapter, "llm_complete", lambda **k: _Resp())
    assert cs.select("bir şey") == [cid]


# ---------------------------------------------------------------- retriever

def test_preferred_ids_come_first():
    from pipeline import cards as _cards

    hedef = _cards.all_cbt_cards()[-1]["id"]
    r = retriever.retrieve("uyuyamıyorum", top_k=5, preferred_ids=[hedef])
    assert r[0].card_id == hedef
    assert r[0].source == "llm"


def test_preferred_ids_never_outrank_safety():
    """Güvenlik kartı hiçbir koşulda geçilmez."""
    from pipeline import cards as _cards

    sid = next(iter(_cards.safety_cards_by_id()))
    hedef = _cards.all_cbt_cards()[-1]["id"]
    r = retriever.retrieve(
        "yaşamak istemiyorum", top_k=5,
        safety_card_ids=[sid], preferred_ids=[hedef],
    )
    assert r[0].card_id == sid
    assert r[0].score >= r[1].score


def test_preferred_ids_ignored_on_hard_stop():
    from pipeline import cards as _cards

    hedef = _cards.all_cbt_cards()[-1]["id"]
    r = retriever.retrieve("x", allow_cbt=False, preferred_ids=[hedef])
    assert all(c.card_id != hedef for c in r)


def test_unknown_preferred_id_is_ignored():
    r = retriever.retrieve("uyuyamıyorum", top_k=5, preferred_ids=["yok_999"])
    assert all(c.card_id != "yok_999" for c in r)
    assert r, "geçersiz kimlik yüzünden sonuç boşalmamalı"


def test_no_preferred_ids_behaves_as_before():
    a = retriever.retrieve("uyuyamıyorum", top_k=5)
    b = retriever.retrieve("uyuyamıyorum", top_k=5, preferred_ids=None)
    assert [c.card_id for c in a] == [c.card_id for c in b]


# ---------------------------------------------------------------- ölçüm aracı

def test_comparison_runs_the_safety_classifier_first():
    """Karşılaştırma üretimdeki sırayı kurmalı: güvenlik önce.

    İlk sürüm retrieve()'i safety_card_ids vermeden çağırıyordu. 41 vakanın
    6'sı güvenlik kartı bekliyor ve o kartların dönmesi yapısal olarak
    imkânsızdı — hepsi "retrieval kaçırdı" diye raporlanıyordu. tfidf 78%
    görünüyordu, düzeltilince 92.7% çıktı. Ölçüm aracının kendi hatası,
    ölçtüğü şeyin hatası gibi okunuyordu.
    """
    import inspect
    import sys as _sys
    from pathlib import Path as _Path

    _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "scripts"))
    import eval_retrieval_compare as erc

    kaynak = inspect.getsource(erc)
    assert "_guvenlik" in kaynak
    for yol in ("_gomme_yolu", "_llm_yolu"):
        fn = inspect.getsource(getattr(erc, yol))
        assert "safety_card_ids" in fn, f"{yol} güvenlik kartlarını geçirmiyor"
        assert "allow_cbt" in fn, f"{yol} allow_cbt geçirmiyor"
