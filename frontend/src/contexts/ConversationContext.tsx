import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { conversations as api } from "@/services/api";
import type { ConversationSummary } from "@/services/types";

interface ConvCtx {
  list: ConversationSummary[];
  refresh: () => Promise<void>;
}
const Ctx = createContext<ConvCtx>({ list: [], refresh: async () => {} });
export const useConversations = () => useContext(Ctx);

export function ConversationProvider({ children }: { children: React.ReactNode }) {
  const [list, setList] = useState<ConversationSummary[]>([]);
  const refresh = useCallback(async () => {
    try {
      const r = await api.list();
      setList(r.conversations);
    } catch {
      /* ignore (e.g. backend offline) */
    }
  }, []);
  useEffect(() => {
    refresh();
  }, [refresh]);
  return <Ctx.Provider value={{ list, refresh }}>{children}</Ctx.Provider>;
}
