"use client";

import { useState } from "react";
import { createExercise } from "@/lib/api";
import { useAuth } from "@/hooks/AuthProvider";
import PastEntries from "./PastEntries";
import type { SmallStepPayload } from "@/lib/types";

// "Eğer X olursa, Y yapacağım." Erteleme, davranışsal aktivasyon ve
// küçük hedef kartlarındaki ortak kalıp. Tek satır; büyük plan değil.

const ORNEKLER: SmallStepPayload[] = [
  { trigger: "sabah kahvemi bitirdiğimde", action: "10 dakika yürüyüşe çıkacağım", difficulty: 3 },
  { trigger: "ödevi açıp 5 dakika bakamayınca", action: "yalnızca ilk cümleyi yazacağım", difficulty: 2 },
  { trigger: "gece 23:00'te", action: "telefonu başka odaya koyacağım", difficulty: 4 },
];

export default function SmallStep() {
  const { isAuthenticated } = useAuth();
  const [data, setData] = useState<SmallStepPayload>({ trigger: "", action: "", difficulty: 3 });
  const [done, setDone] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const hazir = data.trigger.trim().length > 2 && data.action.trim().length > 2;
  const cokZor = data.difficulty >= 7;

  async function bitir() {
    setDone(true);
    if (!isAuthenticated || saving || saved) return;
    setSaving(true);
    try {
      await createExercise("small_step", data as unknown as Record<string, unknown>);
      setSaved(true);
      setRefreshKey((k) => k + 1);
    } catch {
      // ekranda kalır
    } finally {
      setSaving(false);
    }
  }

  function yeni() {
    setData({ trigger: "", action: "", difficulty: 3 });
    setDone(false);
    setSaved(false);
  }

  return (
    <div>
      {!done ? (
        <div className="space-y-8">
          <Field
            label="Eğer…"
            hint="Zaten olan bir şey: bir saat, bir yer, bir alışkanlığın bitişi."
            value={data.trigger}
            onChange={(v) => setData((d) => ({ ...d, trigger: v }))}
            placeholder="akşam yemeği bittiğinde"
          />
          <Field
            label="…o zaman"
            hint="Tek bir davranış. Beş dakikadan kısa, bugün yapılabilir."
            value={data.action}
            onChange={(v) => setData((d) => ({ ...d, action: v }))}
            placeholder="masayı topladıktan sonra 5 dakika dışarı çıkacağım"
          />

          <div>
            <div className="flex items-baseline justify-between mb-1">
              <label className="text-[13px] font-medium text-cbt-text dark:text-cbt-dark-text">
                Ne kadar zor?
              </label>
              <span className="display text-[28px] leading-none text-cbt-text dark:text-cbt-dark-text tabular-nums">
                {data.difficulty}
              </span>
            </div>
            <p className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary mb-4">
              0 kolay, 10 imkânsız. Hedef 3–5 arası: yapılacak kadar kolay, sayılacak kadar gerçek.
            </p>
            <input
              type="range"
              min={0}
              max={10}
              value={data.difficulty}
              onChange={(e) => setData((d) => ({ ...d, difficulty: Number(e.target.value) }))}
              className="w-full accent-cbt-accent dark:accent-cbt-dark-accent"
            />
            {cokZor && (
              <p className="mt-3 text-[13px] text-cbt-warning dark:text-cbt-dark-warning animate-fade-in">
                Bu büyük bir adım. Yarısını, hatta çeyreğini yazsan? Küçük adım tamamlanır; büyük
                adım ertelenir.
              </p>
            )}
          </div>

          {!data.trigger && !data.action && (
            <div>
              <div className="text-[12px] font-medium uppercase tracking-wide text-cbt-textMuted dark:text-cbt-dark-textMuted mb-2">
                Örnek
              </div>
              <ul className="space-y-1.5">
                {ORNEKLER.map((o) => (
                  <li key={o.trigger}>
                    <button
                      onClick={() => setData(o)}
                      className="text-left text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text"
                    >
                      Eğer {o.trigger}, {o.action}.
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <button
            onClick={bitir}
            disabled={!hazir}
            className="w-full min-h-[52px] rounded-2xl bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[15px] font-medium hover:opacity-85 disabled:opacity-40 transition-opacity"
          >
            Planı yaz
          </button>
        </div>
      ) : (
        <div className="animate-slide-up">
          <Plan data={data} big />
          <p className="mt-6 text-[15px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed">
            Bu kadar. Yapınca ya da yapamayınca geri gel; ikisi de bilgi. Yapamadıysan adım büyüktü,
            sen değil.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={yeni}
              className="px-5 h-10 rounded-full bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[14px] font-medium hover:opacity-85"
            >
              Yeni plan
            </button>
            {isAuthenticated ? (
              <span className="text-[13px] text-cbt-success dark:text-cbt-dark-success">
                {saving ? "Kaydediliyor…" : saved ? "Kaydedildi" : ""}
              </span>
            ) : (
              <span className="text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted">
                Hesabın yoksa bu plan yalnızca bu sekmede.
              </span>
            )}
          </div>
        </div>
      )}

      <PastEntries
        kind="small_step"
        refreshKey={refreshKey}
        render={(e) => <Plan data={e.payload as unknown as SmallStepPayload} />}
      />
    </div>
  );
}

function Plan({ data, big = false }: { data: SmallStepPayload; big?: boolean }) {
  return (
    <p
      className={`display leading-snug text-cbt-text dark:text-cbt-dark-text ${
        big ? "text-[26px] sm:text-[32px]" : "text-[17px]"
      }`}
    >
      Eğer <span className="text-cbt-accent dark:text-cbt-dark-accent">{data.trigger}</span>,{" "}
      {data.action}.
      <span className="ml-2 text-[13px] font-sans text-cbt-textMuted dark:text-cbt-dark-textMuted tabular-nums">
        zorluk {data.difficulty}
      </span>
    </p>
  );
}

function Field({
  label,
  hint,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <div>
      <label className="display block text-[22px] text-cbt-text dark:text-cbt-dark-text mb-1">{label}</label>
      <p className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary mb-3">{hint}</p>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value.slice(0, 160))}
        placeholder={placeholder}
        className="w-full px-5 h-14 rounded-2xl border border-cbt-border dark:border-cbt-dark-border bg-cbt-surface dark:bg-cbt-dark-surface text-[17px] text-cbt-text dark:text-cbt-dark-text placeholder:text-cbt-textMuted/70 focus:outline-none focus:border-cbt-borderStrong dark:focus:border-cbt-dark-borderStrong"
      />
    </div>
  );
}
