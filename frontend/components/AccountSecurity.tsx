"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, LogOut, Monitor } from "lucide-react";
import { getMyDevices, revokeDevice, changePassword } from "@/lib/api";
import { setAccessToken } from "@/lib/auth";
import { deviceLabel } from "@/lib/devices";
import { formatRelativeTime } from "@/lib/time";
import { useAuth } from "@/hooks/AuthProvider";
import type { DeviceView } from "@/lib/types";

export default function AccountSecurity() {
  const { logoutAll } = useAuth();
  const [devices, setDevices] = useState<DeviceView[]>([]);
  const [loading, setLoading] = useState(true);

  const [mevcut, setMevcut] = useState("");
  const [yeni, setYeni] = useState("");
  const [pwHata, setPwHata] = useState("");
  const [pwOk, setPwOk] = useState(false);
  const [kaydediliyor, setKaydediliyor] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setDevices(await getMyDevices());
    } catch {
      setDevices([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const sifreDegistir = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwHata("");
    setPwOk(false);
    setKaydediliyor(true);
    try {
      const r = await changePassword(mevcut, yeni);
      // Sunucu diğer oturumları kapattı ve bu cihaza yeni bir token verdi.
      setAccessToken(r.access_token);
      setMevcut("");
      setYeni("");
      setPwOk(true);
      await load();
    } catch (err: any) {
      setPwHata(err?.message || "Şifre değiştirilemedi.");
    } finally {
      setKaydediliyor(false);
    }
  };

  const cihazKapat = async (id: string) => {
    await revokeDevice(id).catch(() => {});
    await load();
  };

  return (
    <div className="space-y-10">
      <section>
        <h3 className="text-[14px] font-semibold text-cbt-text dark:text-cbt-dark-text mb-1">
          Şifre
        </h3>
        <p className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary mb-4 leading-relaxed">
          Şifreni değiştirdiğinde bu cihaz dışındaki tüm oturumlar kapanır.
        </p>

        <form onSubmit={sifreDegistir} className="space-y-3 max-w-sm">
          <input
            type="password"
            value={mevcut}
            onChange={(e) => setMevcut(e.target.value)}
            placeholder="Mevcut şifren"
            autoComplete="current-password"
            className="w-full px-4 h-11 rounded-xl border border-cbt-border dark:border-cbt-dark-border bg-cbt-bg dark:bg-cbt-dark-bg text-[14px] text-cbt-text dark:text-cbt-dark-text placeholder:text-cbt-textMuted focus:outline-none focus:border-cbt-borderStrong dark:focus:border-cbt-dark-borderStrong transition-colors"
          />
          <input
            type="password"
            value={yeni}
            onChange={(e) => setYeni(e.target.value)}
            placeholder="Yeni şifren (en az 8 karakter)"
            autoComplete="new-password"
            className="w-full px-4 h-11 rounded-xl border border-cbt-border dark:border-cbt-dark-border bg-cbt-bg dark:bg-cbt-dark-bg text-[14px] text-cbt-text dark:text-cbt-dark-text placeholder:text-cbt-textMuted focus:outline-none focus:border-cbt-borderStrong dark:focus:border-cbt-dark-borderStrong transition-colors"
          />

          {pwHata && (
            <p className="text-[13px] text-cbt-danger dark:text-cbt-dark-danger">
              {pwHata}
            </p>
          )}
          {pwOk && (
            <p className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary">
              Şifren güncellendi.
            </p>
          )}

          <button
            type="submit"
            disabled={kaydediliyor || !mevcut || yeni.length < 8}
            className="px-5 h-11 rounded-xl bg-cbt-text dark:bg-cbt-dark-text text-cbt-bg dark:text-cbt-dark-bg text-[14px] font-medium hover:opacity-85 disabled:opacity-40 transition-opacity"
          >
            {kaydediliyor ? "Kaydediliyor…" : "Şifreyi değiştir"}
          </button>
        </form>
      </section>

      <section>
        <h3 className="text-[14px] font-semibold text-cbt-text dark:text-cbt-dark-text mb-1">
          Açık oturumlar
        </h3>
        <p className="text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary mb-4 leading-relaxed">
          Hesabına giriş yapılmış cihazlar. Tanımadığın bir şey görürsen
          kapat ve şifreni değiştir.
        </p>

        {loading ? (
          <div className="py-6 flex justify-center">
            <Loader2 className="animate-spin text-cbt-textMuted" size={18} />
          </div>
        ) : (
          <div className="space-y-1">
            {devices.map((d) => (
              <div
                key={d.id}
                className="flex items-center gap-3 py-3 border-b border-cbt-border/40 dark:border-cbt-dark-border/40 last:border-0"
              >
                <Monitor
                  size={15}
                  className="shrink-0 text-cbt-textMuted dark:text-cbt-dark-textMuted"
                />
                <div className="min-w-0 flex-1">
                  <p className="text-[14px] text-cbt-text dark:text-cbt-dark-text">
                    {deviceLabel(d.user_agent)}
                    {d.current && (
                      <span className="ml-2 text-[11px] px-2 py-0.5 rounded-full bg-cbt-surface dark:bg-cbt-dark-surface text-cbt-textSecondary dark:text-cbt-dark-textSecondary">
                        bu cihaz
                      </span>
                    )}
                  </p>
                  <p className="text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted mt-0.5">
                    Son kullanım{" "}
                    {formatRelativeTime(
                      new Date(d.last_used_at || d.created_at).getTime()
                    )}
                  </p>
                </div>
                {!d.current && (
                  <button
                    onClick={() => void cihazKapat(d.id)}
                    className="text-[12px] text-cbt-textMuted dark:text-cbt-dark-textMuted hover:text-cbt-danger dark:hover:text-cbt-dark-danger transition-colors shrink-0"
                  >
                    Kapat
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {devices.length > 1 && (
          <button
            onClick={() => void logoutAll()}
            className="mt-4 inline-flex items-center gap-1.5 text-[13px] text-cbt-textSecondary dark:text-cbt-dark-textSecondary hover:text-cbt-danger dark:hover:text-cbt-dark-danger transition-colors"
          >
            <LogOut size={13} />
            Tüm cihazlardan çık
          </button>
        )}
      </section>
    </div>
  );
}