"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Loader2 } from "lucide-react";
import { useAuth } from "@/hooks/AuthProvider";
import { FOCUS_OPTIONS } from "@/lib/profile";
import AccountSecurity from "@/components/AccountSecurity";

export default function AccountPage() {
  const { user, loading, updateProfile, deleteAccount } = useAuth();
  const router = useRouter();

  const [ad, setAd] = useState("");
  const [konular, setKonular] = useState<string[]>([]);
  const [kaydediliyor, setKaydediliyor] = useState(false);
  const [kaydedildi, setKaydedildi] = useState(false);
  const [silmeOnayi, setSilmeOnayi] = useState(false);

  // Sunucudan gelen değerleri forma bir kez doldur.
  useEffect(() => {
    if (!user) return;
    setAd(user.display_name ?? "");
    setKonular(user.focus_topics ?? []);
  }, [user?.id]);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-cbt-bg dark:bg-cbt-dark-bg">
        <Loader2 className="animate-spin text-cbt-textMuted" size={20} />
      </div>
    );
  }

  const konuDegistir = (id: string) => {
    setKaydedildi(false);
    setKonular((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const profilKaydet = async () => {
    setKaydediliyor(true);
    try {
      await updateProfile({ display_name: ad.trim(), focus_topics: konular });
      setKaydedildi(true);
    } finally {
      setKaydediliyor(false);
    }
  };

  const uyelikTarihi = new Date(user.created_at).toLocaleDateString("tr-TR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="min-h-screen bg-cbt-bg dark:bg-cbt-dark-bg">
      <header className="sticky top-0 z-30 border-b border-cbt-border/50 dark:border-cbt-dark-border/50 bg-cbt-bg/80 dark:bg-cbt-dark-bg/80 backdrop-blur-xl">
        <div className="max-w-2xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
          >
            <ArrowLeft size={15} strokeWidth={2} />
            Sohbete dön
          </Link>
          <span className="text-[15px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text">
            Hesabım
          </span>
          <span className="w-20" />
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-8 space-y-6">
        <Card>
          <h2 className="text-[15px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text mb-5">
            Hesap
          </h2>
          <Row label="E-posta">
            <span className="text-[14px] text-cbt-text dark:text-cbt-dark-text">
              {user.email}
            </span>
            {!user.email_verified && (
              <span className="ml-2 text-[11px] px-2 py-0.5 rounded-full bg-cbt-warningSoft dark:bg-cbt-dark-warningSoft text-cbt-warning dark:text-cbt-dark-warning">
                doğrulanmadı
              </span>
            )}
          </Row>
          <Row label="Üyelik">
            <span className="text-[14px] text-cbt-text dark:text-cbt-dark-text">
              {uyelikTarihi}
            </span>
          </Row>
        </Card>

        <Card>
          <h2 className="text-[15px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text mb-1">
            Profil
          </h2>
          <p className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary mb-5 leading-relaxed">
            Neva sana nasıl hitap etsin ve hangi konularla ilgileniyorsun.
            İstediğin zaman değiştirebilirsin.
          </p>

          <label className="block text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted mb-2">
            Adın
          </label>
          <input
            value={ad}
            onChange={(e) => {
              setAd(e.target.value.slice(0, 60));
              setKaydedildi(false);
            }}
            placeholder="Boş bırakabilirsin"
            className="w-full max-w-sm px-4 h-11 rounded-xl border border-cbt-border dark:border-cbt-dark-border bg-cbt-bg dark:bg-cbt-dark-bg text-[14px] text-cbt-text dark:text-cbt-dark-text placeholder:text-cbt-textMuted focus:outline-none focus:border-cbt-borderStrong dark:focus:border-cbt-dark-borderStrong transition-colors"
          />

          <label className="block text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted mt-6 mb-3">
            İlgilendiğin konular
          </label>
          <div className="flex flex-wrap gap-2">
            {FOCUS_OPTIONS.map((o) => {
              const secili = konular.includes(o.id);
              return (
                <button
                  key={o.id}
                  onClick={() => konuDegistir(o.id)}
                  className={
                    secili
                      ? "px-3.5 py-2 rounded-full text-[13px] font-medium bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg transition-all active:scale-[0.98]"
                      : "px-3.5 py-2 rounded-full text-[13px] bg-cbt-bg dark:bg-cbt-dark-bg border border-cbt-border dark:border-cbt-dark-border text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:border-cbt-borderStrong dark:hover:border-cbt-dark-borderStrong transition-all active:scale-[0.98]"
                  }
                >
                  {o.label}
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-3 mt-6">
            <button
              onClick={() => void profilKaydet()}
              disabled={kaydediliyor}
              className="px-5 h-11 rounded-xl bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[14px] font-medium hover:opacity-85 disabled:opacity-40 transition-opacity"
            >
              {kaydediliyor ? "Kaydediliyor…" : "Kaydet"}
            </button>
            {kaydedildi && (
              <span className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary">
                Kaydedildi.
              </span>
            )}
          </div>
        </Card>

        <Card>
          <h2 className="text-[15px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text mb-5">
            Güvenlik
          </h2>
          <AccountSecurity />
        </Card>

        <Card>
          <h2 className="text-[15px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text mb-1">
            Verilerim
          </h2>
          <p className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed mb-5">
            Sohbetlerini tek tek silmek için sohbet listesindeki çöp kutusu
            simgesini kullanabilirsin. Konuşmalardan çıkarılan notları{" "}
            <Link
              href="/progress"
              className="underline underline-offset-2 hover:text-cbt-text dark:hover:text-cbt-dark-text"
            >
              Gelişimim
            </Link>{" "}
            sayfasından silebilirsin. Nelerin saklandığını{" "}
            <Link
              href="/gizlilik"
              className="underline underline-offset-2 hover:text-cbt-text dark:hover:text-cbt-dark-text"
            >
              gizlilik sayfasında
            </Link>{" "}
            anlattık.
          </p>

          {silmeOnayi ? (
            <div className="rounded-xl border border-cbt-danger/30 p-4">
              <p className="text-[13px] text-cbt-text dark:text-cbt-dark-text leading-relaxed mb-4">
                Hesabın, bütün sohbetlerin, ölçümlerin ve çıkarılan notların
                kalıcı olarak silinecek. Bu işlem geri alınamaz.
              </p>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => void deleteAccount()}
                  className="px-4 h-10 rounded-lg bg-cbt-danger text-white text-[13px] font-medium hover:opacity-85 transition-opacity"
                >
                  Hesabımı kalıcı olarak sil
                </button>
                <button
                  onClick={() => setSilmeOnayi(false)}
                  className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary"
                >
                  Vazgeç
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setSilmeOnayi(true)}
              className="text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-danger dark:hover:text-cbt-dark-danger transition-colors"
            >
              Hesabımı sil
            </button>
          )}
        </Card>
      </main>
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <section className="bg-cbt-surface dark:bg-cbt-dark-surface rounded-2xl border border-cbt-border/60 dark:border-cbt-dark-border/60 p-7">
      {children}
    </section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-2.5 border-b border-cbt-border/40 dark:border-cbt-dark-border/40 last:border-0">
      <span className="text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted shrink-0">
        {label}
      </span>
      <span className="text-right">{children}</span>
    </div>
  );
}