"""Konuşma durumu sınıflandırmasını ölçer.

Süreç kartları `conversation_state` üzerinden getiriliyor. O etiket yanlışsa
kartlar da yanlış anda gelir: kullanıcı güvence ararken düşünce kaydı
önerilir, kapanışa gelmişken yeni soru sorulur. Kart yazmadan önce bu
katmanın ne kadar isabetli olduğunu bilmek gerekiyor.

Kullanım:
    python scripts/eval_process_state.py                 # tam set
    python scripts/eval_process_state.py --limit 20      # hızlı bakış
    python scripts/eval_process_state.py --only vague    # tek durum
    python scripts/eval_process_state.py --json out.json # makine okunur

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

SET_PATH = BASE / "evals" / "process_state_test_set.jsonl"


# Her karışma aynı maliyette değil. Ham isabet oranı bunu gizliyor:
# own_evidence yerine formulating gelmesi neredeyse zararsız (iki kart da
# fark edileni sabitlemeye çalışıyor), ama reassurance_seeking kaçırılırsa
# güvence verilir ve kaygı döngüsü beslenir.
#
# Düşük maliyetli çiftler — komşu kartlar benzer hamle yaptırıyor:
DUSUK_MALIYET = {
    frozenset({"own_evidence", "formulating"}),
    frozenset({"own_evidence", "reporting_progress"}),
    frozenset({"formulating", "reporting_progress"}),
    frozenset({"winding_down", "withdrawn"}),      # ikisi de "soru sorma"
    frozenset({"vague", "withdrawn"}),             # ikisi de "üsteleme"
}

# Yüksek maliyetli kaçırmalar — davranış açıkça yanlış olur:
YUKSEK_MALIYET = {
    "reassurance_seeking",   # kaçırılırsa güvence verilir, döngü beslenir
    "technique_failed",      # kaçırılırsa başarısızlık kullanıcıya yüklenir
    "ruminating",            # kaçırılırsa keşif sorusu döngüyü besler
    "misunderstood",         # kaçırılırsa savunmaya geçilir
}


def _maliyet(beklenen: str, uretilen: str) -> str:
    """Bir karışmanın davranışsal maliyeti."""
    if uretilen == "neutral":
        # Hiç durum kartı gelmiyor — katman o turda sessizce kapalı.
        return "yuksek"
    if frozenset({beklenen, uretilen}) in DUSUK_MALIYET:
        return "dusuk"
    if beklenen in YUKSEK_MALIYET:
        return "yuksek"
    return "orta"


def _load_cases():
    with open(SET_PATH, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _classify(case) -> str:
    """Tek bir örneği sınıflandır ve conversation_state'i döndür."""
    from pipeline import intent_classifier, safety_classifier

    mesaj = case["user_message_tr"]
    # Güvenlik sınıflandırması intent'i etkiliyor (kriz yolunda kısa devre),
    # o yüzden gerçek akışın aynısını kuruyoruz.
    safety = safety_classifier.classify(mesaj, enable_layer3=False)
    intent = intent_classifier.classify(mesaj, safety, enable_llm=True)
    return getattr(intent, "conversation_state", "neutral")


def run(limit=None, only=None):
    cases = _load_cases()
    if only:
        cases = [c for c in cases if c["expected_state"] == only]
    if limit:
        cases = cases[:limit]

    sonuclar = []
    for i, c in enumerate(cases, 1):
        try:
            uretilen = _classify(c)
            hata = None
        except Exception as e:  # tek örnek patlarsa koşu devam etsin
            uretilen, hata = "HATA", f"{type(e).__name__}: {e}"

        dogru = uretilen == c["expected_state"]
        sonuclar.append({
            "test_id": c["test_id"],
            "beklenen": c["expected_state"],
            "uretilen": uretilen,
            "dogru": dogru,
            "hard_case": c.get("hard_case", False),
            "mesaj": c["user_message_tr"],
            "hata": hata,
        })
        isaret = "." if dogru else "X"
        print(isaret, end="", flush=True)
        if i % 40 == 0:
            print()
    print("\n")
    return sonuclar


def report(sonuclar):
    toplam = len(sonuclar)
    dogru = sum(1 for r in sonuclar if r["dogru"])
    kolay = [r for r in sonuclar if not r["hard_case"]]
    zor = [r for r in sonuclar if r["hard_case"]]

    print(f"Genel isabet : {dogru}/{toplam}  ({dogru/toplam:.0%})")
    if kolay:
        k = sum(1 for r in kolay if r["dogru"])
        print(f"  açık vakalar: {k}/{len(kolay)}  ({k/len(kolay):.0%})")
    if zor:
        z = sum(1 for r in zor if r["dogru"])
        print(f"  zor vakalar : {z}/{len(zor)}  ({z/len(zor):.0%})")

    # Durum bazında
    print("\nDurum bazında:")
    per = defaultdict(lambda: [0, 0])
    for r in sonuclar:
        per[r["beklenen"]][1] += 1
        if r["dogru"]:
            per[r["beklenen"]][0] += 1
    for durum in sorted(per, key=lambda d: per[d][0] / per[d][1]):
        d, t = per[durum]
        cubuk = "#" * int(10 * d / t) + "." * (10 - int(10 * d / t))
        print(f"  {durum:22} {cubuk} {d}/{t}")

    # En sık karışan çiftler — asıl ilgilendiğimiz bilgi
    karisan = Counter(
        (r["beklenen"], r["uretilen"]) for r in sonuclar if not r["dogru"]
    )
    if karisan:
        print("\nKarışan çiftler (beklenen → üretilen):")
        for (b, u), n in karisan.most_common(12):
            print(f"  {b:22} → {u:22} {n}")

    # neutral'a kaçış ayrı bir sorun: katman pratikte devre dışı kalır
    neutral_kacis = sum(
        1 for r in sonuclar if not r["dogru"] and r["uretilen"] == "neutral"
    )
    if neutral_kacis:
        print(
            f"\nneutral'a kaçan: {neutral_kacis}"
            f"  — bu örneklerde süreç kartı devreye girmiyor demektir."
        )

    # Maliyete göre kırılım — ham oran bunu gizliyor
    yanlislar_tum = [r for r in sonuclar if not r["dogru"]]
    if yanlislar_tum:
        kirilim = Counter(_maliyet(r["beklenen"], r["uretilen"]) for r in yanlislar_tum)
        print("\nHataların davranışsal maliyeti:")
        for seviye, etiket in [
            ("yuksek", "yüksek — davranış açıkça yanlış"),
            ("orta", "orta   — kart farklı ama yönü yakın"),
            ("dusuk", "düşük  — komşu kart, benzer hamle"),
        ]:
            if kirilim.get(seviye):
                print(f"  {etiket}: {kirilim[seviye]}")
        agir = [r for r in yanlislar_tum
                if _maliyet(r["beklenen"], r["uretilen"]) == "yuksek"]
        if agir:
            print("  Yüksek maliyetli olanlar:")
            for r in agir:
                print(f"    {r['test_id']}: {r['beklenen']} → {r['uretilen']}")

    yanlislar = [r for r in sonuclar if not r["dogru"]]
    if yanlislar:
        print("\nYanlışlar:")
        for r in yanlislar:
            zor = " [zor]" if r["hard_case"] else ""
            print(f"  {r['test_id']}{zor}: {r['beklenen']} → {r['uretilen']}")
            print(f"      \"{r['mesaj'][:70]}\"")

    return dogru / toplam if toplam else 0.0


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

    # Eşik koymuyoruz: bu bir ölçüm aracı, yayın kapısı değil. Sınıflandırma
    # düzeldikçe eşik konabilir.
    print(f"\nisabet={isabet:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
