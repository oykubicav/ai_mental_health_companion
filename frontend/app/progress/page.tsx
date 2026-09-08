"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, Plus } from "lucide-react";
import { getSessionId, setSessionId as saveSessionId } from "@/lib/session";
import { hasConsent, POLICY_VERSION } from "@/lib/consent";
import { postConsent } from "@/lib/api";
import ConsentModal from "@/components/ConsentModal";
import AssessmentTrend from "@/components/AssessmentTrend";
import AssessmentModal from "@/components/AssessmentModal";
import type { AssessmentKind } from "@/lib/types";
import InsightsPanel from "@/components/InsightsPanel";
import { useAuth } from "@/hooks/AuthProvider";

export default function ProgressPage() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [needsConsent, setNeedsConsent] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [activeKind, setActiveKind] = useState<AssessmentKind>("phq9");
  const [showModal, setShowModal] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    setMounted(true);
    setSessionId(getSessionId());
  }, []);

  // Ölçüm bir oturuma yazılıyor ama ölçüm yapmak için sohbet etmiş olmak
  // gerekmiyor: cihazda oturum yoksa burada açılıyor. Eskiden oturumu
  // olmayan kullanıcıda düğme hiçbir şey yapmıyordu.
  async function olcumeBasla() {
    if (starting) return;
    if (sessionId) {
      setShowModal(true);
      return;
    }
    if (!hasConsent()) {
      setNeedsConsent(true);
      return;
    }
    setStarting(true);
    try {
      const res = await postConsent(POLICY_VERSION);
      saveSessionId(res.session_id);
      setSessionId(res.session_id);
      setShowModal(true);
    } catch {
      // Oturum açılamadı; onay ekranına düşür, oradan tekrar denenebilir.
      setNeedsConsent(true);
    } finally {
      setStarting(false);
    }
  }

  function handleConsentGranted() {
    setNeedsConsent(false);
    setSessionId(getSessionId());
    setShowModal(true);
  }

  if (!mounted) return null;

  if (needsConsent) {
    return <ConsentModal onGranted={handleConsentGranted} />;
  }

  return (
    <div className="min-h-screen bg-cbt-bg dark:bg-cbt-dark-bg">
      <header className="sticky top-0 z-30 border-b border-cbt-border/50 dark:border-cbt-dark-border/50 bg-cbt-bg/80 dark:bg-cbt-dark-bg/80 backdrop-blur-xl">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
          >
            <ArrowLeft size={15} strokeWidth={2} />
            Sohbete dön
          </Link>
          <span className="text-[15px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text">
            Gelişimim
          </span>
          <button
            onClick={olcumeBasla}
            disabled={starting}
            className="flex items-center gap-1 text-[13px] font-medium text-cbt-text dark:text-cbt-dark-text hover:opacity-70 disabled:opacity-50 transition-opacity"
          >
            <Plus size={15} strokeWidth={2} />
            {starting ? "Açılıyor…" : "Yeni ölçüm"}
          </button>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-6 pt-8">
        <div className="flex gap-1">
          <TabButton
            active={activeKind === "phq9"}
            onClick={() => setActiveKind("phq9")}
            label="Ruh hali"
          />
          <TabButton
            active={activeKind === "gad7"}
            onClick={() => setActiveKind("gad7")}
            label="Kaygı"
          />
        </div>
      </div>

      <main className="max-w-3xl mx-auto px-6 py-8">
        <div className="bg-cbt-surface dark:bg-cbt-dark-surface rounded-2xl border border-cbt-border/60 dark:border-cbt-dark-border/60 p-7">
          {isAuthenticated || sessionId ? (
            <AssessmentTrend
              key={`${activeKind}-${refreshKey}`}
              sessionId={isAuthenticated ? null : sessionId}
              kind={activeKind}
            />
          ) : (
            <div className="py-10 text-center">
              <p className="text-[15px] text-cbt-text dark:text-cbt-dark-text mb-2">
                Henüz bir ölçümün yok
              </p>
              <p className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary mb-6 max-w-sm mx-auto leading-relaxed">
                İlk ölçümünü yaparak başlangıç noktanı belirleyebilir, zaman
                içindeki değişimi buradan izleyebilirsin.
              </p>
              <button
                onClick={olcumeBasla}
                disabled={starting}
                className="inline-flex items-center justify-center px-6 h-11 rounded-xl bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[14px] font-medium hover:opacity-85 disabled:opacity-50 transition-opacity"
              >
                {starting ? "Açılıyor…" : "İlk ölçümünü yap"}
              </button>
            </div>
          )}
        </div>
        {!authLoading && (isAuthenticated ? (
          <section className="mt-8 bg-cbt-surface dark:bg-cbt-dark-surface rounded-2xl border border-cbt-border/60 dark:border-cbt-dark-border/60 p-7">
            <h2 className="text-[15px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text mb-1">
              Konuşmalarımızdan
            </h2>
            <p className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary mb-6 leading-relaxed">
              Sohbetlerde tekrar eden konular ve denediğin teknikler.
            </p>
            <InsightsPanel />
          </section>
        ) : (
          <section className="mt-8 rounded-2xl border border-dashed border-cbt-border dark:border-cbt-dark-border p-7">
            <h2 className="text-[15px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text mb-2">
              Konuşmalarımızdan
            </h2>
            <p className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed mb-5">
              Hesabın olursa sohbetlerde tekrar eden konuları ve hangi
              tekniklerin sende işe yaradığını burada biriktirebiliriz.
              Üyeliksiz kullanımda sohbetler bir saat sonra siliniyor, o yüzden
              biriktirecek bir şey kalmıyor.
            </p>
            <div className="flex items-center gap-3">
              <Link
                href="/register"
                className="inline-flex items-center justify-center px-5 h-10 rounded-xl bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[14px] font-medium hover:opacity-85 transition-opacity"
              >
                Hesap oluştur
              </Link>
              <Link
                href="/login"
                className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
              >
                Zaten hesabım var
              </Link>
            </div>
          </section>
        ))}

        <p className="mt-6 text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted leading-relaxed text-center max-w-md mx-auto">
          Bu ölçekler tanı koymaz; yaygın kullanılan tarama araçlarıdır ve
          yalnızca kendi değişimini takip etmen içindir. Zorlandığını
          hissediyorsan bir uzmanla görüşmek en iyi adım olur.
        </p>
      </main>

      {showModal && sessionId && (
        <AssessmentModal
          sessionId={sessionId}
          kind={activeKind}
          onClose={() => setShowModal(false)}
          onSubmit={() => setRefreshKey((k) => k + 1)}
        />
      )}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={
        active
          ? "px-4 h-9 rounded-full text-[13px] font-medium bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg transition-all"
          : "px-4 h-9 rounded-full text-[13px] font-medium text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-text dark:hover:text-cbt-dark-text transition-all"
      }
    >
      {label}
    </button>
  );
}
