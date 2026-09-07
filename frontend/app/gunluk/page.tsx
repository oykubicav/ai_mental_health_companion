"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";
import ThemeToggle from "@/components/ThemeToggle";
import SiteFooter from "@/components/SiteFooter";
import JournalDay from "@/components/journal/JournalDay";
import JournalStrip from "@/components/journal/JournalStrip";
import { listJournal } from "@/lib/api";
import { bugun, kisaTarih, tagLabel } from "@/lib/journal";
import { useAuth } from "@/hooks/AuthProvider";
import type { JournalEntry } from "@/lib/types";

export default function GunlukPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [entries, setEntries] = useState<Record<string, JournalEntry>>({});
  const [selected, setSelected] = useState(bugun());
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    try {
      const r = await listJournal(60);
      const map: Record<string, JournalEntry> = {};
      for (const e of r.entries) map[e.entry_date] = e;
      setEntries(map);
    } catch {
      setEntries({});
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (!authLoading) void load();
  }, [authLoading, load]);

  const kaydedildi = useCallback((entry: JournalEntry) => {
    setEntries((prev) => ({ ...prev, [entry.entry_date]: entry }));
  }, []);

  const silindi = useCallback((date: string) => {
    setEntries((prev) => {
      const kopya = { ...prev };
      delete kopya[date];
      return kopya;
    });
  }, []);

  const gecmis = Object.values(entries)
    .filter((e) => e.entry_date !== selected)
    .sort((a, b) => (a.entry_date < b.entry_date ? 1 : -1))
    .slice(0, 20);

  return (
    <div className="min-h-screen flex flex-col bg-cbt-bg dark:bg-cbt-dark-bg">
      <header className="sticky top-0 z-20 border-b border-cbt-border/50 dark:border-cbt-dark-border/50 bg-cbt-bg/80 dark:bg-cbt-dark-bg/80 backdrop-blur-xl">
        <div className="max-w-2xl mx-auto flex items-center justify-between px-6 py-4">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
          >
            <ArrowLeft size={15} strokeWidth={2} />
            Sohbete dön
          </Link>
          <div className="flex items-center gap-2">
            <Link
              href="/egzersizler"
              className="text-[13px] font-medium text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
            >
              Egzersizler
            </Link>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-2xl w-full mx-auto px-6 pt-12 pb-24">
        <h1 className="display text-[38px] sm:text-[48px] leading-[1.06] text-cbt-text dark:text-cbt-dark-text mb-4">
          Günlük
        </h1>
        <p className="text-[16px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed mb-10">
          Her gün doldurmak zorunda değilsin. Boş bıraktığın gün bir eksik
          değil; sonradan geri dönüp yazabilirsin. Burada seri, rozet ya da
          hatırlatma yok.
        </p>

        {authLoading || loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="animate-spin text-cbt-textMuted" size={20} />
          </div>
        ) : !isAuthenticated ? (
          <div className="p-7 rounded-[24px] bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border/60 dark:border-cbt-dark-border/60">
            <h2 className="display text-[24px] text-cbt-text dark:text-cbt-dark-text mb-3">
              Günlük için hesap gerekiyor.
            </h2>
            <p className="text-[15px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed mb-6">
              Üyeliksiz kullanımda saklanacak bir yer yok — yazdıkların
              tarayıcıyı kapattığında gider. Günlüğün anlamı günler arasında
              durması olduğu için burası hesaba bağlı.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/register"
                className="px-5 h-11 inline-flex items-center rounded-full bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[14px] font-medium hover:opacity-85 transition-opacity"
              >
                Hesap aç
              </Link>
              <Link
                href="/login"
                className="text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text"
              >
                Giriş yap
              </Link>
              <Link
                href="/egzersizler"
                className="text-[14px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text"
              >
                Üyeliksiz egzersizlere bak
              </Link>
            </div>
          </div>
        ) : (
          <>
            <div className="mb-12">
              <JournalStrip entries={entries} selected={selected} onSelect={setSelected} />
            </div>

            <JournalDay
              key={selected}
              date={selected}
              entry={entries[selected] ?? null}
              onSaved={kaydedildi}
              onDeleted={silindi}
              onNavigate={setSelected}
            />

            {gecmis.length > 0 && (
              <section className="mt-16 pt-8 border-t border-cbt-border/60 dark:border-cbt-dark-border/60">
                <h2 className="text-[12px] font-medium uppercase tracking-wide text-cbt-textMuted dark:text-cbt-dark-textMuted mb-5">
                  Geriye dönüp bak
                </h2>
                <ul className="space-y-3">
                  {gecmis.map((e) => (
                    <li key={e.entry_date}>
                      <button
                        onClick={() => setSelected(e.entry_date)}
                        className="w-full text-left p-5 rounded-2xl bg-cbt-surface dark:bg-cbt-dark-surface border border-cbt-border/60 dark:border-cbt-dark-border/60 hover:border-cbt-borderStrong dark:hover:border-cbt-dark-borderStrong transition-colors"
                      >
                        <div className="display text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted mb-1.5">
                          {kisaTarih(e.entry_date)}
                        </div>
                        {e.did && (
                          <p className="text-[14px] text-cbt-text dark:text-cbt-dark-text leading-relaxed line-clamp-2">
                            {e.did}
                          </p>
                        )}
                        {!e.did && e.thoughts && (
                          <p className="text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed line-clamp-2">
                            {e.thoughts}
                          </p>
                        )}
                        {e.tags.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {e.tags.map((t) => (
                              <span
                                key={t}
                                className="text-[11px] px-2 py-0.5 rounded-full bg-cbt-surfaceMuted dark:bg-cbt-dark-surfaceMuted text-cbt-textSecondary dark:text-cbt-dark-textSecondary"
                              >
                                {tagLabel(t)}
                              </span>
                            ))}
                          </div>
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <p className="mt-10 text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted leading-relaxed">
              Günlüğün yapay zekâya gönderilmiyor: Neva sohbette buradakileri
              okumuyor, bunlardan çıkarım yapmıyor. Sen silene kadar durur, her
              günü tek tek silebilirsin.
            </p>
          </>
        )}
      </main>

      <SiteFooter />
    </div>
  );
}
