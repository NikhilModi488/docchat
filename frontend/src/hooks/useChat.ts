import { useCallback, useRef, useState } from "react";
import { streamQuery } from "@/services/api";
import type { ChatMessage } from "@/services/types";

/**
 * useChat — owns the message list for the active conversation and drives SSE
 * streaming, exposing send/stop. The conversationId is created lazily by the
 * backend on first message and surfaced via onConversation.
 */
export function useChat(onConversation?: (id: string) => void) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback((initial: ChatMessage[] = []) => {
    setMessages(initial);
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
    setMessages((prev) => prev.map((m) => (m.streaming ? { ...m, streaming: false } : m)));
  }, []);

  const send = useCallback(
    async (text: string, conversationId: string | null) => {
      const trimmed = text.trim();
      if (!trimmed || streaming) return;

      setMessages((prev) => [
        ...prev,
        { role: "user", content: trimmed },
        { role: "assistant", content: "", streaming: true },
      ]);
      setStreaming(true);
      const ac = new AbortController();
      abortRef.current = ac;

      const patchLast = (patch: Partial<ChatMessage>) =>
        setMessages((prev) => {
          const next = [...prev];
          const i = next.length - 1;
          next[i] = { ...next[i], ...patch };
          return next;
        });

      try {
        await streamQuery(
          trimmed,
          conversationId,
          (e) => {
            if (e.type === "conversation") onConversation?.(e.conversation_id);
            else if (e.type === "sources") patchLast({ citations: e.citations, chunks: e.chunks, language: e.language });
            else if (e.type === "token") setMessages((prev) => {
              const next = [...prev];
              const i = next.length - 1;
              next[i] = { ...next[i], content: next[i].content + e.text };
              return next;
            });
            else if (e.type === "final")
              patchLast({
                id: e.message_id,
                content: e.response,
                citations: e.citations,
                chunks: e.chunks,
                recommendation_questions: e.recommendation_questions,
                ragas_score: e.ragas_score,
                token_usage: e.token_usage,
                response_time: e.response_time,
                language: e.language,
                streaming: false,
              });
            else if (e.type === "error") patchLast({ content: `⚠️ ${e.message}`, streaming: false });
          },
          ac.signal
        );
      } catch (err: any) {
        if (err?.name !== "AbortError") patchLast({ content: `⚠️ ${err.message ?? err}`, streaming: false });
      } finally {
        setStreaming(false);
        patchLast({ streaming: false });
      }
    },
    [streaming, onConversation]
  );

  return { messages, streaming, send, stop, reset, setMessages };
}
