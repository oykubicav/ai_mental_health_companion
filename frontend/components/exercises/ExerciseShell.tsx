"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import ThemeToggle from "@/components/ThemeToggle";
import SiteFooter from "@/components/SiteFooter";

interface Source {
  id: string;
  title: string;
  topic: string;
}

// Egzersiz sayfalarının ortak iskeleti. Sayfanın altında aracın hangi
// kartlardan türetildiği görünür: klinik onay aynı hash'e bağlı kalıyor.
export default function ExerciseShell({
  title,
  intro,
  sources,
  children,
}: {
  title: string;
  intro: string;
  sources: Source[];
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-cbt-bg dark:bg-cbt-dark-bg">
      <header className="sticky top-0 z-20 border-b border-cbt-border/50 dark:border-cbt-dark-border/50 bg-cbt-bg/80 dark:bg-cbt-dark-bg/80 backdrop-blur-xl">
        <div className="max-w-2xl mx-auto flex items-center justify-between px-6 py-4">
          <Link
            href="/egzersizler"
            className="flex items-center gap-1.5 text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
          >
            <ArrowLeft size={15} strokeWidth={2} />
            Egzersizler
          </Link>
          <div className="flex items-center gap-2">
            <Link
              href="/"
              className="text-[13px] font-medium text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
            >
              Sohbete git
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-2xl w-full mx-auto px-6 pt-12 pb-24">
        <h1 className="display text-[38px] sm:text-[48px] leading-[1.06] text-cbt-text dark:text-cbt-dark-text mb-4">
          {title}
        </h1>
        <p className="text-[16px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed mb-10">
          {intro}
        </p>

        {children}

        <section className="mt-16 pt-6 border-t border-cbt-border/60 dark:border-cbt-dark-border/60">
          <h2 className="text-[12px] font-medium uppercase tracking-wide text-cbt-textMuted dark:text-cbt-dark-textMuted mb-3">
            Bu araç hangi kartlardan geliyor
          </h2>
          <ul className="space-y-1.5">
            {sources.map((s) => (
              <li key={s.id}>
                <Link
                  href={`/cards?topic=${s.topic}`}
                  className="text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text underline-offset-4 hover:underline"
                >
                  {s.title}
                </Link>
                <span className="ml-2 text-[11px] font-mono text-cbt-textMuted dark:text-cbt-dark-textMuted">
                  {s.id}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted leading-relaxed">
            Bu sayfa yapay zekâ çağırmaz; yazdıkların Anthropic&apos;e gitmez. Hesabın
            varsa kayıt Neva&apos;nın veritabanında sen silene kadar durur; yoksa
            sayfayı kapattığında gider.
          </p>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
