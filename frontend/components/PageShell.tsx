import Link from "next/link";
import SiteFooter from "./SiteFooter";
import ThemeToggle from "./ThemeToggle";
import Reveal from "./landing/Reveal";

// Metin sayfalarının ortak iskeleti (/hakkinda, /gizlilik, /kaynaklar,
// /acil, /egzersizler). Vitrinle aynı dil: serif başlık, kâğıt dokusu,
// kaydırınca beliren bloklar.

export default function PageShell({
  title,
  intro,
  children,
}: {
  title: string;
  intro?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col bg-cbt-bg dark:bg-cbt-dark-bg">
      <header className="sticky top-0 z-20 border-b border-cbt-border/50 dark:border-cbt-dark-border/50 bg-cbt-bg/80 dark:bg-cbt-dark-bg/80 backdrop-blur-xl">
        <div className="max-w-3xl mx-auto flex items-center justify-between px-6 py-4">
          <Link
            href="/"
            className="display text-[22px] text-cbt-text dark:text-cbt-dark-text"
          >
            Neva
          </Link>
          <div className="flex items-center gap-2">
            <Link
              href="/cards"
              className="hidden sm:flex px-3 h-9 items-center rounded-full text-[13px] font-medium text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
            >
              Konular
            </Link>
            <Link
              href="/egzersizler"
              className="hidden sm:flex px-3 h-9 items-center rounded-full text-[13px] font-medium text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
            >
              Egzersizler
            </Link>
            <ThemeToggle />
            <Link
              href="/"
              className="px-4 h-9 flex items-center rounded-full bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[13px] font-medium hover:opacity-85 transition-opacity"
            >
              Sohbete git
            </Link>
          </div>
        </div>
      </header>

      <div className="relative grain">
        <div className="hero-orb hero-orb-1 animate-drift !w-[320px] !h-[320px] !top-[-10%] !left-[55%]" />
        <div className="relative max-w-3xl w-full mx-auto px-6 pt-20 pb-12">
          <h1 className="display animate-hero-in text-[42px] sm:text-[56px] leading-[1.05] text-cbt-text dark:text-cbt-dark-text mb-5">
            {title}
          </h1>
          {intro && (
            <p
              className="animate-hero-in text-[18px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed max-w-2xl"
              style={{ animationDelay: "80ms" }}
            >
              {intro}
            </p>
          )}
        </div>
      </div>

      <main className="flex-1 max-w-3xl w-full mx-auto px-6 pb-24">
        <div className="space-y-14">{children}</div>
      </main>

      <SiteFooter />
    </div>
  );
}

export function Block({
  id,
  heading,
  children,
}: {
  id?: string;
  heading: string;
  children: React.ReactNode;
}) {
  return (
    <Reveal>
      <section id={id} className="scroll-mt-24">
        <h2 className="display text-[28px] sm:text-[32px] leading-tight text-cbt-text dark:text-cbt-dark-text mb-4">
          {heading}
        </h2>
        <div className="space-y-4 text-[16px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-[1.7]">
          {children}
        </div>
      </section>
    </Reveal>
  );
}
