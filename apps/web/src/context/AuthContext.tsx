import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { clearTokens, setTokens } from "@/lib/authStorage";
import * as api from "@/api/endpoints";
import type { User } from "@/api/endpoints";

type AuthState = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const u = await api.fetchMe();
    setUser(u);
  }, []);

  useEffect(() => {
    const t = localStorage.getItem("docintel_access_token");
    if (!t) {
      setLoading(false);
      return;
    }
    refreshUser()
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    const r = await api.login(email, password);
    setTokens(r.tokens.access_token, r.tokens.refresh_token);
    setUser(r.user);
  }, []);

  const register = useCallback(async (email: string, password: string, fullName?: string) => {
    const r = await api.register(email, password, fullName);
    setTokens(r.tokens.access_token, r.tokens.refresh_token);
    setUser(r.user);
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refreshUser }),
    [user, loading, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
