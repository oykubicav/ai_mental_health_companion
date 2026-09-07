"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { setAccessToken, clearAccessToken } from "@/lib/auth";
import {
  postLogin, postRegister, deleteMe, patchMyProfile,
  postLogout, postLogoutAll, setSessionLostHandler,
} from "@/lib/api";
import { clearSessionId } from "@/lib/session";
import { clearProfile } from "@/lib/profile";
import type { AuthUser, ProfileUpdate } from "@/lib/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  export function useAuthState() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  // Açılışta bellekte token yok — sayfa yenilenince kayboluyor. httpOnly
  // refresh çerezi varsa /auth/refresh hem yeni token'ı hem kullanıcıyı
  // veriyor, yoksa 401 gelir ve anonim devam ederiz.
  useEffect(() => {
    let iptal = false;

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          credentials: "include",
          headers: {
            "Content-Type": "application/json",
            "X-Neva-Client": "web",
          },
        });
        if (!iptal && res.ok) {
          const data = await res.json();
          setAccessToken(data.access_token);
          setUser(data.user);
        }
      } catch {
        // Ağ hatası — anonim başlıyoruz, kullanıcı tekrar girebilir.
      } finally {
        if (!iptal) setLoading(false);
      }
    })();

    return () => {
      iptal = true;
    };
  }, []);

  // fetchJson bir bileşen değil, hook'lara erişemiyor. Yenileme kalıcı
  // olarak başarısız olduğunda bizi buradan haberdar ediyor.
  useEffect(() => {
    setSessionLostHandler(() => {
      clearAccessToken();
      setUser(null);
    });
    return () => setSessionLostHandler(null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await postLogin(email, password);
    setAccessToken(response.access_token);
    setUser(response.user);
    clearSessionId();
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    return await postRegister(email, password);
  }, []);

  const logout = useCallback(async () => {
    // Sunucuya haber ver: refresh token iptal edilsin. Yalnızca tarayıcıyı
    // temizlemek yetmiyordu — çalıntı kopya çalışmaya devam ederdi.
    try {
      await postLogout();
    } catch {
      // Sunucuya ulaşılamasa da yerel çıkış yapılsın.
    }
    clearAccessToken();
    clearSessionId();
    clearProfile();
    setUser(null);
    router.push("/");
  }, [router]);

  const logoutAll = useCallback(async () => {
    try {
      await postLogoutAll();
    } catch {
      // yut
    }
    clearAccessToken();
    clearSessionId();
    clearProfile();
    setUser(null);
    router.push("/");
  }, [router]);

  const deleteAccount = useCallback(async () => {
    await deleteMe();
    clearAccessToken();
    clearSessionId();
    clearProfile();
    setUser(null);
    router.push("/");
  }, [router]);

  const updateProfile = useCallback(async (req: ProfileUpdate) => {
    const fresh = await patchMyProfile(req);
    setUser(fresh);
    return fresh;
  }, []);

  return {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    logoutAll,
    deleteAccount,
    updateProfile,
  };
}