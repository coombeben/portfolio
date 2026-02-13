"use client";

import React, {createContext, useContext, useState, useCallback, useEffect} from "react";
import { apiFetch, UnauthorizedError } from "@/api/client";

interface QuotaContextType {
  used: number;
  total: number;
  refreshQuota: () => Promise<void>;
}

const QuotaContext = createContext<QuotaContextType | undefined>(undefined);

export function QuotaProvider({ children }: { children: React.ReactNode }) {
  const [used, setUsed] = useState(NaN);
  const [total, setTotal] = useState(NaN);

  const refreshQuota = useCallback(async () => {
    try {
      const response = await apiFetch("/api/quota");
      const data = await response.json();
      setUsed(data.limit - data.remaining);
      setTotal(data.limit);
    } catch (error) {
      if (error instanceof UnauthorizedError) {
        return;
      }
      console.error("Failed to fetch quota:", error);
    }
  }, []);

  useEffect(() => {
    refreshQuota();
  }, [refreshQuota])

  return (
    <QuotaContext.Provider value={{ used, total, refreshQuota }}>
      {children}
    </QuotaContext.Provider>
  );
}

// Custom hook for easy access
export function useQuota() {
  const context = useContext(QuotaContext);
  if (!context) throw new Error("useQuota must be used within a QuotaProvider");
  return context;
}