"use client";

import { useEffect, useState } from "react";
import { hasConsent } from "@/lib/consent";
import { readLegacyLocalProfile, clearProfile } from "@/lib/profile";
import ConsentModal from "@/components/ConsentModal";
import ChatWindow from "@/components/ChatWindow";
import Landing from "@/components/Landing";
import Onboarding from "@/components/Onboarding";
import { hasDecided } from "@/lib/assessments";
import AssessmentOptInModal from "@/components/AssessmentOptInModal";
import { useAuth } from "@/hooks/AuthProvider";

type Stage = "landing" | "consent" | "onboarding" | "chat";

export default function Page() {
  const { isAuthenticated, loading, user, updateProfile } = useAuth();
  const [state, setState] = useState<Stage>("landing");
  const [mounted, setMounted] = useState(false);
  const [showOptIn, setShowOptIn] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Sunucuya geçişten önce cihazda kalmış ad/konu bir kez yukarı taşınır,
  // böylece eskiden onboarding yapmış kullanıcıya tekrar sorulmuyor.
  useEffect(() => {
    if (loading || !user || user.onboarded_at) return;
    const eski = readLegacyLocalProfile();
    if (!eski) return;
    updateProfile({ display_name: eski.name, focus_topics: eski.focus })
      .catch(() => {})
      .finally(clearProfile);
  }, [loading, user, updateProfile]);

  useEffect(() => {
    if (loading) return;
    if (isAuthenticated) {
      setState(nextStage());
    } else {
      // Çıkış yapıldı ya da oturum düştü. ChatWindow'u ekrandan kaldırıyoruz:
      // bileşen ekranda kalırsa karşılama metni, mesajlar ve oturum kimliği
      // gibi yerel state'ler önceki kullanıcıdan devralınıyor.
      setState("landing");
    }
  }, [loading, isAuthenticated, user?.onboarded_at]);

  useEffect(() => {
    if (state === "chat" && isAuthenticated && !hasDecided()) {
      const timer = setTimeout(() => setShowOptIn(true), 2500);
      return () => clearTimeout(timer);
    }
  }, [state, isAuthenticated]);

  // Onboarding yalnızca hesabı olan kullanıcıya, ilk girişinde.
  // Karar sunucudaki onboarded_at damgasına bakıyor; cihazdaki bir veri
  // kaybı ya da geçici oturum düşmesi onboarding'i tekrar açmıyor.
  function nextStage(): Stage {
    if (!hasConsent()) return "consent";
    if (isAuthenticated && !user?.onboarded_at) return "onboarding";
    return "chat";
  }

  if (!mounted || loading) return null;

  if (state === "onboarding") {
    return <Onboarding onDone={() => setState("chat")} />;
  }

  if (state === "chat") {
    return (
      <>
        <ChatWindow />
        {showOptIn && <AssessmentOptInModal onDismiss={() => setShowOptIn(false)} />}
      </>
    );
  }

  return (
    <>
      <Landing onStart={() => setState(nextStage())} />
      {state === "consent" && (
        <ConsentModal
          onGranted={() =>
            setState(isAuthenticated && !user?.onboarded_at ? "onboarding" : "chat")
          }
        />
      )}
    </>
  );
}
