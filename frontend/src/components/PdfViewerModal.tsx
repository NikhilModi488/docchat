import { useEffect, useState } from "react";
import { Download, Maximize2, Minimize2, ZoomIn, ZoomOut, X, Loader2 } from "lucide-react";
import { Button, Modal } from "./ui";
import { documents, downloadAuthed, fetchAuthedObjectUrl } from "@/services/api";

interface Props {
  open: boolean;
  onClose: () => void;
  docId: string;
  filename: string;
  page: number;
  totalPages?: number;
  highlight?: string;
}

// Server-side render DPI scale — fixed and high so the page stays crisp at any
// display zoom. Display size is controlled separately via CSS (see `fit`).
const RENDER_ZOOM = 2.5;

/**
 * Renders the cited PDF page as a server-rasterised PNG (PyMuPDF). The page is
 * fetched with an AUTHENTICATED request (Bearer token in the header) and shown
 * via an object URL — a plain <img src> can't carry the token, which 404s
 * user-owned documents. This sidesteps sandboxed-iframe PDF rendering, keeps
 * per-user isolation, and never leaks the server file path.
 *
 * Display fit: `fit = 1` shows the WHOLE page width inside the modal (default).
 * Zoom in/out scales the displayed size via CSS (the underlying PNG is always
 * rendered at RENDER_ZOOM for sharpness), so the whole page is visible and never
 * cut off.
 */
export function PdfViewerModal({ open, onClose, docId, filename, page, totalPages = 1, highlight }: Props) {
  const [fit, setFit] = useState(1); // 1 = fit page width; >1 zoom in; <1 zoom out
  const [current, setCurrent] = useState(page);
  const [full, setFull] = useState(false);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [imgUrl, setImgUrl] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (open) {
      setCurrent(page);
      setFit(1);
    }
  }, [page, open]);

  // Fetch the page image (authenticated) whenever the doc/page changes.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    let createdUrl: string | null = null;
    setLoading(true);
    setFailed(false);

    fetchAuthedObjectUrl(documents.pageUrl(docId, current, RENDER_ZOOM))
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        createdUrl = url;
        setImgUrl(url);
        setLoading(false);
      })
      .catch(() => {
        if (!cancelled) {
          setFailed(true);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [open, docId, current]);

  const download = async () => {
    setDownloading(true);
    try {
      await downloadAuthed(documents.fileUrl(docId), filename);
    } catch {
      /* ignore */
    } finally {
      setDownloading(false);
    }
  };

  if (!open) return null;

  return (
    <Modal open={open} onClose={onClose} className={full ? "max-w-[96vw]" : "max-w-4xl"}>
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium" title={filename}>{filename}</p>
          <p className="text-xs text-muted-foreground">Page {current}{totalPages > 1 ? ` of ${totalPages}` : ""}</p>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" onClick={() => setFit((z) => Math.max(0.5, +(z - 0.25).toFixed(2)))} title="Zoom out"><ZoomOut className="h-4 w-4" /></Button>
          <button onClick={() => setFit(1)} className="w-12 text-center text-xs text-muted-foreground hover:text-foreground" title="Fit page width">
            {Math.round(fit * 100)}%
          </button>
          <Button variant="ghost" size="icon" onClick={() => setFit((z) => Math.min(3, +(z + 0.25).toFixed(2)))} title="Zoom in"><ZoomIn className="h-4 w-4" /></Button>
          <Button variant="ghost" size="icon" loading={downloading} onClick={download} title="Download"><Download className="h-4 w-4" /></Button>
          <Button variant="ghost" size="icon" onClick={() => setFull((f) => !f)} title="Full screen">
            {full ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose} title="Close"><X className="h-4 w-4" /></Button>
        </div>
      </div>

      {highlight && (
        <div className="border-b border-border bg-accent/40 px-4 py-2 text-xs text-accent-foreground">
          <span className="font-medium">Cited passage:</span> {highlight.slice(0, 220)}…
        </div>
      )}

      <div className="scrollbar-thin relative max-h-[78vh] overflow-auto bg-muted/30 p-4">
        {loading && !failed && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}
        {failed && (
          <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
            <p className="text-sm font-medium">This page preview isn’t available.</p>
            <p className="max-w-sm text-xs text-muted-foreground">
              The file may have been removed or re-indexed, or it belongs to a different
              account — sign in as its owner to view it. You can also try downloading the source.
            </p>
            <Button variant="outline" size="sm" loading={downloading} onClick={download} className="mt-1">
              <Download className="h-4 w-4" /> Download source
            </Button>
          </div>
        )}
        {!loading && !failed && imgUrl && (
          /* Centering wrapper; the image width is a % of the container so fit=1
             shows the full page width, and zoom scales from there. */
          <div className="flex justify-center">
            <img
              src={imgUrl}
              alt={`${filename} page ${current}`}
              style={{ width: `${fit * 100}%`, maxWidth: fit <= 1 ? "100%" : "none" }}
              className="h-auto rounded shadow-lg"
            />
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 border-t border-border px-4 py-2">
          <Button variant="outline" size="sm" disabled={current <= 1} onClick={() => setCurrent((c) => c - 1)}>Previous</Button>
          <span className="text-xs text-muted-foreground">{current} / {totalPages}</span>
          <Button variant="outline" size="sm" disabled={current >= totalPages} onClick={() => setCurrent((c) => c + 1)}>Next</Button>
        </div>
      )}
    </Modal>
  );
}
