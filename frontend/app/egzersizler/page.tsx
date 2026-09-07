import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import PageShell from "@/components/PageShell";

export const metadata = {
  title: "Egzersizler — Neva",
  description: "Sohbetten bağımsız çalışan üç araç: nefes, düşünce kaydı, küçük adım.",
};

const TOOLS = [
  {
    href: "/egzersizler/nefes",
    title: "Nefes",
    when: "Kalbin hızlandığında, uyumadan önce, toplantıdan önce.",
    what: "Diyafram, kutu ya da 4-7-8. Daire büyür, küçülür; sen takip edersin.",
    minutes: "1–5 dk",
  },
  {
    href: "/egzersizler/dusunce-kaydi",
    title: "Düşünce kaydı",
    when: "Bir düşünce kafanda dönüp duruyorsa.",
    what: "Yedi soru: ne oldu, ne düşündün, kanıt ne, daha adil cümle ne.",
    minutes: "5–10 dk",
  },
  {
    href: "/egzersizler/kucuk-adim",
    title: "Küçük adım",
    when: "Başlayamıyorsan. Ertelerken, hiçbir şey yapasın gelmezken.",
    what: "Eğer X olursa, Y yapacağım. Tek satır, bugün yapılabilir.",
    minutes: "2 dk",
  },
];

export default function EgzersizlerPage() {
  return (
    <PageShell
      title="Egzersizler"
      intro="Sohbet etmeden de kullanabileceğin üç araç. Yapay zekâ yok, üyelik şart değil; kartlardaki tekniklerin elle tutulur hâli."
    >
      <ul className="grid grid-cols-1 gap-4">
        {TOOLS.map((t) => (
          <li key={t.href}>
            <Link
              href={t.href}
              className="group block p-7 rounded-[24px] bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border/60 dark:border-cbt-dark-border/60 hover:border-cbt-borderStrong dark:hover:border-cbt-dark-borderStrong hover:-translate-y-0.5 transition-all"
            >
              <div className="flex items-start justify-between gap-6">
                <div>
                  <div className="display text-[28px] leading-tight text-cbt-text dark:text-cbt-dark-text mb-2">
                    {t.title}
                  </div>
                  <p className="text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed">
                    <span className="text-cbt-text dark:text-cbt-dark-text">Ne zaman:</span> {t.when}
                  </p>
                  <p className="text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed">
                    <span className="text-cbt-text dark:text-cbt-dark-text">Ne:</span> {t.what}
                  </p>
                </div>
                <div className="shrink-0 flex flex-col items-end gap-3">
                  <span className="text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted tabular-nums">
                    {t.minutes}
                  </span>
                  <ArrowUpRight
                    size={18}
                    className="text-cbt-textMuted dark:text-cbt-dark-textMuted group-hover:text-cbt-text dark:group-hover:text-cbt-dark-text transition-colors"
                  />
                </div>
              </div>
            </Link>
          </li>
        ))}
      </ul>
      <section className="p-7 rounded-[24px] border border-dashed border-cbt-border dark:border-cbt-dark-border">
        <div className="display text-[24px] text-cbt-text dark:text-cbt-dark-text mb-2">
          Günlük
        </div>
        <p className="text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed mb-4">
          Araç değil, alışkanlık: her gün ne olduğunu, aklından ne geçtiğini
          ve iyi gelen bir şeyi kısaca yazabileceğin yer. Hesap gerektirir —
          günler arasında durması gerekiyor.
        </p>
        <Link
          href="/gunluk"
          className="inline-flex items-center gap-1.5 text-[14px] text-cbt-accent dark:text-cbt-dark-accent hover:underline underline-offset-4"
        >
          Günlüğü aç
          <ArrowUpRight size={14} strokeWidth={2} />
        </Link>
      </section>

      <p className="text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted leading-relaxed">
        Bunlar kriz araçları değil. Kendine zarar verme düşüncen varsa nefes egzersizi değil,
        bir insan gerekir:{" "}
        <Link href="/acil" className="underline underline-offset-4 hover:text-cbt-text dark:hover:text-cbt-dark-text">
          acil durumlar
        </Link>
        .
      </p>
    </PageShell>
  );
}
