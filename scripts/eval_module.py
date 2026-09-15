"""Modül ve subintent sınıflandırmasını ölçer.

`conversation_state` konuşmanın nasıl yürütüleceğini belirliyordu; bu iki
eksen ise cevabın neye dayanacağını belirliyor. primary_module retriever'a
filtre veriyor, yani yanlış modül yanlış bilgi alanından kart getirtiyor:
iş yükü anlatan birine yaygın kaygı kartları, ağrı anlatan birine panik
kartları. Bu eksen bugüne kadar hiç ölçülmemişti.

Kullanım:
    python scripts/eval_module.py                      # tam set
    python scripts/eval_module.py --limit 20           # hızlı bakış
    python scripts/eval_module.py --only panic         # tek modül
    python scripts/eval_module.py --json out.json      # makine okunur

Not: gerçek Haiku çağrısı yapıyor, ANTHROPIC_API_KEY gerekiyor.
CBT_LLM_PROVIDER=mock ile çalıştırmak anlamsız — mock sabit değer döner.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

SET_PATH = BASE / "evals" / "module_test_set.jsonl"


# Klinik olarak komşu modüller. Karışmaları büyük ölçüde zararsız, çünkü
# kart havuzları da örtüşüyor ve ikisi de aynı yöne çalışıyor.
KOMSU = {
    frozenset({"panic", "health_anxiety"}),
    frozenset({"gad", "health_anxiety"}),
    frozenset({"gad", "work_stress"}),
    frozenset({"gad", "insomnia"}),
    frozenset({"depression", "low_self_esteem"}),
    frozenset({"depression", "grief_loss"}),
    frozenset({"depression", "life_transitions"}),
    frozenset({"social_anxiety", "low_self_esteem"}),
    frozenset({"social_anxiety", "exam_anxiety"}),
    frozenset({"body_image", "low_self_esteem"}),
    frozenset({"procrastination", "exam_anxiety"}),
    frozenset({"anger", "work_stress"}),
    frozenset({"trauma_awareness", "panic"}),
}


def _maliyet(beklenen: str, uretilen: str) -> str:
    """Bir modül karışmasının davranışsal maliyeti.

    Ham isabet oranı bunların hepsini eşit sayıyor; oysa aralarında
    kategorik fark var.
    """
    # Kriz mesajını sıradan bir CBT konusu sanmak en pahalı hata: cevap yanlış
    # türden olur. safety için güvenlik sınıflandırıcısı ayrı bir katman olarak
    # duruyor, ama modül de yanlışsa iki savunma birden zayıflar.
    if beklenen == "safety" and uretilen != "safety":
        return "yuksek"

    # Ters yön: sıradan bir mesajı kriz sanmak. Kullanıcı gereksiz yere 112
    # görür — rahatsız edici ve güveni zedeler, ama tehlikeli değil.
    #
    # Bu kontrol sınır kontrolünden ÖNCE geliyor ve sırası önemli. İlk sürümde
    # sonra geliyordu ve "ilaç dozumu kendim artırsam olur mu" → safety hatası
    # yüksek maliyetli sayılıyordu. Oysa iki yol da aynı şeyi yapıyor: cevabı
    # reddedip hekime yönlendiriyor. safety yalnızca daha temkinli olanı.
    # Sınırı kaçırmanın pahalı olduğu yer, sorunun CBT içeriğiyle
    # cevaplanmasıydı — bunu safety yolu zaten engelliyor.
    if uretilen == "safety" and beklenen != "safety":
        return "orta"

    if beklenen == "boundary" and uretilen != "boundary":
        return "yuksek"

    # unknown'a kaçış conversation_state'teki neutral'a kaçıştan farklı:
    # katman kapanmıyor, module_filter None dönüyor ve retrieval filtresiz
    # çalışıyor. Sonuç daha az isabetli ama hâlâ ilgili.
    if uretilen == "unknown" and beklenen != "unknown":
        return "orta"

    if frozenset({beklenen, uretilen}) in KOMSU:
        return "dusuk"
    return "orta"


def _load_cases():
    with open(SET_PATH, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _classify(case):
    """(modül, subintent, güven) döndürür."""
    from pipeline import intent_classifier, safety_classifier

    mesaj = case["user_message_tr"]
    # Gerçek akışın aynısı: güvenlik önce çalışıyor ve kriz yolunda intent
    # kısa devre yapıyor. Sırayı bozarsak ölçtüğümüz şey üretim değil.
    safety = safety_classifier.classify(mesaj, enable_layer3=False)
    gecmis = [
        {"user_message": t.get("user", ""), "response": t.get("assistant", "")}
        for t in case.get("history_tr", []) or []
    ]
    intent = intent_classifier.classify(
        mesaj, safety, history=gecmis, enable_llm=True
    )
    return intent.primary_module, intent.subintent, intent.confidence


def run(limit=None, only=None):
    cases = _load_cases()
    if only:
        cases = [c for c in cases if c["expected_module"] == only]
    if limit:
        cases = cases[:limit]

    sonuclar = []
    for i, c in enumerate(cases, 1):
        try:
            modul, sub, guven = _classify(c)
            hata = None
        except Exception as e:  # tek örnek patlarsa koşu devam etsin
            modul, sub, guven, hata = "HATA", "HATA", None, f"{type(e).__name__}: {e}"

        dogru = modul == c["expected_module"]
        sonuclar.append({
            "test_id": c["test_id"],
            "beklenen": c["expected_module"],
            "uretilen": modul,
            "dogru": dogru,
            "beklenen_subintent": c["expected_subintent"],
            "uretilen_subintent": sub,
            "subintent_dogru": sub == c["expected_subintent"],
            "guven": guven,
            "hard_case": c.get("hard_case", False),
            "mesaj": c["user_message_tr"],
            "hata": hata,
        })
        print("." if dogru else "X", end="", flush=True)
        if i % 40 == 0:
            print()
    print("\n")
    return sonuclar


def report(sonuclar):
    toplam = len(sonuclar)
    if not toplam:
        return 0.0
    dogru = sum(1 for r in sonuclar if r["dogru"])
    kolay = [r for r in sonuclar if not r["hard_case"]]
    zor = [r for r in sonuclar if r["hard_case"]]

    print(f"Modül isabeti : {dogru}/{toplam}  ({dogru/toplam:.0%})")
    if kolay:
        k = sum(1 for r in kolay if r["dogru"])
        print(f"  açık vakalar: {k}/{len(kolay)}  ({k/len(kolay):.0%})")
    if zor:
        z = sum(1 for r in zor if r["dogru"])
        print(f"  zor vakalar : {z}/{len(zor)}  ({z/len(zor):.0%})")

    sub_dogru = sum(1 for r in sonuclar if r["subintent_dogru"])
    print(f"Subintent     : {sub_dogru}/{toplam}  ({sub_dogru/toplam:.0%})")

    print("\nModül bazında:")
    per = defaultdict(lambda: [0, 0])
    for r in sonuclar:
        per[r["beklenen"]][1] += 1
        if r["dogru"]:
            per[r["beklenen"]][0] += 1
    for modul in sorted(per, key=lambda m: per[m][0] / per[m][1]):
        d, t = per[modul]
        cubuk = "#" * int(10 * d / t) + "." * (10 - int(10 * d / t))
        print(f"  {modul:22} {cubuk} {d}/{t}")

    karisan = Counter(
        (r["beklenen"], r["uretilen"]) for r in sonuclar if not r["dogru"]
    )
    if karisan:
        print("\nKarışan çiftler (beklenen → üretilen):")
        for (b, u), n in karisan.most_common(12):
            print(f"  {b:22} → {u:22} {n}")

    unknown_kacis = sum(
        1 for r in sonuclar
        if not r["dogru"] and r["uretilen"] == "unknown"
    )
    if unknown_kacis:
        print(
            f"\nunknown'a kaçan: {unknown_kacis}"
            f"  — retrieval filtresiz çalışır, kapanmaz ama isabeti düşer."
        )

    yanlislar = [r for r in sonuclar if not r["dogru"]]
    if yanlislar:
        kirilim = Counter(_maliyet(r["beklenen"], r["uretilen"]) for r in yanlislar)
        print("\nHataların davranışsal maliyeti:")
        for seviye, etiket in [
            ("yuksek", "yüksek — kriz ya da sınır mesajı kaçtı"),
            ("orta", "orta   — yanlış alan ya da filtresiz retrieval"),
            ("dusuk", "düşük  — klinik komşu, kart havuzları örtüşüyor"),
        ]:
            if kirilim.get(seviye):
                print(f"  {etiket}: {kirilim[seviye]}")
        agir = [r for r in yanlislar if _maliyet(r["beklenen"], r["uretilen"]) == "yuksek"]
        if agir:
            print("  Yüksek maliyetli olanlar:")
            for r in agir:
                print(f"    {r['test_id']}: {r['beklenen']} → {r['uretilen']}")
                print(f"        \"{r['mesaj'][:70]}\"")

    if yanlislar:
        print("\nYanlışlar:")
        for r in yanlislar:
            z = " [zor]" if r["hard_case"] else ""
            print(f"  {r['test_id']}{z}: {r['beklenen']} → {r['uretilen']}")
            print(f"      \"{r['mesaj'][:70]}\"")

    sub_yanlis = [r for r in sonuclar if not r["subintent_dogru"]]
    if sub_yanlis:
        print("\nSubintent yanlışları:")
        for r in sub_yanlis[:15]:
            print(
                f"  {r['test_id']}: {r['beklenen_subintent']} → "
                f"{r['uretilen_subintent']}"
            )

    return dogru / toplam


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", type=str, default=None)
    ap.add_argument("--json", type=str, default=None, help="sonuçları dosyaya yaz")
    args = ap.parse_args()

    if os.environ.get("CBT_LLM_PROVIDER") == "mock":
        print("CBT_LLM_PROVIDER=mock — sınıflandırıcı gerçek karar vermez, ölçüm anlamsız.")
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY yok. Bu koşu gerçek Haiku çağrısı yapıyor.")
        return 2

    sonuclar = run(limit=args.limit, only=args.only)
    isabet = report(sonuclar)

    if args.json:
        Path(args.json).write_text(
            json.dumps(sonuclar, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n→ {args.json}")

    # Eşik yok: bu bir ölçüm aracı, yayın kapısı değil.
    print(f"\nisabet={isabet:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
