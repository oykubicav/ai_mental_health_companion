"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/AuthProvider";
import { CheckCircle } from "lucide-react";

export default function RegisterPage() {
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await register(email, password);
      setDone(true);
    } catch (err: any) {
      setError(err?.message || "Kayıt tamamlanamadı. Lütfen tekrar dene.");
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
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
          <div className="max-w-sm text-center">
            <CheckCircle
              size={44}
              strokeWidth={1.5}
              className="mx-auto mb-6 text-cbt-success dark:text-cbt-dark-success"
            />
            <h2 className="text-[24px] font-semibold tracking-tight text-cbt-text dark:text-cbt-dark-text mb-3">
              E-postanı kontrol et
            </h2>
            <p className="text-[14px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary leading-relaxed mb-2">
              <span className="font-medium text-cbt-text dark:text-cbt-dark-text">{email}</span>{" "}
              adresine bir doğrulama bağlantısı gönderdik. Bağlantıya
              tıkladıktan sonra giriş yapabilirsin.
            </p>
            <p className="text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted mb-8">
              E-posta görünmüyorsa spam klasörüne de bak.
            </p>
            <Link
              href="/login"
              className="inline-flex items-center justify-center px-7 h-12 rounded-xl bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[15px] font-medium hover:opacity-85 transition-opacity"
            >
              Doğruladım, giriş yap
            </Link>
          </div>
        </main>
      </div>
    );
  }

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
            Hesap oluştur
          </h1>
          <p className="text-[14px] text-cbt-textMuted dark:text-cbt-dark-textMuted text-center mb-10">
            Gelişimini kaydet, kaldığın yerden devam et
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
              <label className="block text-[13px] font-medium text-cbt-text dark:text-cbt-dark-text mb-1.5">
                Şifre
              </label>
              <input
                type="password"
                required
                minLength={8}
                maxLength={128}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 h-12 rounded-xl border border-cbt-border dark:border-cbt-dark-border bg-cbt-surface dark:bg-cbt-dark-surface text-[15px] text-cbt-text dark:text-cbt-dark-text focus:outline-none focus:border-cbt-borderStrong dark:focus:border-cbt-dark-borderStrong transition-colors"
              />
              <p className="mt-1.5 text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted">
                En az 8 karakter
              </p>
            </div>

            {error && (
              <p className="text-[13px] text-cbt-danger dark:text-cbt-dark-danger leading-relaxed">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full h-12 rounded-xl bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[15px] font-medium hover:opacity-85 transition-opacity disabled:opacity-40"
            >
              {submitting ? "Hesap oluşturuluyor…" : "Devam et"}
            </button>

            <p className="text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted leading-relaxed text-center">
              Kayıt olarak KVKK aydınlatma metnini kabul etmiş olursun.
              Hesabını ve verilerini istediğin an silebilirsin.
            </p>
          </form>

          <p className="mt-8 text-center text-[13px] text-cbt-textMuted dark:text-cbt-dark-textMuted">
            Zaten hesabın var mı?{" "}
            <Link
              href="/login"
              className="font-medium text-cbt-text dark:text-cbt-dark-text hover:underline underline-offset-2"
            >
              Giriş yap
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
