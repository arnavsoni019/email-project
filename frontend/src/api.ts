/** Client for the local mailorg FastAPI backend. Nothing here talks to the network
 *  beyond localhost — the backend is the only thing that touches Gmail or a model. */

const BASE = "http://localhost:8000";

/** How many of the newest messages the inbox shows. The store holds every synced
 *  message; this only bounds what is displayed and enriched. */
export const INBOX_LIMIT = 40;

export type Priority = "action" | "fyi" | "ignore";

export interface Message {
  id: string;
  threadId: string;
  sender: string;
  email: string;
  subject: string;
  tldr: string;
  cat: string;
  prio: Priority;
  time: string;
  exact: string;
  unread: boolean;
  processed: boolean;
}

export interface MessageDetail extends Message {
  body: string;
  /** Sanitised original HTML; empty for genuinely plain-text mail. */
  html: string;
  /** Remote images replaced with blank pixels (tracking-pixel defence). */
  blockedImages: number;
  imagesLoaded: boolean;
  to: string[];
  cc: string[];
  n: number;
  earlier: { who: string; line: string; when: string }[];
}

export interface Stats {
  total: number;
  unprocessed: number;
  priorities: { id: Priority; t: string; k: number }[];
  categories: { n: string; k: number }[];
  account: string;
}

export interface AppSettings {
  /** Live value: the .env ceiling narrowed by the UI switch. */
  cloud_enabled: boolean;
  cloud_allowed_tasks: string[];
  /** What .env permits the switch to reach; empty means the switch is inert. */
  cloud_allowed_ceiling: string[];
  cloud_configurable: boolean;
  cloud_model: string;
  cloud_base_url: string;
  /** Whether an API key is set. The key itself is never sent to the browser. */
  cloud_key_present: boolean;
  model_light: string;
  model_heavy: string;
  ollama_host: string;
  ollama_connected: boolean;
  categories: string[];
}

export interface ProposedAction {
  id: number;
  type: string;
  targetId: string;
  payload: Record<string, unknown>;
  status: string;
  rationale: string;
  createdTs: number;
}

/** One retrieved email behind an answer. `cited` = the model actually referenced it. */
export interface AskSource {
  n: number;
  messageId: string;
  sender: string;
  subject: string;
  category: string;
  ts: number;
  distance: number;
  cited: boolean;
}

export interface AskResult {
  question: string;
  answer: string;
  sources: AskSource[];
}

/** Progress of the single background job (sync / enrichment). */
export interface JobStatus {
  state: "idle" | "running" | "done" | "error";
  kind: "sync" | "process" | null;
  phase: string;
  done: number;
  total: number;
  error: string | null;
}

/** FastAPI puts the useful sentence in `detail`; without this the UI would surface
 *  "400 /api/actions" instead of "…is an unattended mailbox — a reply would bounce." */
async function errorText(res: Response, path: string): Promise<string> {
  try {
    const d = (await res.json()) as { detail?: unknown };
    if (typeof d?.detail === "string" && d.detail) return d.detail;
  } catch {
    // Non-JSON error body (a proxy page, a crash): fall through to the status line.
  }
  return `${res.status} ${path}`;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(await errorText(res, path));
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await errorText(res, path));
  return res.json() as Promise<T>;
}

export const api = {
  messages: (params: { prio?: string | null; cat?: string | null; q?: string; limit?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.prio) qs.set("prio", params.prio);
    if (params.cat) qs.set("cat", params.cat);
    if (params.q) qs.set("q", params.q);
    qs.set("limit", String(params.limit ?? INBOX_LIMIT));
    return get<{ messages: Message[] }>(`/api/messages?${qs}`).then((d) => d.messages);
  },
  message: (id: string, images = false) =>
    get<MessageDetail>(`/api/messages/${id}${images ? "?images=true" : ""}`),
  stats: () => get<Stats>("/api/stats"),
  settings: () => get<AppSettings>("/api/settings"),
  actions: () => get<{ actions: ProposedAction[] }>("/api/actions").then((d) => d.actions),
  // These go through post(), not a bare fetch: a bare fetch resolves on a 4xx and hands
  // back {detail: "..."} as though it succeeded, so a refusal would look like a success
  // and the caller's error handling would never run.
  propose: (body: {
    type: string;
    target_id: string;
    payload?: Record<string, unknown>;
    rationale?: string;
  }) => post<{ id: number; status: string }>("/api/actions", body),
  decide: (id: number, approve: boolean) =>
    post<{ id: number; status: string }>(`/api/actions/${id}/decide?approve=${approve}`),

  // --- inbox draft composer. Generate and revise persist nothing; only save writes.
  draft: (targetId: string) => post<{ body: string }>("/api/draft", { target_id: targetId }),
  reviseDraft: (targetId: string, draft: string, feedback: string) =>
    post<{ body: string }>("/api/draft/revise", {
      target_id: targetId, draft, feedback,
    }),
  saveDraft: (targetId: string, body: string) =>
    post<{ actionId: number; draftId: string; to: string }>("/api/draft/save", {
      target_id: targetId, body,
    }),
  startSync: (body: { full?: boolean; max_messages?: number | null; process?: boolean } = {}) =>
    post<JobStatus>("/api/sync", body),
  startProcess: (body: { all?: boolean; limit?: number | null } = {}) =>
    post<JobStatus>("/api/process", body),
  job: () => get<JobStatus>("/api/job"),
  startIndex: (body: { rebuild?: boolean; limit?: number | null } = {}) =>
    post<JobStatus>("/api/index", body),
  ask: (question: string, k?: number) => post<AskResult>("/api/ask", { question, k }),
  saveSettings: (patch: { cloud_enabled?: boolean; cloud_allowed_tasks?: string[] }) =>
    fetch(`${BASE}/api/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }).then((r) => {
      if (!r.ok) throw new Error(`${r.status} PUT /api/settings`);
      return r.json() as Promise<AppSettings>;
    }),
};
