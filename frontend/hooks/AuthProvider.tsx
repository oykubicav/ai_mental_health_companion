"use client";

import { createContext, useContext } from "react";
import { useAuthState } from "./useAuth";

type AuthValue = ReturnType<typeof useAuthState>;

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const value = useAuthState();
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth, AuthProvider içinde çağrılmalı");
  }
  return ctx;
}