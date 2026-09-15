"""Kart seçim yollarını aynı sette karşılaştırır.

Üç yol var ve üçü de aynı soruya cevap veriyor: mesaja hangi kartlar
temel alınmalı?

    tfidf   karakter n-gramı benzerliği          (üretimdeki varsayılan)
    st      sentence-transformers benzerliği     (CBT_PREFER_ST=1)
    llm     Haiku'ya bütün başlıklar verilip seçtirmek

Ölçüt: evals/retrieval_test_set.jsonl içindeki expected_cards'tan en az
biri ilk 6'da geliyor mu (hit rate).

Neden gerekli: gömme sıralamasının ayırt etme gücü ölçüldü ve düşük çıktı
(medyan tepe skor 0.093, tepe/son oranı 1.58x). "Kedim öldü" ile "kedim ödül
aldı" aynı kartı getiriyordu. Kararı modele vermenin gerçekten daha iyi olup
olmadığı tahminle değil ölçümle belirlensin.

Kullanım:
    python scripts/eval_retrieval_compare.py                # tfidf + llm
    python scripts/eval_retrieval_compare.py --yollar tfidf st llm
    python scripts/eval_retrieval_compare.py --json out.json

llm yolu gerçek Haiku çağrısı yapıyor (vaka başına bir çağrı).
st yolu sentence-transformers kurulu olmasını gerektiriyor.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

SET_PATH = BASE / "evals" / "retrieval_test_set.jsonl"
TOP_K = 6


def _vakalar():
    with open(SET_PATH, encoding="utf-8") as f:
        ham = [json.loads(l) for l in f if l.strip()]
    # Beklenen kartı olmayan ve kriz yolundaki vakalar dışarıda: kriz
    # yolunda CBT kartı zaten bilerek gelmiyor, orada hit aramak yanlış.
    return [c for c in ham if c.get("expected_cards") and c.get("expected_allow_cbt", True)]


def _guvenlik(vaka):
    """Üretimdeki gibi: güvenlik sınıflandırıcısı önce çalışır.

    İlk sürüm bunu atlıyordu ve safety_card_ids vermeden retrieve()
    çağırıyordu. 41 vakanın 6'sı güvenlik kartı bekliyor; o kartların
    dönmesi yapısal olarak imkânsızdı ve hepsi "kaçtı" sayılıyordu.
    Yani ölçüm, retrieval'ın suçu olmayan bir şeyi retrieval'a yazıyordu.
    """
    from pipeline import safety_classifier

    s = safety_classifier.classify(vaka["user_message_tr"], enable_layer3=False)
    return (s.safety_card_ids or None), s.allow_cbt


def _gomme_yolu(vaka, prefer_st: bool):
    from pipeline import config, retriever

    sids, allow = _guvenlik(vaka)
    onceki = config.PREFER_ST_RETRIEVAL
    config.PREFER_ST_RETRIEVAL = prefer_st
    try:
        retriever._build_card_index.cache_clear()
        r = retriever.retrieve(
            vaka["user_message_tr"], top_k=TOP_K,
            safety_card_ids=sids, allow_cbt=allow,
        )
        return [c.card_id for c in r]
    finally:
        config.PREFER_ST_RETRIEVAL = onceki
        retriever._build_card_index.cache_clear()


def _llm_yolu(vaka):
    from pipeline import card_selector, retriever

    sids, allow = _guvenlik(vaka)
    secim = card_selector.select(vaka["user_message_tr"], allow_cbt=allow)
    if secim is None and allow:
        return None  # model cevap vermedi — ayrı raporlanıyor
    r = retriever.retrieve(
        vaka["user_message_tr"], top_k=TOP_K,
        safety_card_ids=sids, allow_cbt=allow, preferred_ids=secim or None,
    )
    return [c.card_id for c in r]


YOLLAR = {
    "tfidf": lambda v: _gomme_yolu(v, False),
    "st": lambda v: _gomme_yolu(v, True),
    "llm": _llm_yolu,
}


def kosu(yol_adi, vakalar):
    fn = YOLLAR[yol_adi]
    isabet = 0
    cevapsiz = 0
    kacan = []
    for v in vakalar:
        try:
            gelen = fn(v)
        except Exception as e:
            gelen, = (None,)
            print(f"  [{v['test_id']}] HATA {type(e).__name__}: {e}")
        if gelen is None:
            cevapsiz += 1
            kacan.append((v["test_id"], "cevap yok"))
            continue
        if set(gelen) & set(v["expected_cards"]):
            isabet += 1
        else:
            kacan.append((v["test_id"], v["user_message_tr"][:48]))
        print("." if gelen and set(gelen) & set(v["expected_cards"]) else "X",
              end="", flush=True)
    print()
    return {"yol": yol_adi, "isabet": isabet, "toplam": len(vakalar),
            "cevapsiz": cevapsiz, "kacan": kacan}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yollar", nargs="+", default=["tfidf", "llm"],
                    choices=list(YOLLAR))
    ap.add_argument("--json", type=str, default=None)
    args = ap.parse_args()

    if "llm" in args.yollar:
        if os.environ.get("CBT_LLM_PROVIDER") == "mock":
            print("CBT_LLM_PROVIDER=mock — llm yolu ölçülemez.")
            return 2
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("ANTHROPIC_API_KEY yok — llm yolu gerçek çağrı yapıyor.")
            return 2

    vakalar = _vakalar()
    print(f"{len(vakalar)} vaka, ilk {TOP_K} kart içinde beklenen kart aranıyor.\n")

    sonuclar = []
    for yol in args.yollar:
        print(f"{yol}:")
        sonuclar.append(kosu(yol, vakalar))

    print("\n" + "=" * 52)
    for s in sonuclar:
        oran = s["isabet"] / s["toplam"] if s["toplam"] else 0
        ek = f"  (cevapsız: {s['cevapsiz']})" if s["cevapsiz"] else ""
        print(f"  {s['yol']:8} {s['isabet']:>3}/{s['toplam']}  {oran:.1%}{ek}")

    # Hangi vakalarda yollar ayrışıyor — asıl bilgi burada
    if len(sonuclar) >= 2:
        kacan_setleri = {s["yol"]: {t for t, _ in s["kacan"]} for s in sonuclar}
        adlar = list(kacan_setleri)
        hepsi_kacirdi = set.intersection(*kacan_setleri.values())
        print(f"\n  Hepsinin kaçırdığı: {len(hepsi_kacirdi)}"
              f"  — bunlar seçim yolu sorunu değil, kart ya da etiket sorunu.")
        for a in adlar:
            ozel = kacan_setleri[a] - set.union(
                *[kacan_setleri[b] for b in adlar if b != a]
            )
            if ozel:
                print(f"  Yalnızca {a} kaçırdı: {sorted(ozel)}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(sonuclar, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n→ {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
