import { useState } from "react";
import { FileText, ChevronDown, Copy, Check, Maximize2, Minimize2 } from "lucide-react";
import { Badge } from "./ui";
import { PdfViewerModal } from "./PdfViewerModal";
import type { Citation, Chunk } from "@/services/types";
import { cn } from "@/lib/utils";

/** Resolve the full chunk text for a citation (falls back to its preview). */
function fullText(citation: Citation, chunks: Chunk[]): string {
  const byId = chunks.find((ch) => ch.chunk_id && ch.chunk_id === citation.chunk_id);
  if (byId?.content) return byId.content;
  const byPage = chunks.find((ch) => ch.filename === citation.filename && ch.page === citation.page);
  return byPage?.content || citation.preview || "";
}

function SourceCard({
  citation,
  chunks,
  onOpenPdf,
}: {
  citation: Citation;
  chunks: Chunk[];
  onOpenPdf: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const text = fullText(citation, chunks);
  const long = text.length > 280;

  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="rounded-md border border-border bg-background p-2.5">
      <div className="flex items-center justify-between gap-2">
        <button
          onClick={onOpenPdf}
          className="flex min-w-0 items-center gap-1.5 text-sm font-medium text-primary hover:underline disabled:text-foreground disabled:no-underline"
          disabled={!citation.doc_id}
          title="Open source page"
        >
          <FileText className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{citation.filename}</span>
          <span className="shrink-0 text-muted-foreground">· p.{citation.page}</span>
        </button>
        <div className="flex shrink-0 items-center gap-1.5">
          <Badge className="bg-accent text-accent-foreground">score {citation.score.toFixed(2)}</Badge>
          <button onClick={copy} title="Copy chunk" className="text-muted-foreground hover:text-foreground">
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Full chunk content — scrollable when expanded, clamped otherwise. */}
      <div
        className={cn(
          "mt-2 whitespace-pre-wrap break-words rounded bg-muted/40 p-2 text-xs leading-relaxed text-muted-foreground",
          expanded ? "scrollbar-thin max-h-72 overflow-y-auto" : "line-clamp-3"
        )}
      >
        {text}
      </div>

      {long && (
        <button
          onClick={() => setExpanded((e) => !e)}
          className="mt-1.5 flex items-center gap-1 text-xs font-medium text-primary hover:underline"
        >
          {expanded ? (
            <><Minimize2 className="h-3 w-3" /> Show less</>
          ) : (
            <><Maximize2 className="h-3 w-3" /> Show full chunk ({text.length.toLocaleString()} chars)</>
          )}
        </button>
      )}
    </div>
  );
}

export function CitationsPanel({ citations, chunks = [] }: { citations: Citation[]; chunks?: Chunk[] }) {
  const [open, setOpen] = useState(false);
  const [viewer, setViewer] = useState<Citation | null>(null);
  if (!citations?.length) return null;

  return (
    <div className="mt-3 rounded-lg border border-border bg-card/50">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium">
        <span className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-primary" /> {citations.length} source{citations.length > 1 ? "s" : ""}
        </span>
        <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="space-y-2 px-3 pb-3">
          {citations.map((c, i) => (
            <SourceCard key={c.chunk_id || i} citation={c} chunks={chunks} onOpenPdf={() => c.doc_id && setViewer(c)} />
          ))}
        </div>
      )}
      {viewer && (
        <PdfViewerModal
          open={!!viewer}
          onClose={() => setViewer(null)}
          docId={viewer.doc_id}
          filename={viewer.filename}
          page={viewer.page}
          highlight={fullText(viewer, chunks).slice(0, 220)}
        />
      )}
    </div>
  );
}
