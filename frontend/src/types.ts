import type { AppSettings, Message, MessageDetail, ProposedAction, Stats } from "./api";

export type Screen = "inbox" | "digest" | "ask" | "queue" | "settings";

/** Everything the screens need from the app shell. */
export interface SharedProps {
  messages: Message[]; // filtered + visible
  live: Message[]; // unarchived, unfiltered
  stats: Stats | null;
  settings: AppSettings | null;
  proposals: ProposedAction[];
  sel: MessageDetail | null;
  selId: string | null;
  hover: string | null;
  archiving: string | null;
  loading: boolean;
  narrow: boolean;
  selOut: boolean;
  pendCount: number;
  prioFilter: string | null;
  catFilter: string | null;
  setHover: (id: string | null) => void;
  select: (id: string) => void;
  archive: (id: string) => void;
  propose: (type: string, targetId: string, rationale: string) => Promise<void>;
  resolve: (id: number, ok: boolean) => Promise<void>;
  goScreen: (s: Screen) => void;
  flash: (text: string, actionLabel?: string, act?: () => void) => void;
  setPrioFilter: (v: string | null) => void;
  setCatFilter: (v: string | null) => void;
  clearFilter: () => void;
  back: () => void;
  reloadSettings: () => Promise<void>;
}
