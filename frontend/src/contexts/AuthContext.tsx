import React, { createContext, useContext, useEffect, useState } from "react";
import { auth, getToken, setToken } from "@/services/api";

interface AuthCtx {
  username: string | null;
  ready: boolean;
  login: (u: string, p: string) => Promise<void>;
  register: (u: string, p: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>(null!);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [username, setUsername] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      if (getToken()) {
        try {
          const me = await auth.me();
          setUsername(me.username);
        } catch {
          setToken(null);
        }
      }
      setReady(true);
    })();
  }, []);

  const login = async (u: string, p: string) => {
    const r = await auth.login(u, p);
    setToken(r.access_token);
    setUsername(r.username);
  };
  const register = async (u: string, p: string) => {
    const r = await auth.register(u, p);
    setToken(r.access_token);
    setUsername(r.username);
  };
  const logout = () => {
    setToken(null);
    setUsername(null);
  };

  return <Ctx.Provider value={{ username, ready, login, register, logout }}>{children}</Ctx.Provider>;
}
