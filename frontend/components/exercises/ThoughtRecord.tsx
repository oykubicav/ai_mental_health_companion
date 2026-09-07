"use client";

import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { createExercise } from "@/lib/api";
import { useAuth } from "@/hooks/AuthProvider";
import PastEntries from "./PastEntries";
import type { ThoughtRecordPayload } from "@/lib/types";

// Kartlardaki yedi soruluk düşünce kaydının tek form hâli. Her adım tek
// soru; ilerlemek için doldurmak şart değil — boş bırakıp geçmek de bilgi.

export const TRAPS: { id: string; label: string; hint: string }[] = [
  { id: "catastrophizing", label: "Felaketleştirme", hint: "En kötü sonucu tek sonuç sanmak" },
  { id: "mind_reading", label: "Zihin okuma", hint: "Başkasının ne düşündüğünü bildiğini varsaymak" },
  { id: "overgeneralizing", label: "Aşırı genelleme", hint: "Bir örnekten “hep / hiç” çıkarmak" },
  { id: "all_or_nothing", label: "Hep ya da hiç", hint: "Ara ton yok; ya mükemmel ya başarısız" },
  { id: "labeling", label: "Etiketleme", hint: "Bir davranış yerine kendine ad koymak" },
  { id: "personalizing", label: "Kişiselleştirme", hint: "Senden bağımsız şeyleri üstlenmek" },
  { id: "discounting", label: "Olumluyu yok sayma", hint: "İyi gideni “sayılmaz” demek" },
  { id: "fortune_telling", label: "Kehanet", hint: "Gelecekteki sonucu kesin bilmek" },
];

const EMPTY: ThoughtRecordPayload = {
  situation: "",
  thought: "",
  emotion: "",
  intensity_before: 60,
  traps: [],
  evidence_for: "",
  evidence_against: "",
  alternative: "",
  intensity_after: 60,
};

type StepDef = {
  key: keyof ThoughtRecordPayload;
  title: string;
  hint: string;
  kind: "text" | "textarea" | "slider" | "traps";
  placeholder?: string;
};

const STEPS: StepDef[] = [
  {
    key: "situation",
    title: "Ne oldu?",
    hint: "Yalnızca olay. Yorum yok, sadece kamera ne kaydederdi.",
    kind: "text",
    placeholder: "Toplantıda sunum yaparken sesim titredi",
  },
  {
    key: "thought",
    title: "O an aklından ne geçti?",
    hint: "İlk gelen cümle. Düzeltme, olduğu gibi yaz.",
    kind: "textarea",
    placeholder: "Herkes beceriksiz olduğumu anladı",
  },
  {
    key: "emotion",
    title: "Ne hissettin?",
    hint: "Tek kelime yeter: utanç, korku, öfke, çaresizlik…",
    kind: "text",
    placeholder: "Utanç",
  },
  {
    key: "intensity_before",
    title: "Ne kadar güçlüydü?",
    hint: "0 hiç, 100 dayanılmaz.",
    kind: "slider",
  },
  {
    key: "traps",
    title: "Bu düşüncede bir tuzak var mı?",
    hint: "Olmayabilir. Varsa işaretle; adı olunca küçülür.",
    kind: "traps",
  },
  {
    key: "evidence_for",
    title: "Bu düşünceyi destekleyen kanıt",
    hint: "Gerçekten olan şeyler. His değil, olgu.",
    kind: "textarea",
    placeholder: "Bir kişi telefonuna baktı",
  },
  {
    key: "evidence_against",
    title: "Bu düşünceye ters düşen kanıt",
    hint: "Bir arkadaşın anlatsa ona ne hatırlatırdın?",
    kind: "textarea",
    placeholder: "İki kişi soru sordu, biri sonra teşekkür etti",
  },
  {
    key: "alternative",
    title: "Daha dengeli bir cümle",
    hint: "Pembe değil, adil. İki kanıtı da içeren bir cümle.",
    kind: "textarea",
    placeholder: "Sesim titredi ama sunum bitti; dinleyenlerin çoğu ilgiliydi",
  },
  {
    key: "intensity_after",
    title: "Şimdi ne kadar güçlü?",
    hint: "Aynı his. Düşmek zorunda değil; bazen sadece netleşir.",
    kind: "slider",
  },
];

export default function ThoughtRecord() {
  const { isAuthenticated } = useAuth();
  const [data, setData] = useState<ThoughtRecordPayload>(EMPTY);
  const [step, setStep] = useState(0);
  const [finished, setFinished] = useState(false);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const def = STEPS[step];
  const last = step === STEPS.length - 1;

  function set<K extends keyof ThoughtRecordPayload>(k: K, v: ThoughtRecordPayload[K]) {
    setData((d) => ({ ...d, [k]: v }));
  }

  function next() {
    if (last) setFinished(true);
    else setStep((s) => s + 1);
  }

  function reset() {
    setData(EMPTY);
    setStep(0);
    setFinished(false);
    setSaved(false);
  }

  async function kaydet() {
    if (saving || saved) return;
    setSaving(true);
    try {
      await createExercise("thought_record", data as unknown as Record<string, unknown>);
      setSaved(true);
      setRefreshKey((k) => k + 1);
    } catch {
      // kaydedilmedi; özet ekranda kalır
    } finally {
      setSaving(false);
    }
  }

  if (finished) {
    const fark = data.intensity_before - data.intensity_after;
    return (
      <div>
        <Summary data={data} />
        <p className="mt-6 text-[15px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed">
          {fark > 10
            ? `${data.emotion || "His"} ${data.intensity_before}'den ${data.intensity_after}'e indi. Düşünce değişmedi belki; ama artık tek başına değil.`
            : fark < -5
              ? "His arttı. Bu da olur — bazen yazınca daha görünür olur. Bunu Neva'yla konuşmak isteyebilirsin."
              : "His çok değişmedi. Normal; kayıt tutmak bir seferde değil, tekrarla iş görür."}
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            onClick={reset}
            className="px-5 h-10 rounded-full bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[14px] font-medium hover:opacity-85"
          >
            Yeni kayıt
          </button>
          {isAuthenticated ? (
            saved ? (
              <span className="text-[13px] text-cbt-success dark:text-cbt-dark-success">Kaydedildi</span>
            ) : (
              <button
                onClick={kaydet}
                disabled={saving}
                className="text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text disabled:opacity-50"
              >
                {saving ? "Kaydediliyor…" : "Kaydet"}
              </button>
            )
          ) : (
            <span className="text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted">
              Hesabın olsaydı bu kayıt dururdu; şimdilik yalnızca bu sekmede.
            </span>
          )}
        </div>
        <Past refreshKey={refreshKey} />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-4 mb-10">
        <button
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0}
          aria-label="Geri"
          className="w-9 h-9 flex items-center justify-center rounded-full border border-cbt-border dark:border-cbt-dark-border text-cbt-textSecondary dark:text-cbt-dark-textSecondary disabled:opacity-0 transition-all"
        >
          <ArrowLeft size={16} strokeWidth={2} />
        </button>
        <div className="flex-1 flex gap-1">
          {STEPS.map((s, i) => (
            <span
              key={s.key}
              className={`h-1 flex-1 rounded-full transition-colors ${
                i <= step ? "bg-cbt-text dark:bg-cbt-dark-text" : "bg-cbt-border dark:bg-cbt-dark-border"
              }`}
            />
          ))}
        </div>
      </div>

      <div key={def.key} className="animate-slide-up">
        <h2 className="display text-[30px] sm:text-[36px] leading-[1.1] text-cbt-text dark:text-cbt-dark-text mb-2">
          {def.title}
        </h2>
        <p className="text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary mb-7">{def.hint}</p>

        {def.kind === "text" && (
          <input
            autoFocus
            value={data[def.key] as string}
            onChange={(e) => set(def.key, e.target.value.slice(0, 200) as never)}
            onKeyDown={(e) => {
              if (e.key === "Enter") next();
            }}
            placeholder={def.placeholder}
            className="w-full px-5 h-14 rounded-2xl border border-cbt-border dark:border-cbt-dark-border bg-cbt-surface dark:bg-cbt-dark-surface text-[17px] text-cbt-text dark:text-cbt-dark-text placeholder:text-cbt-textMuted/70 focus:outline-none focus:border-cbt-borderStrong dark:focus:border-cbt-dark-borderStrong"
          />
        )}

        {def.kind === "textarea" && (
          <textarea
            autoFocus
            value={data[def.key] as string}
            onChange={(e) => set(def.key, e.target.value.slice(0, 800) as never)}
            placeholder={def.placeholder}
            rows={4}
            className="w-full px-5 py-4 rounded-2xl border border-cbt-border dark:border-cbt-dark-border bg-cbt-surface dark:bg-cbt-dark-surface text-[17px] leading-relaxed text-cbt-text dark:text-cbt-dark-text placeholder:text-cbt-textMuted/70 focus:outline-none focus:border-cbt-borderStrong dark:focus:border-cbt-dark-borderStrong resize-none"
          />
        )}

        {def.kind === "slider" && (
          <div className="py-4">
            <div className="display text-[64px] leading-none text-cbt-text dark:text-cbt-dark-text tabular-nums mb-6">
              {data[def.key] as number}
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={data[def.key] as number}
              onChange={(e) => set(def.key, Number(e.target.value) as never)}
              className="w-full accent-cbt-accent dark:accent-cbt-dark-accent"
            />
            <div className="flex justify-between text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted mt-2">
              <span>Hiç</span>
              <span>Dayanılmaz</span>
            </div>
          </div>
        )}

        {def.kind === "traps" && (
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {TRAPS.map((t) => {
              const active = data.traps.includes(t.id);
              return (
                <li key={t.id}>
                  <button
                    onClick={() =>
                      set(
                        "traps",
                        active ? data.traps.filter((x) => x !== t.id) : [...data.traps, t.id]
                      )
                    }
                    className={`w-full text-left px-4 py-3 rounded-2xl border transition-all ${
                      active
                        ? "border-cbt-text dark:border-cbt-dark-text bg-cbt-surface dark:bg-cbt-dark-surface"
                        : "border-cbt-border dark:border-cbt-dark-border bg-cbt-surface dark:bg-cbt-dark-surface hover:border-cbt-borderStrong dark:hover:border-cbt-dark-borderStrong"
                    }`}
                  >
                    <span className="block text-[15px] font-medium text-cbt-text dark:text-cbt-dark-text">
                      {t.label}
                    </span>
                    <span className="block text-[12px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary">
                      {t.hint}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        <button
          onClick={next}
          className="mt-8 w-full min-h-[52px] rounded-2xl bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[15px] font-medium hover:opacity-85 transition-opacity"
        >
          {last ? "Bitir" : "Devam"}
        </button>
      </div>

      <Past refreshKey={refreshKey} />
    </div>
  );
}

function Past({ refreshKey }: { refreshKey: number }) {
  return (
    <PastEntries
      kind="thought_record"
      refreshKey={refreshKey}
      render={(e) => <Summary data={e.payload as unknown as ThoughtRecordPayload} compact />}
    />
  );
}

function Summary({ data, compact = false }: { data: ThoughtRecordPayload; compact?: boolean }) {
  const trapLabels = TRAPS.filter((t) => data.traps?.includes(t.id)).map((t) => t.label);
  return (
    <div className={compact ? "space-y-2" : "space-y-4"}>
      <Row label="Durum" value={data.situation} compact={compact} />
      <Row label="Düşünce" value={data.thought} compact={compact} />
      <Row
        label="His"
        value={`${data.emotion || "—"} · ${data.intensity_before} → ${data.intensity_after}`}
        compact={compact}
      />
      {trapLabels.length > 0 && <Row label="Tuzak" value={trapLabels.join(", ")} compact={compact} />}
      {!compact && <Row label="Lehte" value={data.evidence_for} />}
      {!compact && <Row label="Aleyhte" value={data.evidence_against} />}
      <Row label="Dengeli cümle" value={data.alternative} emphasis compact={compact} />
    </div>
  );
}

function Row({
  label,
  value,
  emphasis,
  compact,
}: {
  label: string;
  value: string;
  emphasis?: boolean;
  compact?: boolean;
}) {
  if (!value) return null;
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-cbt-textMuted dark:text-cbt-dark-textMuted">
        {label}
      </div>
      <div
        className={`${compact ? "text-[14px]" : "text-[15px]"} leading-relaxed ${
          emphasis
            ? "display text-[18px] text-cbt-text dark:text-cbt-dark-text"
            : "text-cbt-text dark:text-cbt-dark-text"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
