import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Plus, MessageSquare, Trash2, Pencil, Check, X, FileText } from "lucide-react";
import { Button } from "./ui";
import { useConversations } from "@/contexts/ConversationContext";
import { conversations as api } from "@/services/api";
import { cn, relativeTime } from "@/lib/utils";

export function Sidebar() {
  const { list, refresh } = useConversations();
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  const newChat = async () => {
    const c = await api.create();
    await refresh();
    navigate(`/c/${c.id}`);
  };

  const remove = async (id: string) => {
    await api.remove(id);
    await refresh();
    if (conversationId === id) navigate("/");
  };

  const saveRename = async (id: string) => {
    if (draft.trim()) await api.rename(id, draft.trim());
    setEditing(null);
    await refresh();
  };

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-card/40">
      <div className="flex items-center gap-2 px-4 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <FileText className="h-4 w-4" />
        </div>
        <span className="text-lg font-semibold tracking-tight">DocChat</span>
      </div>

      <div className="px-3">
        <Button onClick={newChat} className="w-full justify-start">
          <Plus className="h-4 w-4" /> New chat
        </Button>
      </div>

      <div className="mt-3 px-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">Conversations</div>
      <nav className="scrollbar-thin mt-1 flex-1 space-y-0.5 overflow-y-auto px-2 pb-4">
        {list.length === 0 && <p className="px-2 py-4 text-sm text-muted-foreground">No conversations yet.</p>}
        {list.map((c) => {
          const active = c.id === conversationId;
          return (
            <div
              key={c.id}
              className={cn(
                "group flex items-center gap-1 rounded-md px-2 py-2 text-sm transition-colors",
                active ? "bg-accent text-accent-foreground" : "hover:bg-secondary"
              )}
            >
              {editing === c.id ? (
                <div className="flex w-full items-center gap-1">
                  <input
                    autoFocus
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && saveRename(c.id)}
                    className="h-7 w-full rounded border border-input bg-background px-2 text-xs"
                  />
                  <button onClick={() => saveRename(c.id)} className="text-green-500"><Check className="h-4 w-4" /></button>
                  <button onClick={() => setEditing(null)} className="text-muted-foreground"><X className="h-4 w-4" /></button>
                </div>
              ) : (
                <>
                  <Link to={`/c/${c.id}`} className="flex min-w-0 flex-1 items-center gap-2">
                    <MessageSquare className="h-4 w-4 shrink-0 opacity-70" />
                    <span className="min-w-0 flex-1 truncate" title={c.title}>{c.title}</span>
                  </Link>
                  <div className="flex shrink-0 items-center gap-0.5 opacity-0 group-hover:opacity-100">
                    <button
                      onClick={() => { setEditing(c.id); setDraft(c.title); }}
                      className="rounded p-1 text-muted-foreground hover:text-foreground"
                      title="Rename"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => remove(c.id)}
                      className="rounded p-1 text-muted-foreground hover:text-destructive"
                      title="Delete"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </>
              )}
            </div>
          );
        })}
      </nav>

      <div className="border-t border-border px-4 py-3 text-xs text-muted-foreground">
        Local RAG · fully offline
      </div>
    </aside>
  );
}
