"use client";

import { ArrowRight, ArrowUpRight } from "lucide-react";
import ThemeToggle from "./ThemeToggle";
import SiteFooter from "./SiteFooter";
import Reveal from "./landing/Reveal";
import PipelineDemo from "./landing/PipelineDemo";
import TopicMosaic from "./landing/TopicMosaic";

export default function Landing({ onStart }: { onStart: () => void }) {
  return (
    <div className="relative min-h-screen flex flex-col overflow-x-clip">
      <header className="sticky top-0 z-20 border-b border-cbt-border/50 dark:border-cbt-dark-border/50 bg-cbt-bg/80 dark:bg-cbt-dark-bg/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-6 py-4">
          <span className="display text-[22px] text-cbt-text dark:text-cbt-dark-text">
            Neva
          </span>
          <nav className="flex items-center gap-1 sm:gap-2">
            <a
              href="/cards"
              className="px-3 h-9 flex items-center rounded-full text-[13px] font-medium text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
            >
              Konular
            </a>
            <a
              href="/hakkinda"
              className="hidden sm:flex px-3 h-9 items-center rounded-full text-[13px] font-medium text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
            >
              Hakkında
            </a>
            <ThemeToggle />
            <button
              onClick={onStart}
              className="ml-1 px-4 h-9 flex items-center rounded-full bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[13px] font-medium hover:opacity-85 transition-opacity"
            >
              Başla
            </button>
          </nav>
        </div>
      </header>

      <main className="flex-1">
        {/* Giriş */}
        <section className="relative grain">
          <div className="hero-orb hero-orb-1 animate-drift" />
          <div className="hero-orb hero-orb-2 animate-drift-alt" />

          <div className="relative max-w-6xl mx-auto px-6 pt-16 sm:pt-24 pb-20 sm:pb-28 grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
            <div className="lg:col-span-7">
              <p className="animate-hero-in text-[13px] font-medium tracking-wide text-cbt-accent dark:text-cbt-dark-accent mb-5">
                Türkçe · Bilişsel davranışçı terapi temelli · Ücretsiz
              </p>
              <h1
                className="display animate-hero-in text-[46px] sm:text-[64px] lg:text-[72px] leading-[1.02] tracking-[-0.015em] text-cbt-text dark:text-cbt-dark-text mb-7"
                style={{ animationDelay: "60ms" }}
              >
                Aklından geçeni yaz.
                <br />
                <span className="text-cbt-textSecondary dark:text-cbt-dark-textSecondary">
                  Gerisine birlikte bakalım.
                </span>
              </h1>
              <p
                className="animate-hero-in text-[17px] sm:text-[19px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed max-w-xl mb-9"
                style={{ animationDelay: "120ms" }}
              >
                Kaygı, uykusuz geceler, kendine karşı sertlik ya da zor bir dönem.
                Neva ne hissettiğini yargılamadan dinler, düşünce örüntülerini
                fark etmene yardım eder ve bugün için küçük bir adım önerir.
              </p>

              <div
                className="animate-hero-in flex flex-col sm:flex-row items-start sm:items-center gap-3 sm:gap-5 mb-6"
                style={{ animationDelay: "180ms" }}
              >
                <button
                  onClick={onStart}
                  className="inline-flex items-center gap-2 px-7 min-h-[52px] rounded-full bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[15px] font-medium hover:opacity-85 transition-all active:scale-[0.98]"
                >
                  Konuşmaya başla
                  <ArrowRight size={16} strokeWidth={2} />
                </button>
                <a
                  href="/cards"
                  className="inline-flex items-center gap-1.5 text-[15px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
                >
                  Önce konulara göz at
                  <ArrowUpRight size={15} strokeWidth={2} />
                </a>
              </div>

              <p
                className="animate-hero-in text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted"
                style={{ animationDelay: "240ms" }}
              >
                Üyelik gerektirmez. Üyeliksiz sohbetler bir saat sonra silinir.
              </p>
            </div>

            <div className="lg:col-span-5 animate-hero-in" style={{ animationDelay: "200ms" }}>
              <PipelineDemo />
            </div>
          </div>
        </section>

        {/* Üç adım */}
        <section className="max-w-6xl mx-auto px-6 py-20 sm:py-28">
          <Reveal className="max-w-2xl mb-14">
            <h2 className="display text-[36px] sm:text-[46px] leading-[1.08] text-cbt-text dark:text-cbt-dark-text mb-4">
              Bir sohbet nasıl ilerler
            </h2>
            <p className="text-[16px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed">
              Terapi seansı değil, ders de değil. Yirmi dakikalık, sonu belli
              bir konuşma. Neva uzatmaz; iyi bir yerde bitirmeyi teklif eder.
            </p>
          </Reveal>

          <ol className="grid grid-cols-1 md:grid-cols-3 gap-x-10 gap-y-12">
            <StepItem
              n="01"
              title="Anlat"
              body="Düzgün cümle kurman gerekmiyor. Aklından geçen neyse o; yarım bırakılmış bir cümle bile yeter."
            />
            <StepItem
              n="02"
              title="Fark et"
              body="Neva o düşüncenin içindeki örüntüyü isimlendirir: felaketleştirme, zihin okuma, hep-hiç. Adı olunca küçülür."
              delay={90}
            />
            <StepItem
              n="03"
              title="Küçük bir adım at"
              body="Bir nefes çalışması, bir düşünce kaydı ya da yarın için tek bir plan. Büyük değişim istemez; bugün için bir adım."
              delay={180}
            />
          </ol>
        </section>

        {/* Konular */}
        <section className="border-y border-cbt-border/60 dark:border-cbt-dark-border/60 bg-cbt-surfaceMuted/60 dark:bg-cbt-dark-surface/40">
          <div className="max-w-6xl mx-auto px-6 py-20 sm:py-28">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16">
              <Reveal className="lg:col-span-4">
                <h2 className="display text-[36px] sm:text-[46px] leading-[1.08] text-cbt-text dark:text-cbt-dark-text mb-4">
                  Ne konuşabilirsin
                </h2>
                <p className="text-[16px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed mb-8">
                  Neva her şeyi bilmez; on sekiz konuyu iyi bilir. Konuşman
                  bunların dışına çıkarsa bunu açıkça söyler, uydurmaz.
                </p>
                <dl className="grid grid-cols-2 gap-x-6 gap-y-5">
                  <Stat n="18" label="konu modülü" />
                  <Stat n="180" label="bilgi kartı" />
                  <Stat n="19" label="güvenlik kartı" />
                  <Stat n="171" label="kaynak" />
                </dl>
              </Reveal>
              <div className="lg:col-span-8">
                <TopicMosaic />
              </div>
            </div>
          </div>
        </section>

        {/* Yapmadıkları */}
        <section className="max-w-6xl mx-auto px-6 py-20 sm:py-28">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-16">
            <Reveal className="lg:col-span-5">
              <h2 className="display text-[36px] sm:text-[46px] leading-[1.08] text-cbt-text dark:text-cbt-dark-text mb-4">
                Neva&apos;nın yapmadıkları
              </h2>
              <p className="text-[16px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed">
                Bir uygulamanın ne yapabildiğinden çok ne yapmayacağı güven
                verir. Bunlar tasarım kararı, küçük yazı değil.
              </p>
            </Reveal>
            <ul className="lg:col-span-7 divide-y divide-cbt-border dark:divide-cbt-dark-border border-y border-cbt-border dark:border-cbt-dark-border">
              <NotItem
                title="Tanı koymaz."
                body="Kaygı, depresyon, panik gibi kelimeleri konuşmanın diliyle kullanır; senin hakkında bir hüküm olarak kullanmaz."
              />
              <NotItem
                title="İnsan gibi davranmaz."
                body="Bir yapay zekâ olduğunu her yerde açıkça söyler. Terapist ya da arkadaş rolü oynamaz."
                delay={60}
              />
              <NotItem
                title="Uydurmaz."
                body="Cevaplar klinik psikolog onaylı kartlara dayanır. Hangi kartı kullandığını her cevabın altında gösterir."
                delay={120}
              />
              <NotItem
                title="Seni tutmaya çalışmaz."
                body="Bildirim, seri, rozet yok. Konuşma iyi bir yere geldiğinde bitirmeyi teklif eder."
                delay={180}
              />
              <NotItem
                title="Kriz anında rol yapmaz."
                body="Kendine zarar verme işareti gördüğünde teknik anlatmayı bırakır; gerçek bir insana ulaşmana yardım eder."
                delay={240}
              />
            </ul>
          </div>
        </section>

        {/* Güven */}
        <section className="max-w-6xl mx-auto px-6 pb-20 sm:pb-28">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-10 md:gap-8">
            <TrustItem
              title="Gizlilik"
              body="Üyeliksiz kullanırsan sohbetler bir saat sonra silinir. Hesap açarsan sen silene kadar durur; tek tuşla silersin. Verilerin nerede işlendiğini saklamıyoruz."
              href="/gizlilik"
              link="Gizlilik ve veriler"
            />
            <TrustItem
              title="Bilimsel temel"
              body="NICE, APA gibi klinik rehberler ve hakemli araştırmalardan sentezlendi. Her kartın kaynağı görünür."
              href="/kaynaklar"
              link="Kaynak listesi"
              delay={90}
            />
            <TrustItem
              title="İnsan onayı"
              body="Bütün içerik 4 Eylül 2026'da bir klinik psikolog tarafından tek tek okundu. Bir kart değişirse onayı düşer, yeniden okunur."
              href="/hakkinda#sinirlar"
              link="Sınırlarımız"
              delay={180}
            />
          </div>
        </section>

        {/* Kapanış */}
        <section className="relative overflow-hidden">
          <div className="hero-orb hero-orb-1 animate-drift-alt !left-auto !right-[10%] !top-[-20%]" />
          <Reveal className="relative max-w-6xl mx-auto px-6 py-24 sm:py-32 text-center">
            <h2 className="display text-[40px] sm:text-[56px] leading-[1.05] text-cbt-text dark:text-cbt-dark-text mb-4">
              Hazır olduğunda başla.
            </h2>
            <p className="text-[16px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary mb-9">
              Acele etmene gerek yok. Kapatıp sonra da gelebilirsin.
            </p>
            <button
              onClick={onStart}
              className="inline-flex items-center gap-2 px-8 min-h-[52px] rounded-full bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[15px] font-medium hover:opacity-85 transition-all active:scale-[0.98]"
            >
              Konuşmaya başla
              <ArrowRight size={16} strokeWidth={2} />
            </button>
          </Reveal>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}

function StepItem({
  n,
  title,
  body,
  delay = 0,
}: {
  n: string;
  title: string;
  body: string;
  delay?: number;
}) {
  return (
    <Reveal as="li" delay={delay} className="relative pt-6 border-t border-cbt-border dark:border-cbt-dark-border">
      <span className="display text-[44px] leading-none text-cbt-accent dark:text-cbt-dark-accent">
        {n}
      </span>
      <h3 className="mt-4 mb-2 text-[19px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text">
        {title}
      </h3>
      <p className="text-[15px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed">
        {body}
      </p>
    </Reveal>
  );
}

function Stat({ n, label }: { n: string; label: string }) {
  return (
    <div>
      <dt className="display text-[36px] leading-none text-cbt-text dark:text-cbt-dark-text tabular-nums">
        {n}
      </dt>
      <dd className="mt-1.5 text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted">{label}</dd>
    </div>
  );
}

function NotItem({ title, body, delay = 0 }: { title: string; body: string; delay?: number }) {
  return (
    <Reveal as="li" delay={delay} className="group py-6 grid grid-cols-[auto_1fr] gap-4 sm:gap-6">
      <svg
        aria-hidden
        viewBox="0 0 20 20"
        className="mt-1.5 w-5 h-5 text-cbt-textMuted dark:text-cbt-dark-textMuted group-hover:text-cbt-danger dark:group-hover:text-cbt-dark-danger transition-colors"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      >
        <circle cx="10" cy="10" r="8.5" />
        <path d="M4 16 16 4" />
      </svg>
      <div>
        <h3 className="display text-[24px] sm:text-[26px] leading-tight text-cbt-text dark:text-cbt-dark-text mb-1.5">
          {title}
        </h3>
        <p className="text-[15px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed max-w-lg">
          {body}
        </p>
      </div>
    </Reveal>
  );
}

function TrustItem({
  title,
  body,
  href,
  link,
  delay = 0,
}: {
  title: string;
  body: string;
  href: string;
  link: string;
  delay?: number;
}) {
  return (
    <Reveal delay={delay}>
      <h3 className="text-[13px] font-medium uppercase tracking-wide text-cbt-textMuted dark:text-cbt-dark-textMuted mb-3">
        {title}
      </h3>
      <p className="text-[15px] text-cbt-text dark:text-cbt-dark-text leading-relaxed mb-4">{body}</p>
      <a
        href={href}
        className="inline-flex items-center gap-1 text-[14px] text-cbt-accent dark:text-cbt-dark-accent hover:underline underline-offset-4"
      >
        {link}
        <ArrowUpRight size={14} strokeWidth={2} />
      </a>
    </Reveal>
  );
}
