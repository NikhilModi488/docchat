import { useState } from "react";
import { Copy, Check, ThumbsUp, ThumbsDown, RefreshCw, User, Sparkles, Clock, Languages } from "lucide-react";
import { Markdown } from "./Markdown";
import { CitationsPanel } from "./CitationsPanel";
import { Badge, Spinner } from "./ui";
import { submitFeedback } from "@/services/api";
import type { ChatMessage } from "@/services/types";
import { cn } from "@/lib/utils";

interface Props {
  message: ChatMessage;
  isLast: boolean;
  onRegenerate?: () => void;
  onPickRecommendation?: (q: string) => void;
}

export function MessageBubble({ message, isLast, onRegenerate, onPickRecommendation }: Props) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(message.feedback ?? null);
  const isUser = message.role === "user";

  const copy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const rate = async (r: "up" | "down") => {
    setFeedback(r);
    if (message.id) {
      try {
        await submitFeedback(message.id, r);
      } catch {
        /* ignore */
      }
    }
  };

  const ragas = message.ragas_score;
  const hasRagas = ragas && typeof ragas.faithfulness === "number";

  return (
    <div className={cn("flex gap-3 px-4 py-5 animate-fade-in", isUser ? "bg-transparent" : "bg-card/40")}>
      <div className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", isUser ? "bg-secondary" : "bg-primary text-primary-foreground")}>
        {isUser ? <User className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">{isUser ? "You" : "DocChat"}</span>
          {message.language && message.language !== "en" && (
            <Badge className="bg-accent text-accent-foreground"><Languages className="mr-1 h-3 w-3" />{message.language}</Badge>
          )}
        </div>

        <div className="mt-1">
          {message.content ? <Markdown content={message.content} /> : message.streaming ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner /> retrieving &amp; thinking…
            </div>
          ) : null}
          {message.streaming && message.content && <span className="ml-0.5 inline-block h-4 w-2 animate-pulse-dot bg-primary align-middle" />}
        </div>

        {!isUser && !!message.citations?.length && (
          <CitationsPanel citations={message.citations} chunks={message.chunks} />
        )}

        {!isUser && !message.streaming && !!message.recommendation_questions?.length && (
          <div className="mt-3">
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">Suggested follow-ups</p>
            <div className="flex flex-wrap gap-2">
              {message.recommendation_questions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => onPickRecommendation?.(q)}
                  className="rounded-full border border-border bg-background px-3 py-1.5 text-xs hover:bg-accent hover:text-accent-foreground"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {!isUser && !message.streaming && message.content && (
          <div className="mt-3 flex flex-wrap items-center gap-3 text-muted-foreground">
            <button onClick={copy} className="flex items-center gap-1 text-xs hover:text-foreground">
              {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />} {copied ? "Copied" : "Copy"}
            </button>
            {isLast && onRegenerate && (
              <button onClick={onRegenerate} className="flex items-center gap-1 text-xs hover:text-foreground">
                <RefreshCw className="h-3.5 w-3.5" /> Regenerate
              </button>
            )}
            <button onClick={() => rate("up")} className={cn("hover:text-foreground", feedback === "up" && "text-green-500")}>
              <ThumbsUp className="h-3.5 w-3.5" />
            </button>
            <button onClick={() => rate("down")} className={cn("hover:text-foreground", feedback === "down" && "text-destructive")}>
              <ThumbsDown className="h-3.5 w-3.5" />
            </button>
            {!!message.response_time && (
              <span className="flex items-center gap-1 text-xs"><Clock className="h-3 w-3" />{message.response_time.toFixed(1)}s</span>
            )}
            {hasRagas && (
              <span className="text-xs" title="RAGAS: faithfulness / answer relevancy / context precision">
                RAGAS {ragas!.faithfulness.toFixed(2)} / {(ragas!.answer_relevancy ?? 0).toFixed(2)} / {(ragas!.context_precision ?? 0).toFixed(2)}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
