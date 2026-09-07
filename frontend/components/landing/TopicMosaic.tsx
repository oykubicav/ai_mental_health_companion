"use client";

import { useState } from "react";
import Reveal from "./Reveal";

// cards/cbt_cards.jsonl'deki 18 modül. Sayılar tests/test_review_status.py
// ile aynı kaynaktan; burada elle tutuluyor.
const TOPICS: { id: string; label: string; hint: string }[] = [
  { id: "gad", label: "Yaygın kaygı", hint: "Sürekli endişe, gevşeyememe" },
  { id: "panic", label: "Panik", hint: "Ani ataklar, beden belirtileri" },
  { id: "health_anxiety", label: "Sağlık kaygısı", hint: "Belirti kontrolü, güvence arayışı" },
  { id: "social_anxiety", label: "Sosyal kaygı", hint: "Yargılanma korkusu, kaçınma" },
  { id: "exam_anxiety", label: "Sınav kaygısı", hint: "Donma, erteleme, aile beklentisi" },
  { id: "depression", label: "Düşük ruh hali", hint: "İsteksizlik, geri çekilme" },
  { id: "low_self_esteem", label: "Özdeğer", hint: "İç eleştirmen, yetersizlik hissi" },
  { id: "insomnia", label: "Uyku", hint: "Uykuya dalamama, gece uyanma" },
  { id: "work_stress", label: "İş stresi", hint: "Tükenmişlik, sınır koyamama" },
  { id: "procrastination", label: "Erteleme", hint: "Başlayamama, mükemmelcilik" },
  { id: "anger", label: "Öfke", hint: "Patlama, sonrasında pişmanlık" },
  { id: "relationship_stress", label: "İlişkiler", hint: "Çatışma, iletişim örüntüleri" },
  { id: "grief_loss", label: "Kayıp ve yas", hint: "Yasın seyri, suçluluk" },
  { id: "life_transitions", label: "Yaşam değişimleri", hint: "Taşınma, ayrılık, yeni roller" },
  { id: "body_image", label: "Beden imajı", hint: "Ayna, kıyas, yeme örüntüleri" },
  { id: "chronic_pain", label: "Kronik ağrı", hint: "Ağrıyla yaşamak, hareket korkusu" },
  { id: "financial_stress", label: "Maddi kaygı", hint: "Borç, belirsizlik, utanç" },
  { id: "trauma_awareness", label: "Zor yaşantılar", hint: "Farkındalık, ne zaman uzman" },
];

export default function TopicMosaic() {
  const [hover, setHover] = useState<string | null>(null);
  const current = TOPICS.find((t) => t.id === hover);

  return (
    <div>
      <ul className="flex flex-wrap gap-2 sm:gap-2.5">
        {TOPICS.map((t, i) => (
          <Reveal key={t.id} as="li" delay={i * 30}>
            <a
              href={`/cards?topic=${t.id}`}
              onMouseEnter={() => setHover(t.id)}
              onMouseLeave={() => setHover(null)}
              onFocus={() => setHover(t.id)}
              onBlur={() => setHover(null)}
              className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-full border text-[14px] transition-all duration-200 ${
                hover === t.id
                  ? "bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg border-transparent -translate-y-0.5"
                  : "bg-cbt-surface dark:bg-cbt-dark-surface border-cbt-border dark:border-cbt-dark-border text-cbt-text dark:text-cbt-dark-text"
              }`}
            >
              {t.label}
              <span
                className={`text-[11px] tabular-nums ${
                  hover === t.id
                    ? "opacity-60"
                    : "text-cbt-textMuted dark:text-cbt-dark-textMuted"
                }`}
              >
                10
              </span>
            </a>
          </Reveal>
        ))}
      </ul>

      <div className="h-8 mt-5 text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary transition-opacity duration-200">
        {current ? (
          <span key={current.id} className="animate-fade-in">
            <span className="font-medium text-cbt-text dark:text-cbt-dark-text">{current.label}</span>
            {" — "}
            {current.hint}
          </span>
        ) : (
          <span className="text-cbt-textMuted dark:text-cbt-dark-textMuted">
            Her modülde 10 kart: nedir, döngü, kendini kontrol, teknikler, ne zaman uzman.
          </span>
        )}
      </div>
    </div>
  );
}
