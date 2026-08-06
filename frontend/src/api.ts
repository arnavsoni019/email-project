/** Client for the local mailorg FastAPI backend. Nothing here talks to the network
 *  beyond localhost — the backend is the only thing that touches Gmail or a model. */

const BASE = "http://localhost:8000";

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

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  messages: (params: { prio?: string | null; cat?: string | null; q?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.prio) qs.set("prio", params.prio);
    if (params.cat) qs.set("cat", params.cat);
    if (params.q) qs.set("q", params.q);
    const suffix = qs.toString() ? `?${qs}` : "";
    return get<{ messages: Message[] }>(`/api/messages${suffix}`).then((d) => d.messages);
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
};
