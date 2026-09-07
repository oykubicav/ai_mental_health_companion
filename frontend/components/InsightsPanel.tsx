"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Trash2 } from "lucide-react";
import { getMyInsights, deleteMyInsights } from "@/lib/api";
import type { InsightsResponse, Milestone } from "@/lib/types";

// Sayı değil, ilk'ler. Seri, rozet ya da "kaç gündür" yok — Neva'nın
// kullanıcıyı tutmaya çalışmama sözü burada da geçerli.
const EXERCISE_NAMES: Record<string, string> = {
  thought_record: "düşünce kaydı",
  small_step: "küçük adım planı",
  breathing: "nefes",
};

const MILESTONE_TEXT: Record<Milestone["kind"], (detail: string | null) => string> = {
  first_session: () => "İlk konuşma.",
  first_assessment: (d) => `İlk ölçüm${d ? ` (${d})` : ""}.`,
  first_technique: (d) => `İlk denediğin teknik${d ? `: ${d.toLowerCase()}` : ""}.`,
  first_helped: (d) => `İlk işe yaradı dediğin teknik${d ? `: ${d.toLowerCase()}` : ""}.`,
  first_exercise: (d) => `İlk egzersiz${d ? `: ${EXERCISE_NAMES[d] ?? d}` : ""}.`,
  first_journal: () => "İlk günlük kaydı.",
  first_referral: () => "Neva seni bir uzmana yönlendirdi. Bunu saklamıyoruz.",
};

function tarih(iso: string): string {
  return new Date(iso).toLocaleDateString("tr-TR", { day: "numeric", month: "long", year: "numeric" });
}

const VERDICT_LABELS: Record<string, string> = {
  "yararlı": "işe yaradı",
  "yararsız": "işe yaramadı",
  "denenmedi": "denenmedi",
  "deneyecek": "denenecek",
};

const VERDICT_STYLES: Record<string, string> = {
  "yararlı":
    "bg-cbt-successSoft dark:bg-cbt-dark-successSoft text-cbt-success dark:text-cbt-dark-success",
  "yararsız":
    "bg-cbt-surface dark:bg-cbt-dark-surface text-cbt-textMuted dark:text-cbt-dark-textMuted",
};

export default function InsightsPanel() {
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [silinecek, setSilinecek] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await getMyInsights());
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const sil = async () => {
    try {
      await deleteMyInsights();
      await load();
    } finally {
      setSilinecek(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-10">
        <Loader2 className="animate-spin text-cbt-textMuted" size={18} />
      </div>
    );
  }

  if (!data) return null;

  const bosMu =
    data.themes.length === 0 &&
    data.coping.length === 0 &&
    data.triggers.length === 0 &&
    data.milestones.length === 0;

  if (bosMu) {
    return (
      <p className="text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted leading-relaxed">
        Konuştukça burada birikecek: hangi konular tekrar ediyor, hangi
        teknikler sende işe yarıyor.
      </p>
    );
  }

  return (
    <div className="space-y-8">
      {data.milestones.length > 0 && (
        <section>
          <h3 className="text-[13px] font-medium text-cbt-textMuted dark:text-cbt-dark-textMuted mb-4">
            Yolculuk
          </h3>
          <ol className="relative border-l border-cbt-border dark:border-cbt-dark-border ml-1.5 space-y-5">
            {data.milestones.map((m) => (
              <li key={m.kind} className="pl-5 relative">
                <span
                  className={`absolute -left-[5px] top-[7px] w-[9px] h-[9px] rounded-full ${
                    m.kind === "first_referral"
                      ? "bg-cbt-warning dark:bg-cbt-dark-warning"
                      : "bg-cbt-accent dark:bg-cbt-dark-accent"
                  }`}
                />
                <div className="display text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted tabular-nums">
                  {tarih(m.at)}
                </div>
                <div className="text-[14px] text-cbt-text dark:text-cbt-dark-text">
                  {MILESTONE_TEXT[m.kind]?.(m.detail) ?? m.kind}
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      {data.coping.length > 0 && (
        <section>
          <h3 className="text-[13px] font-medium text-cbt-textMuted dark:text-cbt-dark-textMuted mb-3">
            Denediğin teknikler
          </h3>
          <div className="space-y-2">
            {data.coping.map((c) => (
              <div
                key={c.technique}
                className="flex items-center justify-between gap-3 py-2 border-b border-cbt-border/40 dark:border-cbt-dark-border/40 last:border-0"
              >
                <span className="text-[14px] text-cbt-text dark:text-cbt-dark-text">
                  {c.label}
                </span>
                <span
                  className={[
                    "text-[12px] px-2.5 py-1 rounded-full shrink-0",
                    VERDICT_STYLES[c.verdict] ||
                      "bg-cbt-surface dark:bg-cbt-dark-surface text-cbt-textSecondary dark:text-cbt-dark-textSecondary",
                  ].join(" ")}
                >
                  {VERDICT_LABELS[c.verdict] || c.verdict}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {data.themes.length > 0 && (
        <section>
          <h3 className="text-[13px] font-medium text-cbt-textMuted dark:text-cbt-dark-textMuted mb-3">
            Tekrar eden konular
          </h3>
          <div className="flex flex-wrap gap-2">
            {data.themes.map((t) => (
              <span
                key={t.label}
                className="text-[13px] px-3 py-1.5 rounded-full bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border/60 dark:border-cbt-dark-border/60 text-cbt-textSecondary dark:text-cbt-dark-textSecondary"
              >
                {t.label}
                {t.sessions > 1 && (
                  <span className="text-cbt-textMuted dark:text-cbt-dark-textMuted">
                    {" "}· {t.sessions} sohbet
                  </span>
                )}
              </span>
            ))}
          </div>
        </section>
      )}

      {data.triggers.length > 0 && (
        <section>
          <h3 className="text-[13px] font-medium text-cbt-textMuted dark:text-cbt-dark-textMuted mb-3">
            Anlattığın durumlar
          </h3>
          <div className="flex flex-wrap gap-2">
            {data.triggers.map((t) => (
              <span
                key={t}
                className="text-[13px] px-3 py-1.5 rounded-full bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border/60 dark:border-cbt-dark-border/60 text-cbt-textSecondary dark:text-cbt-dark-textSecondary"
              >
                {t}
              </span>
            ))}
          </div>
        </section>
      )}

      <div className="pt-2 border-t border-cbt-border/40 dark:border-cbt-dark-border/40">
        <p className="text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted leading-relaxed mb-3">
          Bunlar konuşmalarımızdan çıkarılmış notlar, bir değerlendirme ya da
          tanı değil. Yanlış olabilirler — öyleyse silebilirsin, sohbetlerin
          yerinde kalır.
        </p>
        {silinecek ? (
          <div className="flex items-center gap-2">
            <button
              onClick={sil}
              className="text-[12px] px-3 py-1.5 rounded-lg bg-cbt-danger/10 text-cbt-danger dark:text-cbt-dark-danger"
            >
              Evet, sil
            </button>
            <button
              onClick={() => setSilinecek(false)}
              className="text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted"
            >
              Vazgeç
            </button>
          </div>
        ) : (
          <button
            onClick={() => setSilinecek(true)}
            className="inline-flex items-center gap-1.5 text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-danger dark:hover:text-cbt-dark-danger transition-colors"
          >
            <Trash2 size={12} />
            Bu notları sil
          </button>
        )}
      </div>
    </div>
  );
}