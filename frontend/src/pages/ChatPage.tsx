import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Sparkles, FileText, Languages, MessageSquarePlus } from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { MessageBubble } from "@/components/MessageBubble";
import { Composer } from "@/components/Composer";
import { useConversations } from "@/contexts/ConversationContext";
import { conversations as api } from "@/services/api";

const EXAMPLES = [
  "Summarise the key points of my documents",
  "What is the leave policy?",
  "List the main security requirements",
];

export function ChatPage() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const { refresh } = useConversations();
  const [preset, setPreset] = useState("");
  const lastUserMsg = useRef<string>("");
  // The conversation whose messages are currently in state. Used to decide when
  // to (re)load history. Kept idempotent so React 18 StrictMode's double-invoked
  // effects can't reload an empty (not-yet-persisted) conversation and wipe the
  // messages we're actively streaming.
  const loadedConvId = useRef<string | null>(null);

  const onConversation = (id: string) => {
    if (id !== conversationId) {
      // We're streaming into this brand-new conversation — claim it so the
      // history-load effect skips it instead of fetching an empty result.
      loadedConvId.current = id;
      navigate(`/c/${id}`, { replace: true });
      refresh();
    }
  };

  const { messages, streaming, send, stop, reset } = useChat(onConversation);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load a conversation's history only when switching to a DIFFERENT one than
  // what's already in state (idempotent across StrictMode double-runs).
  useEffect(() => {
    if (!conversationId) {
      if (loadedConvId.current !== null) {
        loadedConvId.current = null;
        reset([]);
      }
      return;
    }
    if (conversationId === loadedConvId.current) return; // already loaded / streaming
    loadedConvId.current = conversationId;
    api.get(conversationId).then((c) => reset(c.messages)).catch(() => reset([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const handleSend = (text: string) => {
    lastUserMsg.current = text;
    send(text, conversationId ?? null);
    refresh();
  };

  const regenerate = () => {
    if (lastUserMsg.current) send(lastUserMsg.current, conversationId ?? null);
  };

  const empty = messages.length === 0;

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="scrollbar-thin min-h-0 flex-1 overflow-y-auto">
        {empty ? (
          <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center px-4 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
              <Sparkles className="h-7 w-7" />
            </div>
            <h1 className="mt-4 text-2xl font-semibold">Ask your documents anything</h1>
            <p className="mt-2 max-w-md text-sm text-muted-foreground">
              Hybrid retrieval + reranking over your local knowledge base, with citations, multilingual support, and
              fully offline local LLMs.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {EXAMPLES.map((e) => (
                <button
                  key={e}
                  onClick={() => setPreset(e)}
                  className="rounded-full border border-border bg-card px-4 py-2 text-sm hover:bg-accent hover:text-accent-foreground"
                >
                  {e}
                </button>
              ))}
            </div>
            <div className="mt-6 flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1"><FileText className="h-3.5 w-3.5" /> Citations</span>
              <span className="flex items-center gap-1"><Languages className="h-3.5 w-3.5" /> Any language</span>
              <span className="flex items-center gap-1"><MessageSquarePlus className="h-3.5 w-3.5" /> Follow-ups</span>
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl divide-y divide-border/50">
            {messages.map((m, i) => (
              <MessageBubble
                key={i}
                message={m}
                isLast={i === messages.length - 1}
                onRegenerate={regenerate}
                onPickRecommendation={handleSend}
              />
            ))}
          </div>
        )}
      </div>

      <Composer onSend={handleSend} onStop={stop} streaming={streaming} presetValue={preset} />
    </div>
  );
}
