"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch, setUnauthorizedHandler, UnauthorizedError } from "@/api/client";

export type AuthStatus = "checking" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  isAuthenticated: boolean;
  checkSession: () => Promise<void>;
  login: (password: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export class RateLimitError extends Error {
  constructor(message = "Too many sessions created today.") {
    super(message);
    this.name = "RateLimitError";
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("checking");

  const checkSession = useCallback(async () => {
    setStatus("checking");
    try {
      const response = await apiFetch("/auth/session", { method: "GET" });
      if (!response.ok) {
        throw new Error("Session check failed");
      }
      setStatus("authenticated");
    } catch (error) {
      if (error instanceof UnauthorizedError) {
        setStatus("unauthenticated");
        return;
      }
      console.error("Failed to check session:", error);
      setStatus("unauthenticated");
    }
  }, []);

  const login = useCallback(async (password: string) => {
    const response = await fetch("/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      credentials: "include",
      body: JSON.stringify({ password }),
    });

    if (response.status === 429) {
      throw new RateLimitError();
    }

    if (response.status === 401) {
      throw new UnauthorizedError("Invalid password");
    }

    if (!response.ok) {
      throw new Error("Login failed");
    }

    setStatus("authenticated");
  }, []);

  useEffect(() => {
    let isActive = true;

    setUnauthorizedHandler(() => {
      if (isActive) {
        setStatus("unauthenticated");
      }
    });

    void checkSession();

    return () => {
      isActive = false;
      setUnauthorizedHandler(null);
    };
  }, [checkSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      isAuthenticated: status === "authenticated",
      checkSession,
      login,
    }),
    [status, checkSession, login],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}

