"use client";

import { useEffect, useRef, useState } from "react";
import { ShieldCheck, Tag, Search, BookOpen, Stamp, RotateCcw } from "lucide-react";

// Sohbette her cevabın altındaki "nasıl üretildi" panelinin vitrin hâli.
// Örnekler hazır yazılmıştır; kart adları ve kimlikler gerçek kartlara ait.

interface Sample {
  id: string;
  thought: string;
  topic: string;
  trap: string;
  trapNote: string;
  card: string;
  cardId: string;
}

const SAMPLES: Sample[] = [
  {
    id: "exam",
    thought: "Bu sınavı kesin batıracağım, her şey bitecek.",
    topic: "Sınav kaygısı",
    trap: "Felaketleştirme",
    trapNote: "Tek bir sonuç bütün geleceğe yayılıyor.",
    card: "“Kazanamazsam her şey biter”",
    cardId: "exam_thoughts_004",
  },
  {
    id: "sleep",
    thought: "Saat üç, yine uyuyamıyorum. Yarın mahvolacağım.",
    topic: "Uyku",
    trap: "Felaketleştirme",
    trapNote: "Kötü bir gece, kötü bir gün demek değil.",
    card: "Yatakta dönen düşünceleri yeniden çerçevele",
    cardId: "insom_thoughtrec_007",
  },
  {
    id: "social",
    thought: "Toplantıda saçmaladım, herkes fark etti.",
    topic: "Sosyal kaygı",
    trap: "Zihin okuma",
    trapNote: "Başkalarının ne düşündüğü tahmin ediliyor, bilinmiyor.",
    card: "Olay sonrası geri sarma",
    cardId: "soc_postevent_006",
  },
  {
    id: "self",
    thought: "Hiçbir şeyi doğru düzgün yapamıyorum.",
    topic: "Özdeğer",
    trap: "Aşırı genelleme",
    trapNote: "Bir örnekten “hiçbir” ve “hep” türetiliyor.",
    card: "İç eleştirmenin tuzakları",
    cardId: "lse_innercritic_005",
  },
];

const STEP_GAP = 520;
const TYPE_SPEED = 22;

export default function PipelineDemo() {
  const [active, setActive] = useState<Sample | null>(null);
  const [typed, setTyped] = useState("");
  const [step, setStep] = useState(0);
  const timers = useRef<number[]>([]);

  function clearTimers() {
    timers.current.forEach((t) => window.clearTimeout(t));
    timers.current = [];
  }

  function run(sample: Sample) {
    clearTimers();
    setActive(sample);
    setTyped("");
    setStep(0);

    const chars = Array.from(sample.thought);
    chars.forEach((_, i) => {
      timers.current.push(
        window.setTimeout(() => setTyped(chars.slice(0, i + 1).join("")), i * TYPE_SPEED)
      );
    });
    const typingDone = chars.length * TYPE_SPEED + 350;
    for (let s = 1; s <= 5; s++) {
      timers.current.push(
        window.setTimeout(() => setStep(s), typingDone + (s - 1) * STEP_GAP)
      );
    }
  }

  function reset() {
    clearTimers();
    setActive(null);
    setTyped("");
    setStep(0);
  }

  useEffect(() => clearTimers, []);

  return (
    <div className="relative w-full max-w-md mx-auto lg:mx-0">
      <div className="rounded-[28px] bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border dark:border-cbt-dark-border shadow-[0_24px_60px_-30px_rgba(0,0,0,0.25)] dark:shadow-none overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-cbt-border/70 dark:border-cbt-dark-border/70">
          <span className="text-[12px] font-medium tracking-wide uppercase text-cbt-textMuted dark:text-cbt-dark-textMuted">
            Perde arkası
          </span>
          {active && (
            <button
              onClick={reset}
              className="flex items-center gap-1 text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
            >
              <RotateCcw size={12} strokeWidth={2} />
              Başka bir düşünce
            </button>
          )}
        </div>

        <div className="p-5 min-h-[340px] flex flex-col">
          {!active ? (
            <>
              <p className="text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed mb-4">
                Bir düşünce seç. Neva&apos;nın onu cevaplamadan önce ne yaptığını
                adım adım gör.
              </p>
              <ul className="flex flex-col gap-2">
                {SAMPLES.map((s, i) => (
                  <li key={s.id}>
                    <button
                      onClick={() => run(s)}
                      className="w-full text-left px-4 py-3 rounded-2xl bg-cbt-userBubble dark:bg-cbt-dark-userBubble text-[14px] text-cbt-userBubbleText dark:text-cbt-dark-userBubbleText hover:ring-2 ring-cbt-accent/40 dark:ring-cbt-dark-accent/40 transition-all active:scale-[0.99] animate-step-in"
                      style={{ animationDelay: `${i * 70}ms` }}
                    >
                      {s.thought}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <>
              <div className="self-end max-w-[90%] px-4 py-3 rounded-2xl rounded-br-md bg-cbt-userBubble dark:bg-cbt-dark-userBubble text-[14px] text-cbt-userBubbleText dark:text-cbt-dark-userBubbleText mb-5">
                {typed}
                {step === 0 && (
                  <span className="inline-block w-[2px] h-[14px] ml-0.5 align-middle bg-current animate-caret" />
                )}
              </div>

              <ol className="flex flex-col gap-2.5">
                {step >= 1 && (
                  <Row
                    icon={<ShieldCheck size={15} strokeWidth={2} />}
                    label="Güvenlik kontrolü"
                    value="Risk işareti yok"
                    tone="ok"
                  />
                )}
                {step >= 2 && (
                  <Row icon={<Tag size={15} strokeWidth={2} />} label="Konu" value={active.topic} />
                )}
                {step >= 3 && (
                  <Row
                    icon={<Search size={15} strokeWidth={2} />}
                    label="Düşünce tuzağı"
                    value={active.trap}
                    note={active.trapNote}
                  />
                )}
                {step >= 4 && (
                  <Row
                    icon={<BookOpen size={15} strokeWidth={2} />}
                    label="Kullanılan kart"
                    value={active.card}
                    note={active.cardId}
                    mono
                  />
                )}
                {step >= 5 && (
                  <Row
                    icon={<Stamp size={15} strokeWidth={2} />}
                    label="Klinik onay"
                    value="4 Eylül 2026"
                    note="Klinik psikolog · kart değişirse onay düşer"
                  />
                )}
              </ol>

              {step >= 5 && (
                <p className="mt-auto pt-5 text-[12px] leading-relaxed text-cbt-textMuted dark:text-cbt-dark-textMuted animate-step-in">
                  Cevap bu kartın içeriğiyle yazılır. Gerçek sohbette aynı panel
                  her cevabın altında açılır.
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({
  icon,
  label,
  value,
  note,
  tone,
  mono,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  note?: string;
  tone?: "ok";
  mono?: boolean;
}) {
  const valueCls =
    tone === "ok"
      ? "text-cbt-success dark:text-cbt-dark-success"
      : "text-cbt-text dark:text-cbt-dark-text";
  return (
    <li className="flex items-start gap-3 px-3.5 py-2.5 rounded-xl bg-cbt-surfaceMuted dark:bg-cbt-dark-surfaceMuted animate-step-in">
      <span className="mt-0.5 text-cbt-textMuted dark:text-cbt-dark-textMuted">{icon}</span>
      <div className="min-w-0">
        <div className="text-[11px] uppercase tracking-wide text-cbt-textMuted dark:text-cbt-dark-textMuted">
          {label}
        </div>
        <div className={`text-[14px] font-medium ${valueCls}`}>{value}</div>
        {note && (
          <div
            className={`text-[12px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary ${
              mono ? "font-mono" : ""
            }`}
          >
            {note}
          </div>
        )}
      </div>
    </li>
  );
}
