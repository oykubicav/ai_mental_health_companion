"use client";

import { useState } from "react";
import { FOCUS_OPTIONS } from "@/lib/profile";
import { useAuth } from "@/hooks/AuthProvider";

export default function Onboarding({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState<0 | 1>(0);
  const [name, setName] = useState("");
  const [focus, setFocus] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const { updateProfile } = useAuth();

  function toggle(id: string) {
    setFocus((prev) => {
      if (id === "unsure") return prev.includes("unsure") ? [] : ["unsure"];
      const withoutUnsure = prev.filter((x) => x !== "unsure");
      return withoutUnsure.includes(id)
        ? withoutUnsure.filter((x) => x !== id)
        : [...withoutUnsure, id];
    });
  }

  // Kayıt başarısız olsa da kullanıcıyı ekranda tutmuyoruz — sohbete geçmesi
  // profil kaydından önemli. Kaydedilmediyse bir sonraki girişte tekrar sorulur.
  async function save(payload: { display_name?: string; focus_topics?: string[] }) {
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
    void save({ display_name: name.trim(), focus_topics: focus });
  }

  function skip() {
    void save({});
  }

  return (
    <div className="min-h-screen flex flex-col bg-cbt-bg dark:bg-cbt-dark-bg">
      <header className="px-6 py-5 flex items-center justify-between">
        <span className="text-[17px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text">
          Neva
        </span>
        <button
          onClick={skip}
          className="text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
        >
          Şimdilik geç
        </button>
      </header>

      <main className="flex-1 flex items-center justify-center px-6 pb-20">
        <div className="w-full max-w-lg">
          {step === 0 ? (
            <div className="animate-fade-in">
              <div className="text-[13px] font-medium text-cbt-textMuted dark:text-cbt-dark-textMuted mb-3">
                Hesabın hazır
              </div>
              <h1 className="text-[32px] sm:text-[38px] font-semibold tracking-[-0.02em] text-cbt-text dark:text-cbt-dark-text leading-tight mb-3">
                Sana nasıl
                <br />
                hitap edelim?
              </h1>
              <p className="text-[15px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed mb-8">
                Gerçek adın olmak zorunda değil. Boş bırakırsan da olur —
                sadece konuşmayı biraz daha kendine ait hissettirmek için.
              </p>

              <input
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value.slice(0, 40))}
                onKeyDown={(e) => {
                  if (e.key === "Enter") setStep(1);
                }}
                placeholder="Adın"
                className="w-full px-5 h-14 rounded-2xl border border-cbt-border dark:border-cbt-dark-border bg-cbt-surface dark:bg-cbt-dark-surface text-[17px] text-cbt-text dark:text-cbt-dark-text placeholder:text-cbt-textMuted focus:outline-none focus:border-cbt-borderStrong dark:focus:border-cbt-dark-borderStrong transition-colors"
              />

              <button
                onClick={() => setStep(1)}
                className="mt-6 w-full h-12 rounded-xl bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[15px] font-medium hover:opacity-85 transition-opacity"
              >
                Devam
              </button>
            </div>
          ) : (
            <div className="animate-fade-in">
              <h1 className="text-[32px] sm:text-[38px] font-semibold tracking-[-0.02em] text-cbt-text dark:text-cbt-dark-text leading-tight mb-3">
                {name ? `${name}, bu aralar` : "Bu aralar"}
                <br />
                seni ne meşgul ediyor?
              </h1>
              <p className="text-[15px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed mb-8">
                Birden fazla seçebilirsin. Bu seçim seni bir yere kilitlemez;
                konuştukça değişebilir.
              </p>

              <div className="flex flex-wrap gap-2 mb-10">
                {FOCUS_OPTIONS.map((o) => {
                  const active = focus.includes(o.id);
                  return (
                    <button
                      key={o.id}
                      onClick={() => toggle(o.id)}
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

              <div className="flex items-center gap-3">
                <button
                  onClick={() => setStep(0)}
                  className="px-5 h-12 rounded-xl text-[15px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
                >
                  Geri
                </button>
                <button
                  onClick={finish}
                  disabled={saving}
                  className="flex-1 h-12 rounded-xl bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[15px] font-medium hover:opacity-85 disabled:opacity-50 transition-opacity"
                >
                  {saving ? "Kaydediliyor…" : "Konuşmaya başla"}
                </button>
              </div>
            </div>
          )}

          <div className="flex justify-center gap-1.5 mt-10">
            <Dot active={step === 0} />
            <Dot active={step === 1} />
          </div>
        </div>
      </main>
    </div>
  );
}

function Dot({ active }: { active: boolean }) {
  return (
    <span
      className={
        active
          ? "w-6 h-1.5 rounded-full bg-cbt-text dark:bg-cbt-dark-text transition-all"
          : "w-1.5 h-1.5 rounded-full bg-cbt-border dark:bg-cbt-dark-border transition-all"
      }
    />
  );
}
