"use client";

import { useState } from "react";
import { ArrowLeft, Check, Sprout, BookOpen, Stethoscope } from "lucide-react";
import { FOCUS_OPTIONS } from "@/lib/profile";
import { useAuth } from "@/hooks/AuthProvider";
import type { TherapyExperience } from "@/lib/types";

// Hesap açıldıktan sonra bir kez gösterilen dört adım. Cevaplar sunucuda
// (users.display_name / focus_topics / therapy_experience); son adım
// hiçbir şey kaydetmez, yalnızca Neva'nın ne olmadığını söyler.

type Step = 0 | 1 | 2 | 3;
const LAST: Step = 3;

const EXPERIENCE: {
  id: TherapyExperience;
  title: string;
  body: string;
  icon: React.ReactNode;
}[] = [
  {
    id: "none",
    title: "İlk kez",
    body: "Daha önce böyle bir şey denemedim.",
    icon: <Sprout size={20} strokeWidth={1.8} />,
  },
  {
    id: "some",
    title: "Biraz",
    body: "Kitap, uygulama ya da birkaç seans.",
    icon: <BookOpen size={20} strokeWidth={1.8} />,
  },
  {
    id: "ongoing",
    title: "Şu an bir uzmanla görüşüyorum",
    body: "Neva bunun yanında, yerine değil.",
    icon: <Stethoscope size={20} strokeWidth={1.8} />,
  },
];

const PROMISES: { title: string; body: string }[] = [
  {
    title: "Tanı koymaz.",
    body: "Söylediklerinden bir etiket çıkarmaz. Bu bir uzmanın işi.",
  },
  {
    title: "Yapay zekâdır, saklamaz.",
    body: "İnsan gibi davranmaz. Her cevabın nasıl üretildiğini altındaki panelden görebilirsin.",
  },
  {
    title: "Kriz anında rol yapmaz.",
    body: "Kendine zarar verme işareti gördüğünde teknik anlatmayı bırakır, gerçek bir insana ulaşmana yardım eder.",
  },
];

export default function Onboarding({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState<Step>(0);
  const [name, setName] = useState("");
  const [focus, setFocus] = useState<string[]>([]);
  const [experience, setExperience] = useState<TherapyExperience | null>(null);
  const [seen, setSeen] = useState<boolean[]>(PROMISES.map(() => false));
  const [saving, setSaving] = useState(false);
  const { updateProfile } = useAuth();

  function toggleFocus(id: string) {
    setFocus((prev) => {
      if (id === "unsure") return prev.includes("unsure") ? [] : ["unsure"];
      const rest = prev.filter((x) => x !== "unsure");
      return rest.includes(id) ? rest.filter((x) => x !== id) : [...rest, id];
    });
  }

  // Kayıt başarısız olsa da kullanıcı ekranda tutulmaz — sohbete geçmesi
  // profil kaydından önemli. Kaydedilmediyse bir sonraki girişte tekrar sorulur.
  async function save(payload: Parameters<typeof updateProfile>[0]) {
    if (saving) return;
    setSaving(true);
    try {
      await updateProfile(payload);
    } catch {
      // sessiz geç
    } finally {
      setSaving(false);
      onDone();
    }
  }

  function finish() {
    void save({
      display_name: name.trim(),
      focus_topics: focus,
      ...(experience ? { therapy_experience: experience } : {}),
    });
  }

  function next() {
    setStep((s) => (s < LAST ? ((s + 1) as Step) : s));
  }
  function back() {
    setStep((s) => (s > 0 ? ((s - 1) as Step) : s));
  }

  const allSeen = seen.every(Boolean);

  return (
    <div className="min-h-screen flex flex-col bg-cbt-bg dark:bg-cbt-dark-bg">
      <header className="px-6 py-5 flex items-center justify-between">
        <span className="display text-[22px] text-cbt-text dark:text-cbt-dark-text">Neva</span>
        <button
          onClick={() => void save({})}
          className="text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
        >
          Şimdilik geç
        </button>
      </header>

      <main className="flex-1 flex flex-col items-center px-6 pb-16">
        <div className="w-full max-w-xl">
          <div className="flex items-center gap-4 mt-4 sm:mt-10 mb-12">
            <button
              onClick={back}
              disabled={step === 0}
              aria-label="Geri"
              className="w-9 h-9 flex items-center justify-center rounded-full border border-cbt-border dark:border-cbt-dark-border text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text disabled:opacity-0 transition-all"
            >
              <ArrowLeft size={16} strokeWidth={2} />
            </button>
            <Progress step={step} />
          </div>

          {step === 0 && (
            <div key="s0" className="animate-slide-up">
              <Heading
                eyebrow="Hesabın hazır"
                title={
                  <>
                    Sana nasıl
                    <br />
                    hitap edelim?
                  </>
                }
                body="Gerçek adın olmak zorunda değil. Boş bırakırsan da olur; sadece konuşmayı biraz daha kendine ait hissettirir."
              />
              <input
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value.slice(0, 40))}
                onKeyDown={(e) => {
                  if (e.key === "Enter") next();
                }}
                placeholder="Adın"
                className="w-full px-5 h-14 rounded-2xl border border-cbt-border dark:border-cbt-dark-border bg-cbt-surface dark:bg-cbt-dark-surface text-[17px] text-cbt-text dark:text-cbt-dark-text placeholder:text-cbt-textMuted focus:outline-none focus:border-cbt-borderStrong dark:focus:border-cbt-dark-borderStrong transition-colors"
              />
              <Primary onClick={next}>Devam</Primary>
            </div>
          )}

          {step === 1 && (
            <div key="s1" className="animate-slide-up">
              <Heading
                title={
                  <>
                    {name ? `${name}, bu aralar` : "Bu aralar"}
                    <br />
                    seni ne meşgul ediyor?
                  </>
                }
                body="Birden fazla seçebilirsin. Bu seçim seni bir yere kilitlemez; konuştukça değişebilir."
              />
              <div className="flex flex-wrap gap-2 mb-10">
                {FOCUS_OPTIONS.map((o) => {
                  const active = focus.includes(o.id);
                  return (
                    <button
                      key={o.id}
                      onClick={() => toggleFocus(o.id)}
                      className={
                        active
                          ? "px-4 py-2.5 rounded-full text-[14px] font-medium bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg transition-all active:scale-[0.98]"
                          : "px-4 py-2.5 rounded-full text-[14px] bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border dark:border-cbt-dark-border text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:border-cbt-borderStrong dark:hover:border-cbt-dark-borderStrong hover:text-cbt-text dark:hover:text-cbt-dark-text transition-all active:scale-[0.98]"
                      }
                    >
                      {o.label}
                    </button>
                  );
                })}
              </div>
              <Primary onClick={next}>Devam</Primary>
            </div>
          )}

          {step === 2 && (
            <div key="s2" className="animate-slide-up">
              <Heading
                title={
                  <>
                    Daha önce böyle
                    <br />
                    bir şey denedin mi?
                  </>
                }
                body="Neva'nın seni nereden karşılayacağını belirler. Yanlış cevap yok."
              />
              <ul className="flex flex-col gap-3 mb-10">
                {EXPERIENCE.map((e) => {
                  const active = experience === e.id;
                  return (
                    <li key={e.id}>
                      <button
                        onClick={() => setExperience(e.id)}
                        className={`w-full text-left flex items-center gap-4 px-5 py-4 rounded-2xl border transition-all active:scale-[0.99] ${
                          active
                            ? "border-cbt-text dark:border-cbt-dark-text bg-cbt-surface dark:bg-cbt-dark-surface"
                            : "border-cbt-border dark:border-cbt-dark-border bg-cbt-surface dark:bg-cbt-dark-surface hover:border-cbt-borderStrong dark:hover:border-cbt-dark-borderStrong"
                        }`}
                      >
                        <span
                          className={
                            active
                              ? "text-cbt-accent dark:text-cbt-dark-accent"
                              : "text-cbt-textMuted dark:text-cbt-dark-textMuted"
                          }
                        >
                          {e.icon}
                        </span>
                        <span className="flex-1 min-w-0">
                          <span className="block text-[16px] font-medium text-cbt-text dark:text-cbt-dark-text">
                            {e.title}
                          </span>
                          <span className="block text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary">
                            {e.body}
                          </span>
                        </span>
                        <span
                          className={`w-5 h-5 rounded-full border flex items-center justify-center transition-colors ${
                            active
                              ? "bg-cbt-text dark:bg-cbt-dark-text border-transparent text-cbt-bg dark:text-cbt-dark-bg"
                              : "border-cbt-borderStrong dark:border-cbt-dark-borderStrong"
                          }`}
                        >
                          {active && <Check size={12} strokeWidth={3} />}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
              <Primary onClick={next}>Devam</Primary>
            </div>
          )}

          {step === 3 && (
            <div key="s3" className="animate-slide-up">
              <Heading
                title={
                  <>
                    Başlamadan önce
                    <br />
                    üç şey.
                  </>
                }
                body="Neva'nın ne yapmayacağını bilmek, ne yapacağını bilmekten daha önemli. Her birine dokun."
              />
              <ul className="flex flex-col gap-3 mb-10">
                {PROMISES.map((p, i) => {
                  const done = seen[i];
                  return (
                    <li key={p.title}>
                      <button
                        onClick={() =>
                          setSeen((prev) => prev.map((v, j) => (j === i ? true : v)))
                        }
                        className={`w-full text-left px-5 py-4 rounded-2xl border transition-all active:scale-[0.99] ${
                          done
                            ? "border-cbt-border dark:border-cbt-dark-border bg-cbt-surfaceMuted dark:bg-cbt-dark-surfaceMuted"
                            : "border-cbt-borderStrong dark:border-cbt-dark-borderStrong bg-cbt-surface dark:bg-cbt-dark-surface hover:-translate-y-0.5"
                        }`}
                      >
                        <span className="flex items-center justify-between gap-4">
                          <span className="display text-[22px] text-cbt-text dark:text-cbt-dark-text">
                            {p.title}
                          </span>
                          <span
                            className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-all ${
                              done
                                ? "bg-cbt-success dark:bg-cbt-dark-success text-white scale-100"
                                : "border border-cbt-borderStrong dark:border-cbt-dark-borderStrong"
                            }`}
                          >
                            {done && <Check size={13} strokeWidth={3} />}
                          </span>
                        </span>
                        {done && (
                          <span className="block mt-2 text-[14px] leading-relaxed text-cbt-textSecondary dark:text-cbt-dark-textSecondary animate-fade-in">
                            {p.body}
                          </span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
              <Primary onClick={finish} disabled={!allSeen || saving}>
                {saving ? "Kaydediliyor…" : allSeen ? "Konuşmaya başla" : "Üçüne de dokun"}
              </Primary>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function Progress({ step }: { step: Step }) {
  return (
    <div className="flex-1 flex gap-1.5" aria-label={`Adım ${step + 1} / ${LAST + 1}`}>
      {Array.from({ length: LAST + 1 }).map((_, i) => (
        <span
          key={i}
          className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
            i <= step
              ? "bg-cbt-text dark:bg-cbt-dark-text"
              : "bg-cbt-border dark:bg-cbt-dark-border"
          }`}
        />
      ))}
    </div>
  );
}

function Heading({
  eyebrow,
  title,
  body,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  body: string;
}) {
  return (
    <>
      {eyebrow && (
        <div className="text-[13px] font-medium text-cbt-accent dark:text-cbt-dark-accent mb-3">
          {eyebrow}
        </div>
      )}
      <h1 className="display text-[36px] sm:text-[46px] leading-[1.06] text-cbt-text dark:text-cbt-dark-text mb-4">
        {title}
      </h1>
      <p className="text-[15px] sm:text-[16px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed mb-8">
        {body}
      </p>
    </>
  );
}

function Primary({
  onClick,
  disabled,
  children,
}: {
  onClick: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="mt-2 w-full min-h-[52px] rounded-2xl bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[15px] font-medium hover:opacity-85 disabled:opacity-40 disabled:hover:opacity-40 transition-opacity"
    >
      {children}
    </button>
  );
}
