/**
 * services/api.ts
 * Typed client for the FastAPI backend. All requests are same-origin via the
 * Vite dev proxy (/api -> :8000). Bearer token (if any) is attached from
 * localStorage. Streaming uses fetch + a ReadableStream SSE parser so we can
 * pass an AbortSignal for the "stop generation" button.
 */
import type {
  Analytics,
  ChatMessage,
  ConversationSummary,
  DocumentInfo,
  HealthInfo,
} from "./types";

const TOKEN_KEY = "docchat_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string | null) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const t = getToken();
  return t ? { ...extra, Authorization: `Bearer ${t}` } : extra;
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

// --- auth -----------------------------------------------------------------
export const auth = {
  register: (username: string, password: string) =>
    fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }).then(handle<{ access_token: string; username: string }>),
  login: (username: string, password: string) =>
    fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }).then(handle<{ access_token: string; username: string }>),
  me: () => fetch("/api/auth/me", { headers: authHeaders() }).then(handle<{ username: string }>),
};

// --- health ---------------------------------------------------------------
export const getHealth = () => fetch("/api/health").then(handle<HealthInfo>);

// --- documents ------------------------------------------------------------
export const documents = {
  list: () => fetch("/api/documents", { headers: authHeaders() }).then(handle<{ documents: DocumentInfo[] }>),
  remove: (id: string) =>
    fetch(`/api/document/${id}`, { method: "DELETE", headers: authHeaders() }).then(handle),
  reindex: (id: string) =>
    fetch(`/api/reindex?doc_id=${encodeURIComponent(id)}`, { method: "POST", headers: authHeaders() }).then(handle),
  fileUrl: (id: string) => `/api/document/${id}/file`,
  pageUrl: (id: string, page: number, zoom = 2) => `/api/document/${id}/page/${page}.png?zoom=${zoom}`,
};

/**
 * Fetch a protected media URL WITH the auth header and return an object URL.
 * Plain <img src>/<a href> can't carry the Bearer token, which 404s
 * user-owned documents — this keeps the token in the header and respects
 * per-user isolation. Caller must URL.revokeObjectURL when done.
 */
export async function fetchAuthedObjectUrl(url: string): Promise<string> {
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* not json */
    }
    throw new Error(detail);
  }
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

/** Download a protected file via authenticated fetch (token in header). */
export async function downloadAuthed(url: string, filename: string): Promise<void> {
  const objectUrl = await fetchAuthedObjectUrl(url);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

/** Upload with progress via XHR (fetch lacks upload progress). */
export function uploadDocument(
  file: File,
  onProgress?: (pct: number) => void
): Promise<{ doc_id: string; filename: string; chunks: number }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/upload");
    const t = getToken();
    if (t) xhr.setRequestHeader("Authorization", `Bearer ${t}`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText));
      else {
        let msg = xhr.statusText;
        try {
          msg = JSON.parse(xhr.responseText).detail;
        } catch {
          /* ignore */
        }
        reject(new Error(msg));
      }
    };
    xhr.onerror = () => reject(new Error("Network error during upload"));
    const fd = new FormData();
    fd.append("file", file);
    xhr.send(fd);
  });
}

// --- conversations --------------------------------------------------------
export const conversations = {
  list: () =>
    fetch("/api/conversations", { headers: authHeaders() }).then(
      handle<{ conversations: ConversationSummary[] }>
    ),
  create: () => fetch("/api/conversation", { method: "POST", headers: authHeaders() }).then(handle<ConversationSummary>),
  get: (id: string) =>
    fetch(`/api/conversation/${id}`, { headers: authHeaders() }).then(
      handle<ConversationSummary & { messages: ChatMessage[] }>
    ),
  rename: (id: string, title: string) =>
    fetch(`/api/conversation/${id}`, {
      method: "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({ title }),
    }).then(handle),
  remove: (id: string) =>
    fetch(`/api/conversation/${id}`, { method: "DELETE", headers: authHeaders() }).then(handle),
};

// --- feedback & analytics -------------------------------------------------
export const submitFeedback = (message_id: number, rating: "up" | "down", comment = "") =>
  fetch("/api/feedback", {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ message_id, rating, comment }),
  }).then(handle);

export const getAnalytics = () => fetch("/api/analytics", { headers: authHeaders() }).then(handle<Analytics>);

// --- streaming chat -------------------------------------------------------
export type StreamEvent =
  | { type: "conversation"; conversation_id: string }
  | { type: "sources"; citations: any[]; chunks: any[]; language: string }
  | { type: "token"; text: string }
  | { type: "final"; [k: string]: any }
  | { type: "done" }
  | { type: "error"; message: string };

/** Open an SSE stream for a query. Returns once the stream completes/aborts. */
export async function streamQuery(
  query: string,
  conversationId: string | null,
  onEvent: (e: StreamEvent) => void,
  signal: AbortSignal
): Promise<void> {
  const res = await fetch("/api/stream-query", {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ query, conversation_id: conversationId }),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(`Stream failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data:")) continue;
      try {
        onEvent(JSON.parse(line.slice(5).trim()));
      } catch {
        /* skip malformed frame */
      }
    }
  }
}
