import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, loadSession, saveSession, setUnauthorizedHandler, type Role, type Session } from "./api";

type AuthCtx = {
  session: Session | null;
  login: (username: string, password: string) => Promise<Session>;
  logout: () => void;
  can: (...roles: Role[]) => boolean;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(() => loadSession());
  const qc = useQueryClient();

  const logout = useCallback(() => {
    saveSession(null);
    setSession(null);
    qc.clear();
  }, [qc]);

  useEffect(() => setUnauthorizedHandler(logout), [logout]);

  const login = useCallback(
    async (username: string, password: string) => {
      const s = await api<Session>("/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      qc.clear();
      saveSession(s);
      setSession(s);
      return s;
    },
    [qc],
  );

  const value = useMemo<AuthCtx>(
    () => ({
      session,
      login,
      logout,
      can: (...roles) => !!session && (session.role === "presenter" || roles.includes(session.role)),
    }),
    [session, login, logout],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth outside AuthProvider");
  return v;
}

export const ROLE_LABEL: Record<Role, string> = {
  engineer: "Engineer",
  operations: "Operations",
  cfo: "CFO",
  presenter: "Presenter",
};
