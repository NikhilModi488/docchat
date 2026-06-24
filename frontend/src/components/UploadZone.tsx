import { useRef, useState } from "react";
import { UploadCloud, File as FileIcon, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { uploadDocument } from "@/services/api";
import { cn } from "@/lib/utils";

const ALLOWED = [".pdf", ".docx", ".txt", ".md", ".pptx"];

interface UploadItem {
  name: string;
  pct: number;
  status: "uploading" | "done" | "error";
  message?: string;
}

export function UploadZone({ onUploaded }: { onUploaded: () => void }) {
  const [drag, setDrag] = useState(false);
  const [items, setItems] = useState<UploadItem[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (files: FileList | null) => {
    if (!files) return;
    for (const file of Array.from(files)) {
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (!ALLOWED.includes(ext)) {
        setItems((p) => [...p, { name: file.name, pct: 0, status: "error", message: "Unsupported type" }]);
        continue;
      }
      const idx = items.length;
      setItems((p) => [...p, { name: file.name, pct: 0, status: "uploading" }]);
      try {
        await uploadDocument(file, (pct) =>
          setItems((p) => p.map((it, i) => (it.name === file.name && it.status === "uploading" ? { ...it, pct } : it)))
        );
        setItems((p) => p.map((it) => (it.name === file.name ? { ...it, pct: 100, status: "done" } : it)));
        onUploaded();
      } catch (e: any) {
        setItems((p) => p.map((it) => (it.name === file.name ? { ...it, status: "error", message: e.message } : it)));
      }
    }
  };

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); handleFiles(e.dataTransfer.files); }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors",
          drag ? "border-primary bg-accent/40" : "border-border hover:border-primary/60 hover:bg-secondary/40"
        )}
      >
        <UploadCloud className="h-9 w-9 text-primary" />
        <p className="mt-3 text-sm font-medium">Drag &amp; drop files here, or click to browse</p>
        <p className="mt-1 text-xs text-muted-foreground">PDF, DOCX, TXT, Markdown, PPTX · up to 25 MB</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ALLOWED.join(",")}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {items.length > 0 && (
        <div className="mt-3 space-y-2">
          {items.map((it, i) => (
            <div key={i} className="flex items-center gap-3 rounded-md border border-border bg-card px-3 py-2">
              <FileIcon className="h-4 w-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <span className="truncate text-sm">{it.name}</span>
                  {it.status === "uploading" && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
                  {it.status === "done" && <CheckCircle2 className="h-4 w-4 text-green-500" />}
                  {it.status === "error" && <XCircle className="h-4 w-4 text-destructive" />}
                </div>
                {it.status === "uploading" && (
                  <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                    <div className="h-full bg-primary transition-all" style={{ width: `${it.pct}%` }} />
                  </div>
                )}
                {it.status === "error" && <p className="text-xs text-destructive">{it.message}</p>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
