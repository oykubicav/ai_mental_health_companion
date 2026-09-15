"""Kartı modelin seçmesi — gömme sıralamasına alternatif.

Neden var:

Retriever kartları TF-IDF karakter n-gramı benzerliğiyle sıralıyor. Ölçümde
bu sıralamanın ayırt etme gücünün çok düşük olduğu görüldü — 89 mesajda en
iyi kartın skoru medyanda 0.093, en iyi/en kötü oranı 1.58x. Somut örnek:
"Kedim öldü ama kimseye söyleyemiyorum" ile "kedim ödül aldı, kimseye
söylemedim" aynı kartı getiriyor, çünkü ortak parçalar 'ama', 'kimseye',
'söyleyemiyorum' gibi dilbilgisi parçaları; 'öldü' hiçbir role sahip değil.

Yani sistemin en sonuç belirleyici kararı (180 karttan hangi 2'si cevaba
temel olacak) en zayıf mekanizmaya bırakılmıştı. Model kaba etiketi seçiyor,
matematik içeriği seçiyordu.

Bu modül kararı modele veriyor: bütün kart başlıkları veriliyor, model
mesaja uyan kimlikleri döndürüyor.

Tasarım kararları:

- AYRI çağrı, intent çağrısına eklenmedi. Eklemek daha ucuz olurdu ama
  intent prompt'u yeni ölçüldü (%92 modül, %93 durum) ve büyütmek o ölçümü
  geçersiz kılardı. Ayrı tutmak ikisini bağımsız ölçülebilir bırakıyor;
  değeri kanıtlanırsa sonra tek çağrıya katlanabilir.
- Varsayılan KAPALI (CBT_LLM_RETRIEVAL=1 ile açılır). Kanıtlanmamış bir yol
  üretimde varsayılan olamaz.
- Model geçersiz kimlik uydurursa o kimlik atılır; hiçbiri geçerli değilse
  None döner ve çağıran gömme sıralamasına düşer. Sessiz bozulma yok.
- allow_cbt=False iken hiç çağrılmıyor: kriz yolunda CBT kartı zaten
  yüzeye çıkmamalı.
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import List, Optional

from . import cards as _cards
from . import config
from . import llm_adapter

MAX_SECIM = 3


def enabled() -> bool:
    """Varsayılan kapalı — ölçülene kadar üretimde açılmaz."""
    return os.environ.get("CBT_LLM_RETRIEVAL", "0") == "1"


_SYSTEM_TR = """Sen bir Türkçe CBT self-help sisteminin kart seçicisisin.

Elinde klinik psikolog onayından geçmiş bilgi kartları var. Görevin:
kullanıcının mesajına cevap yazarken TEMEL ALINACAK kartları seçmek.

KURALLAR:
1. En fazla {maks} kart kimliği seç. Az seçmek çok seçmekten iyidir.
2. Gerçekten uyan kart yoksa boş liste döndür. Uydurma kart kimliği YAZMA.
3. Kullanıcının ne anlattığına bak, hangi kelimeleri kullandığına değil.
   "Kedim öldü" bir kayıp mesajıdır; içindeki kelimelere benzeyen kart değil,
   kayıpla ilgili kart gerekir.
4. Konuşma geçmişi verilmişse konuyu oradan da al — tek mesaj yanıltabilir.
5. Sıralama önemli: en uygun kart başa.

FORMAT — sadece geçerli JSON:
{{"card_ids": ["...", "..."], "rationale": "en fazla 12 kelime"}}

KARTLAR:
{katalog}"""


@lru_cache(maxsize=1)
def _katalog() -> tuple:
    """(katalog_metni, gecerli_kimlikler) — kartlar değişmedikçe bir kez kurulur."""
    kartlar = _cards.all_cbt_cards()
    satirlar = [f"{c['id']} [{c['topic']}] {c['title_tr']}" for c in kartlar]
    return "\n".join(satirlar), frozenset(c["id"] for c in kartlar)


def reset_cache() -> None:
    _katalog.cache_clear()


def _gecmis_blogu(history: Optional[List[dict]]) -> str:
    if not history:
        return ""
    satir = []
    for t in history[-2:]:
        k = (t.get("user_message") or "").strip()
        if k:
            satir.append(f"- {k}")
    if not satir:
        return ""
    return "ÖNCEKİ MESAJLAR (bağlam):\n" + "\n".join(satir) + "\n\n"


def select(
    user_message: str,
    *,
    history: Optional[List[dict]] = None,
    allow_cbt: bool = True,
    max_cards: int = MAX_SECIM,
) -> Optional[List[str]]:
    """Modele kart seçtirir. Başarısızlıkta None döner — çağıran gömmeye düşer.

    None ile [] farklı: None "seçemedim, sen bak" demek; [] ise "baktım,
    uyan kart yok" demek. İkincisi çağıran için bilgi — materyalin zayıf
    olduğunu söylüyor.
    """
    if not allow_cbt or not user_message or not user_message.strip():
        return None

    katalog, gecerli = _katalog()
    try:
        resp = llm_adapter.llm_complete(
            system=_SYSTEM_TR.format(maks=max_cards, katalog=katalog),
            user=f"{_gecmis_blogu(history)}Mesaj: \"{user_message}\"\n\nSeçim JSON'u:",
            model=config.LLM_MODEL_INTENT,
            max_tokens=200,
            temperature=0.0,
            redact=True,
        )
    except Exception:
        return None

    m = re.search(r"\{.*\}", resp.text, flags=re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except Exception:
        return None

    ham = data.get("card_ids", [])
    if not isinstance(ham, list):
        return None

    # Uydurulan kimlikler atılıyor. Model kart kimliği halüsine ettiğinde
    # sessizce yanlış içerik gelmesindense hiç gelmemesi yeğ.
    secim, gorulen = [], set()
    for cid in ham:
        cid = str(cid).strip()
        if cid in gecerli and cid not in gorulen:
            secim.append(cid)
            gorulen.add(cid)
        if len(secim) >= max_cards:
            break
    return secim
