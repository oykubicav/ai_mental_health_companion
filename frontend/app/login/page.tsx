"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/AuthProvider";
import { postResendVerify } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [needsVerify, setNeedsVerify] = useState(false);
  const [resendMessage, setResendMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/");
    } catch (err: any) {
      if (err?.status === 403 || err?.message?.includes("doğrula")) {
        setError(
          "E-posta adresin henüz doğrulanmamış. Kayıt olurken gönderdiğimiz bağlantıya tıkla — gerekirse spam klasörüne de bak."
        );
        setNeedsVerify(true);
      } else {
        setError(err?.message || "Giriş yapılamadı. Bilgilerini kontrol edip tekrar dene.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-cbt-bg dark:bg-cbt-dark-bg">
      <header className="px-6 py-5">
        <Link
          href="/"
          className="text-[17px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text"
        >
          Neva
        </Link>
      </header>

      <main className="flex-1 flex items-center justify-center px-6 pb-24">
        <div className="w-full max-w-sm">
          <h1 className="text-[28px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text mb-2 text-center">
            Tekrar hoş geldin
          </h1>
          <p className="text-[14px] text-cbt-textMuted dark:text-cbt-dark-textMuted text-center mb-10">
            Hesabınla devam et
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[13px] font-medium text-cbt-text dark:text-cbt-dark-text mb-1.5">
                E-posta
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 h-12 rounded-xl border border-cbt-border dark:border-cbt-dark-border bg-cbt-surface dark:bg-cbt-dark-surface text-[15px] text-cbt-text dark:text-cbt-dark-text placeholder:text-cbt-textMuted focus:outline-none focus:border-cbt-borderStrong dark:focus:border-cbt-dark-borderStrong transition-colors"
                placeholder="ornek@eposta.com"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-[13px] font-medium text-cbt-text dark:text-cbt-dark-text">
                  Şifre
                </label>
                <Link
                  href="/forgot-password"
                  className="text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
                >
                  Şifreni mi unuttun?
                </Link>
              </div>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 h-12 rounded-xl border border-cbt-border dark:border-cbt-dark-border bg-cbt-surface dark:bg-cbt-dark-surface text-[15px] text-cbt-text dark:text-cbt-dark-text focus:outline-none focus:border-cbt-borderStrong dark:focus:border-cbt-dark-borderStrong transition-colors"
              />
            </div>

            {error && (
              <p className="text-[13px] text-cbt-danger dark:text-cbt-dark-danger leading-relaxed">
                {error}
              </p>
            )}

            {needsVerify && (
              <button
                type="button"
                onClick={async () => {
                  await postResendVerify(email);
                  setResendMessage(
                    "Doğrulama bağlantısı yeniden gönderildi. E-posta kutunu kontrol et."
                  );
                  setNeedsVerify(false);
                }}
                className="text-[13px] font-medium text-cbt-text dark:text-cbt-dark-text underline underline-offset-2"
              >
                Doğrulama bağlantısını yeniden gönder
              </button>
            )}
            {resendMessage && (
              <p className="text-[13px] text-cbt-success dark:text-cbt-dark-success">
                {resendMessage}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full h-12 rounded-xl bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[15px] font-medium hover:opacity-85 transition-opacity disabled:opacity-40"
            >
              {submitting ? "Giriş yapılıyor…" : "Giriş yap"}
            </button>
          </form>

          <div className="mt-8 text-center space-y-3">
            <p className="text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted">
              Hesabın yok mu?{" "}
              <Link
                href="/register"
                className="font-medium text-cbt-text dark:text-cbt-dark-text hover:underline underline-offset-2"
              >
                Kayıt ol
              </Link>
            </p>
            <p className="text-[13px]">
              <Link
                href="/"
                className="text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-text dark:hover:text-cbt-dark-text transition-colors"
              >
                Üyeliksiz devam et
              </Link>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
