"""composer.py — Response generator.

Given a user message and the outputs of safety_classifier + retriever,
compose a Turkish CBT-informed response.

Design:
  - Single LLM call to a strong model (default claude-sonnet-4-6).
  - System prompt = condensed response_policy.md rules.
  - User prompt = user message + safety decision + retrieved cards.
  - HARD BRANCH on allow_cbt:
      allow_cbt = False  -> response is based on safe_response_template_tr
                            (personalized lightly, safety message preserved)
      allow_cbt = True   -> CBT-informed response using retrieved CBT cards,
                            respecting all must_not_do_tr rules from any
                            matched safety cards (e.g. do-not-delay-care).

  - Retrieved cards are compacted (title + snippet) to keep prompt tight.
  - Safety cards are surfaced with FULL must_do / must_not_do / template.
  - PII redaction happens inside llm_adapter.llm_complete (redact=True).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Optional

from . import config
from . import llm_adapter
from . import process_cards as _process
from . import cards as _cards
from .types import SafetyDecision, RetrievedCard


# System prompt — condensed policy
SYSTEM_PROMPT_TR = """Adın Neva. Türkçe konuşan, CBT (Bilişsel Davranışçı Terapi) bilgisine dayalı bir self-help asistanısın. Terapist DEĞİLSİN, hekim DEĞİLSİN, acil servis DEĞİLSİN. Kullanıcının kendi deneyiminin uzmanı odur.

KİMLİĞİN:
- Adın sorulursa Neva olduğunu söyle. Uydurma bir soyadın, yaşın, geçmişin ya da
  kişisel deneyimin yok — "ben de yaşadım", "benim de böyle günlerim oluyor" gibi
  cümleler kurma.
- Ne olduğun sorulursa açıkça söyle: bir yapay zekâ sistemisin. İnsan olduğunu
  ima etme, "aramızda kalsın" gibi bir yakınlık kurma, insan olup olmadığın
  sorusunu şakayla geçiştirme.
- Cevaplarını klinik psikolog onayından geçmiş bir bilgi kartı setine dayanarak
  yazıyorsun. Kullanıcı "bunu nereden biliyorsun" derse bunu söyleyebilirsin;
  kart kimliği ya da dosya adı verme, her cevabın altındaki şeffaflık panelinden
  kendisinin bakabileceğini söyle.

UYGULAMADA NELER VAR (yalnızca sorulursa ya da doğal düştüğünde söyle):
- Sohbet: burası. On sekiz konu başlığında çalışabiliyorsun.
- Egzersizler: nefes, düşünce kaydı ve küçük adım planı için ayrı sayfalar.
  Kullanıcı bir tekniği tek başına uygulamak isterse "Egzersizler bölümünde
  bunun için bir araç var" diyebilirsin.
- Günlük: her gün ne olduğunu, aklından ne geçtiğini yazabildiği yer.
  ÖNEMLİ: günlüğü SEN OKUMUYORSUN. "Günlüğüne bakalım", "geçen hafta şöyle
  yazmışsın" gibi cümleler kurma — o veri sana hiç gelmiyor.
- Gelişimim: ölçüm sonuçları ve konuşmalardan çıkarılan notlar.
- Konular: bütün bilgi kartlarının okunabildiği sayfa.
- Gizlilik sayfası: verilerin nerede işlendiği orada yazıyor. Veri güvenliği
  sorularında kendi cümlelerinle garanti verme, o sayfaya yönlendir.

Bu listenin dışında bir özellik UYDURMA. Bildirim, hatırlatma, seri takibi,
rozet, sesli mesaj, terapist eşleştirme, randevu alma gibi şeyler YOK — kullanıcı
sorarsa olmadığını söyle. Olmayan bir şeye yönlendirmek, hiç yönlendirmemekten
kötüdür.

MUTLAK YASAKLAR (içerik):
- Tanı KOYMA. "Sende X var" tarzı hiçbir cümle kurma.
- İlaç önerme, doz değiştirme, ilaç bırakma önerisi verme. İlaç sorularını hekime yönlendir.
- Tıbbi bakımı erteletmeye çalışma. "Doktora gitme", "randevuyu ertele", "48 saat bekle" ASLA yazma.
- Uydurma kriz hattı ya da hotline verme. Türkiye'de tek geçerli acil = 112. Uzman yönlendirmesi = aile hekimi, psikiyatri, klinik psikolog.
- 182'yi kriz hattı olarak GÖSTERME (MHRS randevu hattı, kriz hattı değil).
- NHS 24, 111, 988, Samaritans, Mind, Anxiety UK gibi UK/US-özgü referansları KULLANMA.
- Fiziksel semptomu (göğüs ağrısı, nefes darlığı, bayılma, ani nörolojik belirti) "sadece kaygı" olarak normalleştirme.
- Krizde gizlilik sözü verme. Krizde yalnız kalmayı önerme.

YASAK CÜMLE KALIPLARI (tone):
"Bunu küçümsemiyorum", "sana çok üzüldüm", "seni anlıyorum", "duyguların çok
geçerli", "merak etme", "kafana takma", "harikasın" — bunları ASLA kullanma.
Performatiftir. Anladığını duyurmak için ayrı paragraf açma; tek cümlelik
teğet-doğrulama yeterli, hemen içeriğe geç.

TEKRARDAN KAÇIN:
Bir kalıbı, bir öneriyi ya da bir kez adlandırdığın örüntüyü tekrar etme.
Kabul edilmiş öneri kapanmıştır. Toparlama hamlesini bir seansta en fazla
bir kez yap.

SORU SORMA DENGESİ:
Tek mesajda tek soru. Son iki cevabında soru sorduysan bu cevapta sorma;
onun yerine bir gözlem, çerçeve ya da somut öneri sun. Kullanıcı açıkça yön
istiyorsa ("ne yapmalıyım") soruyla karşılık verme.

GÜVENLİK KONTROL SORUSU REDDEDİLDİYSE:
Reddi olduğu gibi kabul et. Israr etme, "emin misin" deme, uzun uzun özür
dileme. Kontrol sorusundan ÖNCEKİ konuya dön; o turda 112 ya da acil
yönlendirmesi verme.

KISA CEVAPLARI OLDUĞU GİBİ KABUL ET:
"Evet", "bilmiyorum", "tamam" son sorduğun soruya verilmiş cevaptır.
Netleştirme sorusu SORMA; cevabı al ve ilerlet. Hangisine cevap verildiği
belirsizse daha olası olanı seç, yanlışsa kullanıcı düzeltir.

# _COMPOSER_SYSTEM_TR içinde uygun bir yere ekle:

BAĞLAM KARTLARI HAKKINDA:
- Kartlarda 'NOT:' satırı varsa: bu kart ana odaktan değil, klinik komşuluk üzerinden
  ek bağlam olarak getirildi. Ana yanıtı bu karta değil, NOT'suz olan kartlara dayandır.
  Komşuluk kartını sadece "benzer bir dinamik başka konularda da görülür" gibi bir
  köprü kurmak için kullan. Kart ID'sini yazma.


TON:
- Sıcak ama sakin. Duyguyu ABARTMADAN kabul et.
- Sade Türkçe. Jargon geldiğinde tek cümlede çevir.
- Doğrudan konuya git. "İşte cevap:" gibi çerçeveleme kullanma.
- Emoji kullanma (kullanıcı kullanmadıysa).

SEANSIN YAYI (allow_cbt=true, düşük-risk yolu):
Bir CBT seansı bir yay izler. Sen soru sorup dinleyen bir anketör değilsin;
kullanıcıyla birlikte çalışan biri gibi ilerlersin. Konuşma nerede ise oraya
göre hamle seç.

1) KEŞİF — tablo henüz net değil.
   Ne olduğunu anlamaya çalış. Tek soru sor, kısa tut. Erken teknik önerme.
   Bu aşama 3-4 turdan uzun sürmemeli; sürekli soru sorup durumu deşmek
   kullanıcıyı yorar ve konuşmayı hiçbir yere götürmez.

2) FORMÜLASYON — tablo belli oldu.
   Anladığını topla ve adlandır: neyin neyi tetiklediğini, döngünün nasıl
   döndüğünü sade dille söyle. Burada soru sormana gerek yok; söylediğin şey
   yanlışsa kullanıcı düzeltir.

3) ÇALIŞMA — asıl iş burada.
   Bir CBT hamlesi yap. Bağlam kartlarındaki tekniklerden duruma uyanı seç:
   düşüncenin kanıtını sorgulamak, alternatif bir açıklama aramak, kaçınmayı
   fark etmek, küçük bir davranış denemesi kurmak, dikkati yönlendirmek gibi.
   Bu aşamada cevabın daha uzun olabilir — açıkla, örnekle, birlikte yürü.

4) PEKİŞTİRME — kullanıcı bir şey fark etti.
   Fark edileni sabitle ve kullanılabilir hale getir. Ne zaman işe yarayacağını,
   bir dahaki sefere nasıl hatırlanacağını konuş.

KULLANICI KENDİ KANITINI ÜRETTİĞİNDE:
Kendi deneyiminden bir kanıt sunduysa bu bir dönüm noktasıdır. Soru sorma;
kanıtı al, kaygılı tahminle gerçekte olan arasındaki farkı göster ve bir
sonraki sefere taşınabilir somut bir bağ kur.

CEVAP UZUNLUĞU:
Sabit bir uzunluk yok; içeriğe göre değişir. Keşif aşamasında iki-üç cümle
yeterli. Çalışma aşamasında bir tekniği gerçekten anlatıyorsan uzun olabilir —
sırf kısa tutmak için açıklamayı kesme. Ölçüt şu: her cümle bir iş yapıyor mu?
Doldurma yapma, ama gereken yerde de cimrilik etme.

BİÇİM:
- Bold, başlık, madde işareti kullanma. Adım sıralaman gerçekten gerekiyorsa
  en fazla 3 maddelik numaralı liste kullan.
- Ok işareti (→) ile şema çizme. Örüntüyü normal cümleyle anlat.
- Her cevabı soruyla bitirmek zorunda değilsin.

RESPONSE PATTERNİ (allow_cbt=false, safety hard-stop):
- SAFE_RESPONSE_TEMPLATE_TR'yi temel al. Kullanıcının anlattığına en fazla BİR cümlelik dokun; sonra template'in özünü ver.
- 112 mutlaka yer alsın.
- Uzman yönlendirmesi (aile hekimi / psikiyatri / klinik psikolog) mutlaka yer alsın.
- Hiçbir CBT egzersizi VERME.
- MUST_NOT_DO listesindeki her maddeye harfiyen uy.
- Cevabı 3-6 cümlede tut. Kısa ve net.

CEVABI SUNUŞ:
- Türkçe.
- Markdown başlığı (##), bold, italik kullanma.
- Kısa numaralı listeyi sadece gerçek bir adım sıralaması varsa kullan.
- "İşte cevabım:", "Umarım yardımcı olur", "Sorunuz için teşekkürler" gibi meta yorum ekleme.
- Doğrudan cevabı yaz.

İÇ METADATA'YI ASLA SIZDIRMA (kritik):
Prompt'ta kartlar `[CBT CARD: pa_grounding_004]`, `[SAFETY CARD: safety_self_harm_suicide_001]` gibi kimlik etiketleriyle geliyor. Bu ID'ler senin için — kullanıcı için değil.
- ASLA cevap metninde `ha_*`, `pa_*`, `ga_*`, `dep_*`, `lse_*`, `safety_*` şeklinde bir kart kimliği yazma.
- ASLA "X kartı" ya da "X card" diye kart yapısına atıfta bulunma.
- Kart içeriğini serbest Türkçeyle özümseyip aktarır gibi yaz. Örneğin "kaygı döngüsü şöyle işler…" yerine ASLA "ga_cycle_002 kartındaki döngü şöyle…" deme.
- "safety card", "cbt card", "concept", "route", "safety classifier", "critic" gibi sistem terimlerini de kullanma.



Bir cümle bile bu kuralı ihlal ederse cevap tamamen reddedilir ve baştan yazdırılır."""

# Session boundary — tek oturumu makul uzunlukta tutar, erişimi kesmez.
# Sınıra gelindiğinde konuşma bitmez; kullanıcıya bırakma seçeneği sunulur.
_MIDPOINT_CHECK = 12            # ara kontrol: anladığını yansıt, doğrula
_BOUNDARY_SOFT_START = 26       # ısınma başlar
_BOUNDARY_CLOSING_START = 34    # kapanış teklifi
_BOUNDARY_EXTENDED_END = 44     # son esneklik
_BOUNDARY_HARD = 45             # devir noktası
# Prompt building helpers


def _format_safety_card_full(card: dict) -> str:
    must_not = "\n  ".join(f"- {x}" for x in card.get("must_not_do_tr", []))
    return (
        f"[SAFETY CARD: {card['card_id']}]\n"
        f"  Başlık: {card['title']}\n"
        f"  Risk: {card['risk_level']}   Route: {card['route']}   allow_cbt: {card['allow_cbt']}\n"
        f"  MUST_DO:\n  {card.get('must_do_tr', '')}\n"
        f"  MUST_NOT_DO:\n  {must_not}\n"
        f"  SAFE_RESPONSE_TEMPLATE_TR:\n  {card.get('safe_response_template_tr', '')}\n"
    )


def _format_cbt_card_compact(
    card: dict,
    max_content_chars: int = 700,
    *,
    source: str = "vector",
    via_technique: Optional[str] = None,
    via_neighbor_of: Optional[str] = None,
) -> str:
    content = card["content_tr"]
    if len(content) > max_content_chars:
        content = content[:max_content_chars].rstrip() + " …"

    # Graph enrichment note — LLM'e kartın nasıl geldiğini söyle
    note = ""
    if source == "graph_technique" and via_technique:
        note = (
            f"  NOT: Bu kart ana odaktakilerle aynı tekniği paylaşıyor "
            f"({via_technique}). Aynı yaklaşımı farklı bağlamda önerebilirsin; "
            f"ana odak yerine geçirme.\n"
        )
    elif source == "graph_neighbor" and via_neighbor_of:
        note = (
            f"  NOT: Bu kart, ana konudaki '{via_neighbor_of}' kartının "
            f"klinik olarak komşu modülünden getirildi. Yalnız bağlam "
            f"olarak kullan; ana odak olarak sunma.\n"
        )

    return (
        f"[CBT CARD: {card['id']}]\n"
        f"  Başlık: {card['title_tr']}\n"
        f"  Konu: {card['topic']}   Tür: {card['type']}\n"
        f"{note}"
        f"  İçerik özeti:\n  {content}\n"
    )


def _stage_hint(turn_count: int, history: Optional[List[dict]]) -> str:
    """Konuşmanın hangi aşamada olduğunu ve son turlarda soru sorulup
    sorulmadığını modele açıkça bildirir."""
    turns = history or []
    recent = [t.get("response", "") or "" for t in turns[-2:]]
    asked_recently = sum(1 for r in recent if "?" in r)

    if turn_count <= 3:
        stage = (
            "Şu an KEŞİF aşamasındasın. Ne olduğunu anlamaya çalış, kısa tut."
        )
    elif turn_count <= 6:
        stage = (
            "Keşif aşaması yeterince sürdü. Artık FORMÜLASYONA geç: anladığın "
            "tabloyu adlandır ve bir CBT hamlesine zemin hazırla."
        )
    else:
        stage = (
            "Konuşma ÇALIŞMA aşamasında olmalı. Soru sorup durumu deşmeyi bırak; "
            "bağlam kartlarındaki bir tekniği bu duruma uygula ya da kullanıcının "
            "söylediği bir şeyin üstüne somut biçimde çalış."
        )

    lines = [f"KONUŞMANIN DURUMU:\n- Bu {turn_count}. tur. {stage}"]

    if asked_recently >= 2:
        lines.append(
            "- Son iki cevabında da soru sordun. Bu cevapta SORU SORMA; bir "
            "gözlem, bir çerçeve ya da somut bir öneri ver."
        )
    elif asked_recently == 1:
        lines.append(
            "- Son cevabında soru sordun. Bu turda soru sorman şart değil."
        )

    return "\n".join(lines) + "\n\n"


def _build_user_prompt(
    user_message: str,
    safety: SafetyDecision,
    retrieved: List[RetrievedCard],
    intent=None,
    history: Optional[List[dict]] = None,
    profile_summary: Optional[str] = None,
    turn_count: int = 0,
    process_block: str = "",
) -> str:
    safety_cards_full = _cards.safety_cards_by_id()
    cbt_cards_full = _cards.cbt_cards_by_id()

    safety_blocks = []
    cbt_blocks = []
    seen = set()

    # 1) Full detail for every safety card the classifier surfaced
    for cid in safety.safety_card_ids:
        c = safety_cards_full.get(cid)
        if c and cid not in seen:
            safety_blocks.append(_format_safety_card_full(c))
            seen.add(cid)

    # 2) Compact detail for retrieved CBT cards (skip safety ones already in)
    for r in retrieved:
        if r.card_id in seen:
            continue
        if r.topic == "safety":
            # A safety card came through retrieval but not the classifier
            # output — surface it too, in case of graceful degradation.
            c = safety_cards_full.get(r.card_id)
            if c:
                safety_blocks.append(_format_safety_card_full(c))
                seen.add(r.card_id)
            continue
        c = cbt_cards_full.get(r.card_id)
        if c:
            cbt_blocks.append(_format_cbt_card_compact(c, source=r.source, via_technique=r.via_technique, via_neighbor_of=r.via_neighbor_of))
            seen.add(r.card_id)

    branch_note = (
        "BRANCH: GÜVENLİK KONTROLÜ — ÇIKARIMA DAYALI, DOĞRULAMA GEREKİYOR.\n"
        "  Kullanıcının mesajından kriz işareti ÇIKARILDI ama kesin bir ifade\n"
        "  eşleşmesi yok. Doğrudan kriz metnini basma; önce doğru anlayıp\n"
        "  anlamadığını sor.\n"
        "\n"
        "  Cevabın şu üç parçadan oluşsun, kısa tut (en fazla 4 cümle):\n"
        "  1. Kullanıcının söylediğini bir cümleyle, olduğu gibi yansıt.\n"
        "  2. Ne anladığını açıkça ama yumuşak biçimde söyle. Örnek kalıp:\n"
        "     'Bunu okurken aklıma şu geldi: kendine zarar verme düşüncesi\n"
        "     olabilir mi, yoksa yanlış mı anladım?'\n"
        "  3. Yanıtı ona bırak. Hangi cevabı verirse versin sorun olmadığını belirt.\n"
        "\n"
        "  KURALLAR:\n"
        "  - Suçlayıcı ya da paniklemiş bir ton kullanma. Sakin ve sade ol.\n"
        "  - Henüz 112 ya da acil servis yönlendirmesi YAPMA; bu bir kontrol sorusu.\n"
        "  - Egzersiz verme, konu değiştirme, başka soru sorma.\n"
        "  - Kullanıcıyı etiketleme: 'krizdesin', 'intihar eğilimin var' deme."
    ) if getattr(safety, "needs_confirmation", False) and not safety.allow_cbt else (
        "BRANCH: allow_cbt = FALSE — SAFETY HARD STOP.\n"
        "  Yukarıdaki SAFETY CARD(S) altındaki SAFE_RESPONSE_TEMPLATE_TR temel olsun.\n"
        "  Kullanıcının anlattığına en fazla bir cümlelik kişiselleştirme ekle.\n"
        "  Hiçbir CBT egzersizi verme. MUST_NOT_DO listesini ihlal etme."
    ) if not safety.allow_cbt else (
        "BRANCH: allow_cbt = TRUE, blocks_exercise = TRUE — DESTEKLEYİCİ, EGZERSİZSİZ YOL.\n"
        "  Konuşma devam eder, sıcaklık korunur — ama bu turda EGZERSİZ, TEKNİK,\n"
        "  ADIM ADIM ÇALIŞMA ya da 'şunu dene' türü bir öneri VERİLMEZ.\n"
        "  Yukarıdaki SAFETY CARD(S)'ın SAFE_RESPONSE_TEMPLATE_TR'sini temel al,\n"
        "  kullanıcının anlattığına göre kişiselleştir.\n"
        "\n"
        "  KURALLAR:\n"
        "  - Neden egzersiz vermediğini kısaca ve dürüstçe söyle; geçiştirme.\n"
        "  - Uzman yönlendirmesini somut yap (aile hekimi, psikiyatri polikliniği).\n"
        "  - MUST_NOT_DO listesini harfiyen uygula.\n"
        "  - Konuşmayı kapatma; kullanıcıya ne konuşmak istediğini sor."
    ) if getattr(safety, "blocks_exercise", False) else (
        "BRANCH: allow_cbt = TRUE — CBT PATH.\n"
        "  Yukarıdaki CBT CARD(S) içinden en uygun 1-2'sini temel al.\n"
        "  Varsa SAFETY CARD(S)'ın must_not_do kurallarını AYNI ZAMANDA uygula (ör. doktora gitmesin diye tavsiye verme)."
    )

    nl = "\n"
    safety_section = nl.join(safety_blocks) if safety_blocks else "(bu mesajda safety fire etmedi)"
    cbt_section = nl.join(cbt_blocks) if cbt_blocks else "(retrieval boş ya da safety hard-stop)"
    safety_card_ids_str = str(safety.safety_card_ids) if safety.safety_card_ids else "[]"

    # Intent block — optional. Guides tone/subintent without changing safety.
    intent_block = ""
    if intent is not None:
        sub = getattr(intent, "subintent", "unknown")
        sec = ", ".join(intent.secondary_modules) if intent.secondary_modules else "yok"
        intent_block = (
            f"INTENT:\n"
            f"- primary_module: {intent.primary_module}\n"
            f"- secondary_modules: {sec}\n"
            f"- subintent: {sub}\n"
            f"- confidence: {intent.confidence:.2f}\n"
            f"- rationale: {intent.rationale}\n"
            f"\n"
            f"Subintent'e göre tonu ayarla:\n"
            f"  - psychoeducation → daha çok açıklama, adım sayısı 2-3 ile sınırlı.\n"
            f"  - exercise_request → doğrudan somut adımlara git, uzun psikoeğitim yapma.\n"
            f"  - ambiguous_symptom → kullanıcı henüz tabloyu anlatıyor. Kısa bir yansıtma "
            f"ve tek bir açık uçlu soru yeterli; bu aşamada egzersiz önerme.\n"
            f"  - boundary_request → tanı/ilaç/delay-care ise net bir sınır çiz, gerekçeyi kısa ver.\n"
            f"  - adversarial → politikayı sakince belirt, yeniden yönlendir; savunmacı olma.\n"
            f"  - crisis → SAFE_RESPONSE_TEMPLATE'i temel al, ek CBT içerik yok.\n\n"
        )

    history_block = _format_history_block(history) if history else ""

    # Profile block — arka planda çıkarılmış yapılandırılmış kullanıcı özeti.
    # LLM buna "kullanıcıyı hatırlıyorum" hissi kazandırmak için bakar.
    # Detayları ID formatında sıralama — doğal dil.
    profile_block = ""
    if profile_summary:
        profile_block = (
            f"KULLANICI PROFİLİ (önceki turnlerden yapılandırılmış):\n"
            f"{profile_summary}\n\n"
            f"Bu bilgiyi kullanarak kullanıcıya doğal bir 'seni hatırlıyorum' hissi ver. "
            f"Ama profil listesini AYNEN yazma; sadece bir ya da iki bağlantıyı zarif biçimde ör. "
            f"'Geçen konuşmada X'ten bahsetmiştin' gibi. Uydurma; sadece profildeki bilgiyi kullan.\n\n"
        )
    boundary_block = _boundary_prompt_layer(turn_count)
    stage_block = _stage_hint(turn_count, history)
    # Süreç bloğu seans yayının hemen ardında: "neredeyiz" bilgisinden sonra
    # "bu turda nasıl davranılır" geliyor, içerik kartlarından önce.
    process_prefix = f"{process_block}\n\n" if process_block else ""
    prompt = (
        f"{history_block}"
        f"{profile_block}"
        f"{stage_block}"
        f"{process_prefix}"
        f"{boundary_block}"
        f"KULLANICI MESAJI (bu turdaki):\n"
        f'"""{user_message}"""\n'
        f"\n"
        f"SAFETY DEĞERLENDİRMESİ:\n"
        f"- route: {safety.final_route}\n"
        f"- allow_cbt: {safety.allow_cbt}\n"
        f"- highest_risk: {safety.highest_risk}\n"
        f"- matched safety card ids: {safety_card_ids_str}\n"
        f"\n"
        f"{intent_block}"
        f"{branch_note}\n"
        f"\n"
        f"--- SAFETY CARDS (varsa) ---\n"
        f"{safety_section}\n"
        f"\n"
        f"--- RETRIEVED CBT CARDS ---\n"
        f"{cbt_section}\n"
        f"\n"
        f"GÖREV:\n"
        f"Yukarıdaki kurallara UYARAK, KONUŞMA GEÇMİŞİNİ dikkate alarak Türkçe bir cevap yaz. "
        f"Kullanıcının önceki mesajlarındaki bağlamı kaybetme (isim, durum, denenen egzersizler, vs). "
        f"Sadece cevabı ver; başlık, meta yorum ya da 'İşte cevabım:' gibi çerçeveleme ekleme.\n"
    )
    return prompt

def _boundary_prompt_layer(turn_count: int) -> str:
    """Session turn count'a göre composer prompt'una eklenecek katman.

    Faz 2 Deliverable #5: anti-addiction session boundary.

    Args:
        turn_count: session'ın bu turn dahil kaçıncı turn'ü (1-indexed)

    Returns:
        Sistem prompt'una eklenecek Türkçe direktif. turn_count normal
        aralıktaysa (< _BOUNDARY_SOFT_START) boş string döner.
    """
    if turn_count == _MIDPOINT_CHECK:
        return (
            "\n\nSEANS AKIŞI — ara kontrol:\n"
            "Konuşma bir yere geldi. Bu turda kullanıcının anlattıklarından "
            "çıkardığın tabloyu iki-üç cümlede topla ve doğru anlayıp "
            "anlamadığını sor.\n"
            "- Bu bir değerlendirme ya da teşhis değil; 'seni şöyle analiz ettim' "
            "  tonundan uzak dur. 'Anladığım şu, doğru mu?' tonu kullan.\n"
            "- Kullanıcıyı kategorize etme, özellik listesi çıkarma, güçlü/zayıf "
            "  yön sayma.\n"
            "- Sadece onun kendi anlattıklarını yansıt; yorum ekleme.\n"
            "- Sonda düzeltme alanı bırak: eksik ya da yanlış bir şey varsa "
            "  söylemesini iste."
        )

    if turn_count < _BOUNDARY_SOFT_START:
        return ""

    if turn_count < _BOUNDARY_CLOSING_START:
        return (
            "\n\nSEANS UZUNLUĞU — ısınma:\n"
            "Bu oturum uzadı. Cevaplarını kısalt ve dağılma. Yeni bir konu "
            "açma; kullanıcının şu an bulunduğu noktaya odaklan. Soru sorma "
            "sıklığını düşür — daha çok sen bir şey söyle."
        )

    if turn_count < _BOUNDARY_HARD:
        return (
            "\n\nSEANS UZUNLUĞU — toparlanma:\n"
            "Oturum epey uzadı. Bu turdan itibaren toparlanmaya yönel:\n"
            "- Yeni konu açma, yeni egzersiz başlatma.\n"
            "- Kullanıcının sorusunu yine cevapla ama kısa tut.\n"
            "- Konuşmanın bugün nereye geldiğini bir-iki cümlede topla; bunu "
            "  bir kez yap, sonraki turlarda tekrarlama.\n"
            "- Kullanıcı bir öneriyi kabul ettiyse üstüne ekleme yapma, kapat."
        )

    return (
        "\n\nSEANS AKIŞI — kapanışa yaklaşma:\n"
        "Bu oturum bugünlük yeterince uzadı. Kullanıcıyı engellemiyorsun; "
        "karar ona ait:\n"
        "- Bugün konuşulanları iki-üç cümlede topla.\n"
        "- Varsa üzerinde durduğunuz somut adımı bir kez hatırlat.\n"
        "- Sonda 'bugünlük burada bırakalım mı, yoksa devam mı edelim?' "
        "  diye sor. Dayatma, kapatma; gerçek bir soru olsun.\n"
        "- Yeni konu açma, yeni egzersiz verme.\n"
        "- Kullanıcı devam etmek isterse normal şekilde devam et, aynı "
        "  soruyu her turda tekrarlama."
    )

# History block formatter + summarizer
# Threshold: en son N tur ham metin gönderilir; öncesi Haiku ile özetlenir.
_MAX_VERBATIM_TURNS = 30
_MAX_SNIPPET_CHARS = 800  # tek turnun karakter tavanı — çok uzun mesajları kırp


def _format_history_block(history: List[dict]) -> str:
    """Format the last N turns as a prompt section.

    If history is short (<= _MAX_VERBATIM_TURNS), all turns go verbatim.
    Otherwise the older ones are collapsed into a Haiku-generated summary
    and the last N go verbatim.
    """
    if not history:
        return ""

    if len(history) <= _MAX_VERBATIM_TURNS:
        verbatim = history
        summary_prefix = ""
    else:
        old = history[: -_MAX_VERBATIM_TURNS]
        verbatim = history[-_MAX_VERBATIM_TURNS :]
        summary = _summarize_old_turns(old)
        summary_prefix = (
            f"KONUŞMANIN İLK BÖLÜMÜNÜN ÖZETİ ({len(old)} tur):\n{summary}\n\n"
        )

    lines = []
    total = len(verbatim)
    for i, t in enumerate(verbatim, 1):
        idx_from_end = total - i  # 0 = son tur
        # Uzun mesajları kırp — token bütçesi korunsun
        um = _trim(t.get("user_message", ""))
        rp = _trim(t.get("response", ""))
        lines.append(f"[Turn -{idx_from_end}]")
        lines.append(f"Kullanıcı: {um}")
        lines.append(f"Asistan: {rp}")
        lines.append("")

    return (
        f"--- KONUŞMA GEÇMİŞİ ---\n"
        f"{summary_prefix}"
        + "\n".join(lines)
        + "\n"
    )


def _trim(s: str, cap: int = _MAX_SNIPPET_CHARS) -> str:
    if len(s) <= cap:
        return s
    return s[:cap].rstrip() + " …"


# Cache: (n_turns, hash_of_content) -> summary string. In-process only.
# Prevents re-summarizing the same prefix every message in a long chat.
_SUMMARY_CACHE: dict = {}


def _summarize_old_turns(old_turns: List[dict]) -> str:
    """Ask Haiku for a compact summary of the older conversation.

    Cache keyed by content hash so a 60-turn chat only summarizes turns
    1..30 once, not on every incoming message.
    """
    import hashlib

    joined = "\n\n".join(
        f"Kullanıcı: {_trim(t.get('user_message',''))}\n"
        f"Asistan: {_trim(t.get('response',''))}"
        for t in old_turns
    )
    key = (len(old_turns), hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16])
    if key in _SUMMARY_CACHE:
        return _SUMMARY_CACHE[key]

    system = (
        "Sen bir CBT self-help konuşmasını özetleyensin. "
        "Aşağıdaki konuşmayı 150-200 kelimede Türkçe özetle. "
        "Sıralı liste kullan. Şunları koru: kullanıcının söylediği önemli olaylar/durumlar/tarihler (kişilerin somut isimlerini kullanma; 'partneri', 'annesi', 'iş arkadaşı' gibi rol adları kullan), "
        "belirtilen ana konular ve endişeler, denenen egzersizler, önemli yönlendirmeler (uzman/hekim). "
        "Atıfları rolüyle yaz: 'Kullanıcı işsizliğinden bahsetti', 'Chatbot nefes egzersizini önerdi' gibi. "
        "KVKK: Kullanıcının gerçek adı, soyadı, kimlik/telefon/adres bilgisi ÖZETTE YER ALMASIN — geçtiyse 'kullanıcı' olarak an. "
        "Meta yorum yapma, sadece özeti üret."
    )
    try:
        resp = llm_adapter.llm_complete(
            system=system,
            user=joined,
            model=config.LLM_MODEL_INTENT,  # Haiku — cheap
            max_tokens=400,
            temperature=0.0,
            redact=True,
        )
        summary = resp.text.strip()
    except Exception as e:
        summary = (
            f"(Önceki {len(old_turns)} turnün özeti üretilemedi: "
            f"{type(e).__name__}. Bağlam kısmen kayıp olabilir.)"
        )
    _SUMMARY_CACHE[key] = summary
    return summary



# Public API
@dataclass
class ComposedResponse:
    text: str
    model: str
    provider: str
    latency_ms: float
    branch: str          # "cbt" or "safety"
    prompt_tokens_est: int = 0
    debug_prompt: Optional[str] = None
    # Bu turda kullanılan süreç kartlarının kimlikleri — şeffaflık paneli
    # içerik kartlarından ayrı gösteriyor.
    process_card_ids: List[str] = field(default_factory=list)


def compose(
    user_message: str,
    safety: SafetyDecision,
    retrieved: List[RetrievedCard],
    *,
    intent=None,
    history: Optional[List[dict]] = None,
    profile_summary: Optional[str] = None,
    turn_count: int = 0,
    conversation_state: Optional[str] = None,
    include_prompt_in_debug: bool = False,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> ComposedResponse:
    """Generate a Turkish response for the user.

    Args:
        history: list of {user_message, response} dicts, oldest first.
                 The current user_message is NOT in history. If longer than
                 _MAX_VERBATIM_TURNS, older turns will be Haiku-summarized.
        profile_summary: structured user profile summary from profile_extractor.
                 Injected into prompt so LLM feels "remembers" the user across
                 sessions. If None, no profile context (first turn behavior).

    Returns ComposedResponse with the text and telemetry.
    """
    system = SYSTEM_PROMPT_TR

    # Süreç kartları: konuşmanın nasıl yürütüleceği. İçerik kartlarından
    # ayrı bir aile; konuya değil konuşma durumuna göre getiriliyor.
    process_selected = []
    if _process.enabled():
        process_selected = _process.select(
            conversation_state,
            turn_index=turn_count,
            allow_cbt=safety.allow_cbt,
            blocks_exercise=getattr(safety, "blocks_exercise", False),
        )

    user = _build_user_prompt(
        user_message, safety, retrieved,
        intent=intent, history=history, profile_summary=profile_summary,
        turn_count=turn_count,
        process_block=_process.format_for_prompt(process_selected),
    )
    branch = "cbt" if safety.allow_cbt else "safety"

    resp = llm_adapter.llm_complete(
        system=system,
        user=user,
        model=config.LLM_MODEL_COMPOSER,
        max_tokens=max_tokens,
        temperature=temperature,
        redact=True,   # KVKK — redact PII before LLM call
    )

    return ComposedResponse(
        text=resp.text.strip(),
        model=resp.model,
        provider=resp.provider,
        latency_ms=resp.latency_ms,
        branch=branch,
        prompt_tokens_est=(len(system) + len(user)) // 4,  # rough
        debug_prompt=(system + "\n\n---USER---\n" + user) if include_prompt_in_debug else None,
        process_card_ids=[c.id for c in process_selected],
    )
    
def get_boundary_state(turn_count: int) -> str:
    """turn_count → frontend'e döndürülecek state string."""
    if turn_count < _BOUNDARY_SOFT_START:
        return "normal"
    if turn_count < _BOUNDARY_CLOSING_START:
        return "warmup"
    if turn_count == _BOUNDARY_CLOSING_START:
        return "closing"
    if turn_count < _BOUNDARY_HARD:
        return "extended"
    return "hard_close"

# Mock handlers — for offline plumbing tests
def register_composer_mocks() -> None:
    """Register lightweight mock responses that reflect the branch.
    Useful for dry-run tests without an API key."""

    def _matches(system: str, user: str) -> bool:
        return "GÖREV:" in user and "SAFETY DEĞERLENDİRMESİ:" in user

    def _respond(system: str, user: str) -> str:
        if "allow_cbt: False" in user:
            return (
                "[MOCK/SAFETY] Anlattıkların ciddiye alınması gereken bir durum. "
                "Şu an güvende olman en önemli şey — lütfen 112'yi ara ya da en yakın acil servise git. "
                "Türkiye'de aile hekimi, psikiyatri uzmanı ya da klinik psikolog yönlendirmesi için "
                "aile hekimine başvurabilirsin. Bu chatbot kriz desteğinin yerine geçmez."
            )
        return (
            "[MOCK/CBT] Anlattığını duyuyorum — bu tarz düşünceler ve hisler zorlayıcı olabilir. "
            "Yaşadığın örüntü CBT'de \"kaygı döngüsü\" olarak tanımlanır: bir düşünce → beden tepkisi "
            "→ güvenlik davranışı → kısa vadeli rahatlama → uzun vadede döngü güçlenir. "
            "Küçük bir başlangıç olarak: bugün bir tetikleyici fark ettiğinde, 3 dakika bekleyip "
            "düşünceyi bir cümleyle yaz. Aciliyet hissini azaltmak için yeterli. "
            "Ne zamandır bu his sana eşlik ediyor?"
        )

    llm_adapter.register_mock_handler(_matches, _respond)


if __name__ == "__main__":
    # Sanity — build a prompt without calling any LLM.
    from .types import SafetyDecision, RetrievedCard
    sample_safety = SafetyDecision(
        matches=[], final_route="cbt_support", allow_cbt=True,
        blocks_exercise=False, highest_risk="low", safety_card_ids=[]
    )
    sample_retrieved = [
        RetrievedCard(card_id="pa_psychoed_001", topic="panic", type="psychoeducation",
                      title_tr="Panik atak nedir?", score=0.7, snippet="Panik atak..."),
    ]
    prompt = _build_user_prompt("Panik atak sırasında ne yapabilirim?", sample_safety, sample_retrieved)
    print(prompt[:1500])
