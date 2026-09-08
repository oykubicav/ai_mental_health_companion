// KVKK consent — persist accepted-at timestamp in localStorage.
// This is MVP-level. Prod: send /consent POST to backend so it's audited.

const KEY = "cbt_consent_at";

// Sunucudaki CBT_POLICY_VERSION ile aynı olmalı; uyuşmazsa /consent 400 döner.
export const POLICY_VERSION = "0.2";

export function hasConsent(): boolean {
  if (typeof window === "undefined") return true; // SSR — don't gate
  return window.localStorage.getItem(KEY) !== null;
}

export function grantConsent(): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, new Date().toISOString());
}

export function getConsentAt(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(KEY);
}

export function revokeConsent(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(KEY);
}
