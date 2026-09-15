"""Konuşma düzeyinde ölçüm — tek mesajın göremediği kusurlar.

Şimdiye kadarki iki eval etiket ölçüyordu: doğru modül mü, doğru konuşma
durumu mu. İkisi de %90'ların üstündeyken gerçek bir konuşma kötü olabiliyor,
çünkü asıl kusurlar turlar ARASINDA oluşuyor:

  - aynı açıklamanın daha uzun yazılmış hâli (tekrar)
  - dördüncü turda kapanış teklifi (erken bırakma)
  - bir öneriyi ortaya atıp aynı paragrafta geri çekme
  - her turu soruyla bitirip konuşmayı sorguya çevirme
  - kullanıcının kelimesini klinik terime tercüme etme

Hiçbiri sınıflandırma hatası değil, dolayısıyla hiçbiri diğer iki eval'de
görünmüyor.

Yöntem: senaryodaki kullanıcı turları sabit. Cevap veren taraf gerçek
pipeline (orchestrator.respond), geçmiş biriktirilerek. Kullanıcı simülatörü
KULLANMIYORUZ — simülatör Neva'nın dediğine tepki verirdi ve koşudan koşuya
değişirdi; o zaman ölçtüğümüz şey sistem değil, simülatörün ruh hâli olurdu.
Sabit kullanıcı, farkın kaynağını sisteme sabitliyor.

Kontroller deterministik. LLM-yargıç yok: yargıç da bir model olurdu ve onun
hatasını ölçecek üçüncü bir kata ihtiyaç duyardık.

Kullanım:
    python scripts/eval_conversation.py
    python scripts/eval_conversation.py --only konv_yorgun_gun
    python scripts/eval_conversation.py --json out.json

Not: gerçek LLM çağrısı yapıyor ve senaryo başına birkaç tur sürüyor.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

SET_PATH = BASE / "evals" / "conversation_scenarios.jsonl"

# Kapanış işaretleri — konuşmayı bitirmeye davet eden kalıplar.
_KAPANIS = [
    r"burada dur\w*", r"bugünlük", r"böyle bırak\w*", r"yeter\w* bu kadar",
    r"başka bir zaman", r"yarın (?:devam|burada)", r"istersen (?:bırak|dural)\w*",
    r"burada olmak bile", r"sonra devam ed\w*",
]
# Öneri ortaya atma
_ONERI = [
    r"bir yolu var", r"deneyebilir\w*", r"önerebilir\w*", r"şunu yapabilir\w*",
    r"bir şey öner\w*", r"işe yarayabil\w*",
]
# Aynı cevapta geri çekme
_GERI_CEKME = [
    r"isteyip istemediğini bilmiyorum", r"zorunda değilsin", r"istersen",
    r"bugün (?:bunu )?konuşmak istemeyebilirsin", r"ama bilmiyorum",
    r"buna hazır (?:olup olmadığını|değilsen)",
]
# Güvence kalıpları — reassurance_seeking kartlarının açıkça yasakladığı
#
# Kalıbı ALINTILAYIP reddetmek ihlal değil, kartın tam olarak istediği şey:
# proc_reassurance_001 güvence vermemeyi ve bunu açıkça söylemeyi öneriyor.
# İlk sürüm "Sana 'tehlikeli değil' desem birkaç dakika rahatlarsın" cümlesini
# ihlal saydı — kartın doğru uygulandığı anı hata olarak raporladı.
_REDDETME = [
    r"desem", r"demem", r"diyemem", r"söyleyemem", r"demeyeceğim",
    r"diyebilirdim", r"deseydim", r"demek isterdim ama",
]
_GUVENCE = [
    r"bir şeyin yok", r"merak etme", r"ciddi bir şey değil", r"muhtemelen geçer",
    r"endişelenecek bir şey yok", r"tehlikeli değil",
]

_TEKRAR_ESIK = 0.40
_ANLAM_ESIK = 0.80        # ardışık iki cevabın gömme benzerliği
_NGRAM = 4
_SORU_ORANI_ESIK = 0.60   # turların bu kadarından fazlası soruysa sorgu
_ERKEN_TUR = 4          # bu turdan önce kapanış teklifi erken sayılıyor


def _ngramlar(metin: str, n: int = _NGRAM) -> set:
    k = re.findall(r"\w+", metin.lower(), flags=re.UNICODE)
    if len(k) < n:
        return set()
    return {tuple(k[i:i + n]) for i in range(len(k) - n + 1)}


def _var_mi(kaliplar, metin: str) -> str:
    for p in kaliplar:
        m = re.search(p, metin, flags=re.I)
        if m:
            return m.group(0)
    return ""


def _kontroller(cevaplar: list) -> dict:
    """Bir konuşmanın tamamı üzerinde deterministik kusur taraması."""
    bulgular = {}

    # 1. Sözcük düzeyinde tekrar — ardışık turlar arası n-gram örtüşmesi
    en_yuksek, nerede = 0.0, None
    for i in range(1, len(cevaplar)):
        yeni, onceki = _ngramlar(cevaplar[i]), _ngramlar(cevaplar[i - 1])
        if not yeni or not onceki:
            continue
        oran = len(yeni & onceki) / len(yeni)
        if oran > en_yuksek:
            en_yuksek, nerede = oran, i + 1
    bulgular["tekrar_yok"] = en_yuksek < _TEKRAR_ESIK
    bulgular["tekrar_detay"] = f"en yüksek n-gram örtüşmesi %{en_yuksek * 100:.0f} (tur {nerede})"

    # 1b. Anlam düzeyinde tekrar
    #
    # n-gram kontrolü kopyala-yapıştır tekrarı yakalıyor, başka kelimelerle
    # aynı şeyi söylemeyi yakalamıyor. Gerçek konuşmada tam bu oldu: dördüncü
    # tur üçüncü turun fikrini yeniden anlattı ve sözcük örtüşmesi %0 çıktı.
    # Gömme benzerliği paraphrase'i görüyor.
    #
    # Yalnızca eval'de: çalışma anındaki kritikte her turda gömme hesaplamak
    # gecikme ekler, oradaki kontrol sözcük düzeyinde kalıyor.
    #
    # UYARI: bu kontrol backend'e bağlı. sentence-transformers yoksa TF-IDF
    # karakter n-gramına düşüyor ve o da esasen sözcüksel — yani fallback
    # hâlinde paraphrase yakalanmıyor ve kontrol sessizce geçiyor. Hangi
    # backend'in kullanıldığı raporda yazıyor; "geçti" değeri ancak
    # sentence-transformers ile anlamlı.
    # -1 ile başlıyor: iki cevap tamamen farklıysa benzerlik 0 çıkar ve
    # 0.0'dan büyük olmadığı için ölçüm hiç yapılmamış gibi görünürdü.
    en_benzer, nerede_b = -1.0, None
    try:
        from pipeline import embedding_backend as eb

        uzunlar = [c for c in cevaplar if len(c.split()) >= 15]
        if len(uzunlar) >= 2:
            backend = eb.get_backend()
            bulgular["anlam_tekrari_backend"] = backend.name
            backend.fit(uzunlar)
            v = backend.encode(uzunlar)
            for i in range(1, len(uzunlar)):
                s = float(eb.cosine_similarity(v[i:i + 1], v[i - 1:i])[0][0])
                if s > en_benzer:
                    en_benzer, nerede_b = s, i + 1
    except Exception as e:  # gömme yoksa kontrol atlanır, koşu düşmez
        bulgular["anlam_tekrari_detay"] = f"hesaplanamadı ({type(e).__name__})"

    if nerede_b is not None:
        bulgular["anlam_tekrari_yok"] = en_benzer < _ANLAM_ESIK
        arka = bulgular.get("anlam_tekrari_backend", "?")
        guvenilir = "" if arka == "sentence-transformers" else "  [TF-IDF fallback — paraphrase görmez]"
        bulgular["anlam_tekrari_detay"] = (
            f"en yüksek benzerlik {en_benzer:.2f} (tur {nerede_b}){guvenilir}"
        )
    else:
        bulgular.setdefault("anlam_tekrari_yok", True)
        bulgular.setdefault("anlam_tekrari_detay", "ölçülecek uzun tur yok")

    # 2. Erken kapanış
    erken = None
    for i, c in enumerate(cevaplar[:_ERKEN_TUR], 1):
        isaret = _var_mi(_KAPANIS, c)
        if isaret:
            erken = f"tur {i}: '{isaret}'"
            break
    bulgular["erken_kapanis_yok"] = erken is None
    bulgular["erken_kapanis_detay"] = erken or "yok"

    # 3. Öner-geri çek — aynı cevapta öneri ve ardından geri çekme
    geri = None
    for i, c in enumerate(cevaplar, 1):
        o = _var_mi(_ONERI, c)
        if not o:
            continue
        kalan = c[c.lower().find(o.lower()) + len(o):]
        g = _var_mi(_GERI_CEKME, kalan)
        if g:
            geri = f"tur {i}: '{o}' → '{g}'"
            break
    bulgular["oner_geri_cekme_yok"] = geri is None
    bulgular["oner_geri_cekme_detay"] = geri or "yok"

    # 4. Sorgu hâline gelme
    #
    # İlk sürüm yalnızca 5/5'i yakalıyordu. Kartsız koşuda 4/5 çıktı ve
    # "geçti" denildi — oysa tek kelimelik cevaplar veren birine beş turun
    # dördünde soru sormak tam olarak kartların engellemeye çalıştığı şey.
    # Eşik orana çevrildi.
    soruyla = sum(1 for c in cevaplar if c.rstrip().endswith("?"))
    oran_s = soruyla / len(cevaplar) if cevaplar else 0.0
    bulgular["her_tur_soru_yok"] = oran_s <= _SORU_ORANI_ESIK
    bulgular["her_tur_soru_detay"] = (
        f"{soruyla}/{len(cevaplar)} tur soruyla bitmiş (%{oran_s * 100:.0f})"
    )

    # 5. Güvence verme
    guvence = None
    for i, c in enumerate(cevaplar, 1):
        for p in _GUVENCE:
            m = re.search(p, c, flags=re.I)
            if not m:
                continue
            # Tırnak içindeyse ya da hemen ardından reddetme geliyorsa,
            # kalıp kullanılmıyor; kullanılmayacağı söyleniyor.
            oncesi = c[max(0, m.start() - 3):m.start()]
            sonrasi = c[m.end():m.end() + 40]
            tirnakli = any(t in oncesi for t in ('"', "'", "“", "‘"))
            reddedilmis = bool(_var_mi(_REDDETME, sonrasi))
            if tirnakli or reddedilmis:
                continue
            guvence = f"tur {i}: '{m.group(0)}'"
            break
        if guvence:
            break
    bulgular["guvence_verme_yok"] = guvence is None
    bulgular["guvence_verme_detay"] = guvence or "yok"

    return bulgular


def _senaryolar():
    with open(SET_PATH, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _konusmayi_yurut(senaryo) -> list:
    """Senaryodaki kullanıcı turlarını sırayla geçirip cevapları toplar."""
    from pipeline import orchestrator

    gecmis, cevaplar = [], []
    for i, mesaj in enumerate(senaryo["turlar"]):
        tur = orchestrator.respond(mesaj, history=gecmis, turn_count=i)
        cevaplar.append(tur.response_text)
        gecmis.append({"user_message": mesaj, "response": tur.response_text})
    return cevaplar


def run(only=None):
    senaryolar = _senaryolar()
    if only:
        senaryolar = [s for s in senaryolar if s["id"] == only]

    sonuclar = []
    for s in senaryolar:
        print(f"  {s['id']} ", end="", flush=True)
        try:
            cevaplar = _konusmayi_yurut(s)
            hata = None
        except Exception as e:
            cevaplar, hata = [], f"{type(e).__name__}: {e}"

        bulgular = _kontroller(cevaplar) if cevaplar else {}
        gecti = {
            k: bulgular.get(k, False)
            for k in s["beklenen"] if s["beklenen"][k]
        }
        print("." if all(gecti.values()) and not hata else "X")
        sonuclar.append({
            "id": s["id"],
            "aciklama": s["aciklama"],
            "cevaplar": cevaplar,
            "bulgular": bulgular,
            "beklenen": s["beklenen"],
            "gecti": gecti,
            "hata": hata,
        })
    return sonuclar


def report(sonuclar) -> float:
    toplam = kontrol = gecen = 0
    print()
    for r in sonuclar:
        toplam += 1
        if r["hata"]:
            print(f"\n{r['id']}: HATA — {r['hata']}")
            continue
        basarisiz = [k for k, v in r["gecti"].items() if not v]
        kontrol += len(r["gecti"])
        gecen += len(r["gecti"]) - len(basarisiz)
        durum = "geçti" if not basarisiz else "KALDI"
        print(f"\n{r['id']}: {durum}")
        print(f"  {r['aciklama']}")
        for k in r["gecti"]:
            isaret = "✓" if r["gecti"][k] else "✗"
            detay = r["bulgular"].get(k.replace("_yok", "_detay"), "")
            print(f"    {isaret} {k}  {detay}")
        if basarisiz:
            for i, c in enumerate(r["cevaplar"], 1):
                print(f"      [{i}] {c[:110]}")

    print(f"\nKontrol: {gecen}/{kontrol} geçti  ({toplam} senaryo)")
    return gecen / kontrol if kontrol else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=str, default=None)
    ap.add_argument("--json", type=str, default=None)
    args = ap.parse_args()

    if os.environ.get("CBT_LLM_PROVIDER") == "mock":
        print("CBT_LLM_PROVIDER=mock — mock sabit cevap döner, konuşma ölçülemez.")
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY yok. Bu koşu gerçek konuşma yürütüyor.")
        return 2

    sonuclar = run(only=args.only)
    oran = report(sonuclar)

    if args.json:
        Path(args.json).write_text(
            json.dumps(sonuclar, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n→ {args.json}")

    print(f"\noran={oran:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
