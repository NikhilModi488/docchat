import { useEffect, useMemo, useState } from "react";
import { Search, Trash2, RefreshCw, FileText, Eye, Loader2 } from "lucide-react";
import { Button, Input, Card, Badge } from "@/components/ui";
import { UploadZone } from "@/components/UploadZone";
import { PdfViewerModal } from "@/components/PdfViewerModal";
import { documents } from "@/services/api";
import type { DocumentInfo } from "@/services/types";
import { formatTime, cn } from "@/lib/utils";

export function KnowledgePage() {
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "ready" | "processing" | "error">("all");
  const [busy, setBusy] = useState<string | null>(null);
  const [viewer, setViewer] = useState<DocumentInfo | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await documents.list();
      setDocs(r.documents);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(
    () =>
      docs.filter(
        (d) =>
          d.filename.toLowerCase().includes(query.toLowerCase()) &&
          (statusFilter === "all" || d.status === statusFilter)
      ),
    [docs, query, statusFilter]
  );

  const remove = async (id: string) => {
    setBusy(id);
    try {
      await documents.remove(id);
      await load();
    } finally {
      setBusy(null);
    }
  };
  const reindex = async (id: string) => {
    setBusy(id);
    try {
      await documents.reindex(id);
      await load();
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl px-4 py-6">
        <h1 className="text-xl font-semibold">Knowledge Base</h1>
        <p className="mt-1 text-sm text-muted-foreground">Upload and manage the documents your assistant can search.</p>

        <div className="mt-5">
          <UploadZone onUploaded={load} />
        </div>

        <div className="mt-6 flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search documents…" className="pl-9" />
          </div>
          <div className="flex gap-1 rounded-md border border-border p-0.5">
            {(["all", "ready", "processing", "error"] as const).map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={cn(
                  "rounded px-2.5 py-1 text-xs capitalize",
                  statusFilter === s ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-secondary"
                )}
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <Card className="mt-3 overflow-hidden">
          <div className="grid grid-cols-[1fr_auto_auto_auto_auto] items-center gap-3 border-b border-border px-4 py-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <span>Document</span>
            <span className="text-right">Pages</span>
            <span className="text-right">Chunks</span>
            <span className="text-right">Status</span>
            <span className="text-right">Actions</span>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-10 text-muted-foreground"><Loader2 className="h-5 w-5 animate-spin" /></div>
          ) : filtered.length === 0 ? (
            <div className="py-10 text-center text-sm text-muted-foreground">No documents found.</div>
          ) : (
            filtered.map((d) => (
              <div key={d.id} className="grid grid-cols-[1fr_auto_auto_auto_auto] items-center gap-3 border-b border-border/60 px-4 py-3 last:border-0">
                <div className="flex min-w-0 items-center gap-2">
                  <FileText className="h-4 w-4 shrink-0 text-primary" />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium" title={d.filename}>{d.filename}</p>
                    <p className="text-xs text-muted-foreground">{formatTime(d.upload_time)}</p>
                  </div>
                </div>
                <span className="text-right text-sm tabular-nums">{d.pages}</span>
                <span className="text-right text-sm tabular-nums">{d.chunk_count}</span>
                <span className="text-right">
                  <Badge className={cn(
                    d.status === "ready" && "bg-green-500/15 text-green-500",
                    d.status === "processing" && "bg-yellow-500/15 text-yellow-600",
                    d.status === "error" && "bg-destructive/15 text-destructive"
                  )}>{d.status}</Badge>
                </span>
                <div className="flex justify-end gap-0.5">
                  {d.filename.toLowerCase().endsWith(".pdf") && (
                    <Button variant="ghost" size="icon" onClick={() => setViewer(d)} title="Preview"><Eye className="h-4 w-4" /></Button>
                  )}
                  <Button variant="ghost" size="icon" loading={busy === d.id} onClick={() => reindex(d.id)} title="Re-index"><RefreshCw className="h-4 w-4" /></Button>
                  <Button variant="ghost" size="icon" loading={busy === d.id} onClick={() => remove(d.id)} title="Delete"><Trash2 className="h-4 w-4 text-destructive" /></Button>
                </div>
              </div>
            ))
          )}
        </Card>
      </div>

      {viewer && (
        <PdfViewerModal open={!!viewer} onClose={() => setViewer(null)} docId={viewer.id} filename={viewer.filename} page={1} totalPages={viewer.pages} />
      )}
    </div>
  );
}
