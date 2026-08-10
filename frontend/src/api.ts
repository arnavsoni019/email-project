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
  cloud_enabled: boolean;
  cloud_allowed_tasks: string[];
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

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
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
  message: (id: string) => get<MessageDetail>(`/api/messages/${id}`),
  stats: () => get<Stats>("/api/stats"),
  settings: () => get<AppSettings>("/api/settings"),
  actions: () => get<{ actions: ProposedAction[] }>("/api/actions").then((d) => d.actions),
  propose: (body: {
    type: string;
    target_id: string;
    payload?: Record<string, unknown>;
    rationale?: string;
  }) =>
    fetch(`${BASE}/api/actions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => r.json()),
  decide: (id: number, approve: boolean) =>
    fetch(`${BASE}/api/actions/${id}/decide?approve=${approve}`, { method: "POST" }).then((r) =>
      r.json(),
    ),
  startSync: (body: { full?: boolean; max_messages?: number | null; process?: boolean } = {}) =>
    post<JobStatus>("/api/sync", body),
  startProcess: (body: { all?: boolean; limit?: number | null } = {}) =>
    post<JobStatus>("/api/process", body),
  job: () => get<JobStatus>("/api/job"),
  startIndex: (body: { rebuild?: boolean; limit?: number | null } = {}) =>
    post<JobStatus>("/api/index", body),
  ask: (question: string, k?: number) => post<AskResult>("/api/ask", { question, k }),
};
