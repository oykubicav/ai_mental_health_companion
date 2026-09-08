"use client";

import { useEffect, useState } from "react";
import { hasConsent, grantConsent, POLICY_VERSION } from "@/lib/consent";
import { getSessionId, setSessionId } from "@/lib/session";
import { postConsent } from "@/lib/api";

export default function ConsentModal({
  onGranted,
}: {
  onGranted?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (hasConsent()) {
      onGranted?.();
    } else {
      setOpen(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleAccept() {
    setBusy(true);
    setError(null);
    try {
      const existing = getSessionId() || undefined;
      const res = await postConsent(POLICY_VERSION, existing);
      setSessionId(res.session_id);
      grantConsent();
      setOpen(false);
      onGranted?.();
    } catch (e: any) {
      console.error("consent backend call failed", e);
      setError(
        "Sunucuya şu an ulaşılamıyor. Onayın cihazında kaydedildi, devam edebilirsin."
      );
      grantConsent();
      setSessionId("");
      setTimeout(() => {
        setOpen(false);
        onGranted?.();
      }, 1500);
    } finally {
      setBusy(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 dark:bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
      <div className="w-full max-w-md rounded-3xl bg-cbt-surface dark:bg-cbt-dark-surface shadow-modal p-7 sm:p-8 animate-modal-in border border-cbt-border/40 dark:border-cbt-dark-border/40">
        <h2 className="text-[22px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text mb-6">
          Başlamadan önce
        </h2>

        <div className="space-y-5">
          <Item title="Neva bir terapist değildir">
            Tanı koymaz, ilaç önermez, klinik değerlendirme yapmaz. Terapinin
            ya da tıbbi yardımın yerini tutmaz.
          </Item>

          <Item title="Acil durumlarda 112">
            Kendine ya da bir başkasına zarar verme düşüncen varsa, tıbbi bir
            aciliyet söz konusuysa veya güvende değilsen 112'yi ara ya da en
            yakın acil servise başvur.
          </Item>

          <Item title="Verilerin sende kalır">
            Yazdıkların kalıcı olarak saklanmaz. Sohbetini istediğin an
            silebilirsin.
          </Item>
        </div>

        <p className="text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted mt-6">
          Devam ederek bunları okuduğunu ve kabul ettiğini onaylamış olursun.
        </p>

        {error && (
          <p className="mt-4 text-[13px] text-cbt-warning dark:text-cbt-dark-warning leading-relaxed">
            {error}
          </p>
        )}

        <button
          className="mt-6 w-full h-12 rounded-xl bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg font-medium text-[15px] hover:opacity-85 disabled:opacity-40 transition-opacity active:scale-[0.98]"
          onClick={handleAccept}
          disabled={busy}
        >
          {busy ? "Bir saniye…" : "Anladım, devam et"}
        </button>
      </div>
    </div>
  );
}

function Item({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="text-[14px] font-semibold text-cbt-text dark:text-cbt-dark-text mb-1">
        {title}
      </div>
      <p className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed">
        {children}
      </p>
    </div>
  );
}
