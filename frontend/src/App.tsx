/** mailorg — Aurora Pro.
 *  Ported from design/email-lookup/mailorg - Aurora Pro.dc.html, wired to the local
 *  FastAPI backend. Style values are copied from the design; see ui.ts. */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Resizer, usePaneWidth } from "./Resizer";
import { Icon, Sprite } from "./Sprite";
import {
  api,
  type AppSettings,
  type JobStatus,
  type Message,
  type MessageDetail,
  type ProposedAction,
  type Stats,
} from "./api";
import {
  ACC, EASE, badgeStyle, catColor, catCountStyle, catLabelStyle, glass, iconBtn,
  navIconStyle, navStyle, prioLabelStyle, prioMark, sectionLabel, sideBtn,
} from "./ui";
import type { Screen, SharedProps } from "./types";
import { Inbox } from "./screens/Inbox";
import { Digest } from "./screens/Digest";
import { Ask } from "./screens/Ask";
import { Queue } from "./screens/Queue";
import { Settings } from "./screens/Settings";

const SCREEN_TITLE: Record<Screen, string> = {
  inbox: "Inbox", digest: "Digest", ask: "Ask",
  queue: "Proposed Actions", settings: "Settings",
};

const NAV: { id: Screen; icon: string; label: string }[] = [
  { id: "inbox", icon: "ap-inbox", label: "Inbox" },
  { id: "digest", icon: "ap-digest", label: "Digest" },
  { id: "ask", icon: "ap-ask", label: "Ask" },
  { id: "queue", icon: "ap-queue", label: "Proposed Actions" },
  { id: "settings", icon: "ap-settings", label: "Settings" },
];

export default function App() {
  // --- server data ---------------------------------------------------------
  const [messages, setMessages] = useState<Message[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [proposals, setProposals] = useState<ProposedAction[]>([]);
  const [detail, setDetail] = useState<MessageDetail | null>(null);

  // --- ui state (mirrors the design's component state) ---------------------
  const [screen, setScreen] = useState<Screen>("inbox");
  const [selId, setSelId] = useState<string | null>(null);
  const [archived, setArchived] = useState<string[]>([]);
  const [archiving, setArchiving] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [toast, setToast] = useState<{ text: string; actionLabel?: string; act?: () => void } | null>(null);
  const [narrow, setNarrow] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [theming, setTheming] = useState<string | undefined>(undefined);
  const [out, setOut] = useState(false);
  const [selOut, setSelOut] = useState(false);
  const [sidebar, setSidebar] = useState(true);
  // 234px is the design's width; the bounds keep the nav labels readable at one end
  // and stop the sidebar swallowing the list at the other.
  const { width: sidebarW, set: setSidebarW, reset: resetSidebarW } = usePaneWidth("sidebar", 234, 180, 420);
  const [draggingSidebar, setDraggingSidebar] = useState(false);
  const [prioFilter, setPrioFilter] = useState<string | null>(null);
  const [catFilter, setCatFilter] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [syncedAt, setSyncedAt] = useState<number | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [tick, setTick] = useState(0); // re-render so "4m ago" stays current

  const searchRef = useRef<HTMLInputElement | null>(null);
  const timers = useRef<Record<string, number>>({});
  const gKey = useRef<number | null>(null);
  const detailCache = useRef<Map<string, MessageDetail>>(new Map());
  // Refs mirror state so callbacks can compare without a setState updater (which
  // React StrictMode runs twice, double-firing timers and animation flags).
  const screenRef = useRef<Screen>("inbox");
  const selIdRef = useRef<string | null>(null);

  const setTimer = (k: string, fn: () => void, ms: number) => {
    if (timers.current[k]) clearTimeout(timers.current[k]);
    timers.current[k] = window.setTimeout(fn, ms);
  };

  // --- loading -------------------------------------------------------------
  const reload = useCallback(async () => {
    const [m, s, a] = await Promise.all([
      api.messages(),
      api.stats(),
      api.actions().catch(() => [] as ProposedAction[]),
    ]);
    setMessages(m);
    // The design lists categories busiest-first; keep that ordering.
    setStats({ ...s, categories: [...s.categories].sort((a1, b1) => b1.k - a1.k) });
    setProposals(a);
    setSyncedAt(Date.now());
    if (!selIdRef.current) {
      const first = m.find((x) => x.prio === "action")?.id ?? m[0]?.id ?? null;
      selIdRef.current = first;
      setSelId(first);
    }
  }, []);

  useEffect(() => {
    reload().catch(() => undefined);
    api.settings().then(setSettings).catch(() => undefined);
  }, [reload]);

  /** Load the selected message.
   *
   *  The reader only fades back in once BOTH the fade-out has finished and the new
   *  content has arrived — otherwise the pane briefly renders its empty state between
   *  messages, which reads as a flash. Previously-seen messages come from a cache so
   *  re-selection costs nothing but the fade. */
  useEffect(() => {
    if (!selId) { setDetail(null); setSelOut(false); return; }

    let cancelled = false;
    setSelOut(true);

    const cached = detailCache.current.get(selId);
    const fetched = cached
      ? Promise.resolve(cached)
      : api.message(selId).then((d) => { detailCache.current.set(d.id, d); return d; });
    const faded = new Promise<void>((r) => window.setTimeout(r, 100));

    Promise.all([fetched, faded])
      .then(([d]) => {
        if (cancelled) return;
        setDetail(d);
        requestAnimationFrame(() => { if (!cancelled) setSelOut(false); });
      })
      .catch(() => { if (!cancelled) setSelOut(false); });

    return () => { cancelled = true; };
  }, [selId]);

  useEffect(() => {
    const onResize = () => setNarrow(window.innerWidth < 1120);
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // Keep the "Xm ago" label on the sync button honest.
  useEffect(() => {
    const t = window.setInterval(() => setTick((n) => n + 1), 30_000);
    return () => clearInterval(t);
  }, []);

  const syncAgo = useMemo(() => {
    void tick;
    if (!syncedAt) return "never";
    const secs = Math.floor((Date.now() - syncedAt) / 1000);
    if (secs < 45) return "just now";
    if (secs < 3600) return `${Math.round(secs / 60)}m ago`;
    if (secs < 86400) return `${Math.round(secs / 3600)}h ago`;
    return `${Math.round(secs / 86400)}d ago`;
  }, [syncedAt, tick]);

  // While a job runs the "4m ago" slot shows live progress instead.
  const jobLabel = useMemo(() => {
    if (!job || job.state === "idle") return syncAgo;
    if (job.state === "error") return "failed";
    if (job.state === "done") return "just now";
    return job.total ? `${job.done}/${job.total}` : job.phase;
  }, [job, syncAgo]);

  // --- derived -------------------------------------------------------------
  const live = useMemo(
    () => messages.filter((e) => !archived.includes(e.id)),
    [messages, archived],
  );

  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return live
      .filter((e) => !prioFilter || e.prio === prioFilter)
      .filter((e) => !catFilter || e.cat === catFilter)
      .filter((e) => !needle || `${e.sender} ${e.subject} ${e.tldr}`.toLowerCase().includes(needle));
  }, [live, prioFilter, catFilter, q]);

  // Deliberately NOT keyed on selId: `detail` is only swapped in once the new message
  // has loaded, so holding the previous one during the fade avoids an empty-state flash.
  const sel = useMemo(
    () => (detail && !archived.includes(detail.id) ? detail : null),
    [detail, archived],
  );

  const pendCount = proposals.filter((p) => p.status === "proposed").length;

  // --- behaviour (timings copied from the design) --------------------------
  const flash = useCallback((text: string, actionLabel?: string, act?: () => void) => {
    setToast({ text, actionLabel, act });
    setTimer("toast", () => setToast(null), 4200);
  }, []);

  const goScreen = useCallback((id: Screen) => {
    if (id === screenRef.current) return;
    screenRef.current = id;
    setOut(true);
    setTimer("nav", () => {
      setScreen(id);
      requestAnimationFrame(() => setOut(false));
    }, 130);
  }, []);

  /** Highlight the row immediately (instant feedback); the reader cross-fades on its
   *  own in the load effect above. */
  const select = useCallback((id: string) => {
    if (id === selIdRef.current) return;
    selIdRef.current = id;
    setSelId(id);
    // Only rebuild the array when something actually changes — and keep unchanged rows
    // at the same object identity so the memoised rows skip re-rendering.
    setMessages((ms) =>
      ms.some((e) => e.id === id && e.unread)
        ? ms.map((e) => (e.id === id ? { ...e, unread: false } : e))
        : ms,
    );
  }, []);

  const archive = useCallback((id: string) => {
    setArchiving(id);
    setTimer(`arch-${id}`, () => {
      setArchived((cur) => cur.concat([id]));
      setArchiving(null);
      if (selIdRef.current === id) { selIdRef.current = null; setSelId(null); }
      flash("Archived", "Undo", () => {
        setArchived((cur) => cur.filter((x) => x !== id));
        selIdRef.current = id;
        setSelId(id);
        setToast(null);
      });
    }, 220);
  }, [flash]);

  // `payload` carries the action's parameters (e.g. which label). Without it the
  // executor has nothing to apply and has to guess from the message's category.
  const propose = useCallback(async (
    type: string, targetId: string, rationale: string, payload?: Record<string, unknown>,
  ) => {
    await api.propose({ type, target_id: targetId, rationale, payload });
    setProposals(await api.actions());
    flash(
      type === "draft" ? "Reply drafted — queued for approval" : "Proposed — queued for approval",
      "Review",
      () => { setToast(null); goScreen("queue"); },
    );
  }, [flash, goScreen]);

  const resolve = useCallback(async (id: number, ok: boolean) => {
    await api.decide(id, ok);
    setProposals(await api.actions());
    flash(ok ? "Approved — applies to Gmail in Phase 5" : "Rejected — it will not be proposed again");
  }, [flash]);

  const toggleTheme = useCallback(() => {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
    setTheming("1");
    setTimer("theme", () => setTheming(undefined), 260);
  }, []);

  // Re-fetch one message with remote images permitted. The cached copy has them
  // blocked, so the cache is refreshed rather than read. Deliberately per-message and
  // not persisted: consenting to one sender's tracking pixels is not consent for all.
  const loadImages = useCallback((id: string) => {
    api.message(id, true).then((d) => {
      detailCache.current.set(d.id, d);
      if (selIdRef.current === d.id) setDetail(d);
    }).catch(() => undefined);
  }, []);

  // Sync and enrichment run as a background job on the server (minutes, not
  // milliseconds), so this kicks it off and then polls /api/job for progress.
  const doSync = useCallback(async () => {
    setLoading(true);
    try {
      await api.startSync({ max_messages: 50, process: true });
    } catch {
      // 409 means a job is already running — join its progress rather than fail.
    }
    const poll = async () => {
      try {
        const j = await api.job();
        setJob(j);
        if (j.state === "running") {
          setTimer("job", poll, 1000);
          return;
        }
        await reload();
      } catch {
        /* server went away; stop polling rather than spin */
      }
      setLoading(false);
      setTimer("jobClear", () => setJob(null), 4000);
    };
    poll();
  }, [reload]);

  // --- keyboard (exact bindings from the design) ---------------------------
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName ?? "";
      const typing = tag === "INPUT" || tag === "TEXTAREA";
      if (e.key === "Escape") {
        if (typing) (e.target as HTMLElement).blur();
        setToast(null);
        return;
      }
      if (typing) return;
      if (e.key === "/") { e.preventDefault(); searchRef.current?.focus(); return; }
      if (gKey.current && Date.now() - gKey.current < 1200) {
        gKey.current = null;
        const m: Record<string, Screen> = {
          i: "inbox", d: "digest", a: "ask", p: "queue", s: "settings",
        };
        if (m[e.key]) { e.preventDefault(); goScreen(m[e.key]); return; }
      }
      if (e.key === "g") { gKey.current = Date.now(); return; }
      if (screen !== "inbox") return;
      if (e.key === "j" || e.key === "k") {
        e.preventDefault();
        const i = visible.findIndex((x) => x.id === selId);
        const next = e.key === "j"
          ? Math.min(visible.length - 1, i + 1)
          : Math.max(0, i < 0 ? 0 : i - 1);
        if (visible[next]) select(visible[next].id);
      }
      if (e.key === "e" && selId) { e.preventDefault(); archive(selId); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [screen, visible, selId, select, archive, goScreen]);

  // --- styles --------------------------------------------------------------
  const contentWrap: React.CSSProperties = {
    flex: 1, minHeight: 0, display: "flex", flexDirection: "column",
    opacity: out ? 0 : 1,
    transform: out ? "translateY(7px) scale(.995)" : "none",
    transition: `opacity .13s ${EASE},transform .26s ${EASE}`,
  };
  const topBar = glass({
    flex: "none", display: "flex", alignItems: "center",
    gap: "14px", padding: "9px 14px", borderRadius: "18px",
  });
  const cloudOn = !!settings?.cloud_enabled;
  const privacyDot: React.CSSProperties = {
    width: "7px", height: "7px", borderRadius: "99px", flex: "none",
    background: cloudOn ? "var(--warn)" : "var(--ok)",
    animation: `apSheen 3s ${EASE} infinite`,
  };
  const screenMeta =
    screen === "inbox" ? `${visible.length} conversations`
    : screen === "queue" ? `${pendCount} pending`
    : "";

  const shared: SharedProps = {
    messages: visible, live, stats, settings, proposals, sel, selId, hover, archiving,
    loading, narrow, selOut, pendCount, prioFilter, catFilter,
    setHover, select, archive, propose, resolve, goScreen, flash,
    setPrioFilter, setCatFilter,
    clearFilter: () => { setPrioFilter(null); setCatFilter(null); setQ(""); },
    back: () => { selIdRef.current = null; setSelId(null); },
    reloadSettings: () => api.settings().then(setSettings).then(() => undefined).catch(() => undefined),
    loadImages,
  };

  return (
    <div
      data-theme={theme}
      data-theming={theming}
      style={{ position: "relative", height: "100vh", overflow: "hidden", background: "var(--bg)", color: "var(--fg1)" }}
    >
      <div style={{ position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none", background: "var(--wash)" }} />
      <Sprite />

      {/* gap:0 because the Resizers supply the design's 10px inter-pane spacing */}
      <div style={{ position: "relative", zIndex: 1, height: "100%", display: "flex", gap: narrow ? "10px" : 0, padding: "10px" }}>
        {/* ---------- sidebar ---------- */}
        <aside
          style={glass({
            width: sidebar ? `${sidebarW}px` : "62px",
            flex: "none",
            overflow: "hidden",
            // Animate the collapse toggle, but not the drag — a transition during a
            // drag makes the pane lag the cursor and feel broken.
            transition: draggingSidebar ? "none" : `width .24s ${EASE}`,
          })}
        >
          <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
            <div style={{ padding: "15px 15px 12px", display: "flex", alignItems: "center", gap: "9px" }}>
              <span style={{ width: "27px", height: "27px", display: "grid", placeItems: "center", borderRadius: "9px", background: ACC, color: "var(--acc-on)", fontSize: "13px", fontWeight: 700, letterSpacing: "-.03em" }}>m</span>
              {sidebar && (
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: "13.5px", fontWeight: 700, letterSpacing: "-.025em", lineHeight: 1.1 }}>mailorg</div>
                  <div style={{ fontSize: "10.5px", color: "var(--fg5)", marginTop: "2px" }}>
                    {new Date().toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "long" })}
                  </div>
                </div>
              )}
              <button
                onClick={() => setSidebar((v) => !v)}
                title="Collapse"
                style={{ marginLeft: sidebar ? "auto" : 0, width: "24px", height: "24px", display: "grid", placeItems: "center", border: "none", background: "transparent", color: "var(--fg5)", borderRadius: "9px", cursor: "pointer", transform: sidebar ? "rotate(180deg)" : "none", transition: `transform .22s ${EASE}` }}
              >
                <Icon id="ap-chev-r" />
              </button>
            </div>

            {sidebar && (
              <div style={{ padding: "0 11px 11px" }}>
                <button
                  onClick={doSync}
                  style={{ display: "flex", alignItems: "center", gap: "8px", width: "100%", height: "32px", padding: "0 11px", border: "1px solid var(--s5)", borderRadius: "13px", background: "var(--s4)", color: "var(--fg2)", cursor: "pointer", transition: `background-color .16s ${EASE}` }}
                >
                  <span style={{ display: "grid", placeItems: "center", color: "var(--fg4)", animation: loading ? `apSheen 1.1s ${EASE} infinite` : "none" }}>
                    <Icon id="ap-sync" />
                  </span>
                  <span style={{ fontSize: "12.5px", fontWeight: 600 }}>Sync</span>
                  <span
                    style={{ marginLeft: "auto", fontSize: "11px", color: job?.state === "error" ? "var(--warn-t)" : "var(--fg5)", fontVariantNumeric: "tabular-nums" }}
                    title={job?.error ?? undefined}
                  >
                    {jobLabel}
                  </span>
                </button>
              </div>
            )}

            <nav style={{ padding: "0 11px", display: "flex", flexDirection: "column", gap: "3px" }}>
              {NAV.map((n) => {
                const on = screen === n.id;
                return (
                  <button key={n.id} onClick={() => goScreen(n.id)} title={n.label} style={navStyle(on, sidebar)}>
                    <span style={navIconStyle(on)}><Icon id={n.icon} size={15} /></span>
                    {sidebar && <span>{n.label}</span>}
                    {n.id === "queue" && pendCount > 0 && <span style={badgeStyle}>{pendCount}</span>}
                  </button>
                );
              })}
            </nav>

            {sidebar && (
              <>
                <div style={{ flex: 1, overflowY: "auto", padding: "16px 11px 10px", minHeight: 0 }}>
                  <div style={sectionLabel}>Priority</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                    {(stats?.priorities ?? []).map((p) => {
                      const on = prioFilter === p.id;
                      return (
                        <button
                          key={p.id}
                          onClick={() => { setPrioFilter(on ? null : p.id); setCatFilter(null); goScreen("inbox"); }}
                          style={sideBtn(on)}
                        >
                          <span style={prioMark(p.id)} />
                          <span style={prioLabelStyle(p.id, on)}>{p.t}</span>
                          <span style={{ marginLeft: "auto", fontSize: "11px", color: "var(--fg5)", fontVariantNumeric: "tabular-nums" }}>{p.k}</span>
                        </button>
                      );
                    })}
                  </div>

                  <div style={{ height: "1px", background: "var(--rule)", margin: "13px 5px" }} />
                  <div style={sectionLabel}>Categories</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                    {(stats?.categories ?? []).map((c) => {
                      const on = catFilter === c.n;
                      return (
                        <button
                          key={c.n}
                          onClick={() => { setCatFilter(on ? null : c.n); setPrioFilter(null); goScreen("inbox"); }}
                          style={sideBtn(on)}
                        >
                          <span style={{ width: "7px", height: "7px", borderRadius: "99px", flex: "none", background: catColor(c.n), opacity: c.k ? 1 : 0.4 }} />
                          <span style={catLabelStyle(c.k, on)}>{c.n}</span>
                          <span style={catCountStyle(c.k)}>{c.k}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div style={{ flex: "none", padding: "11px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "8px 11px", borderRadius: "14px", background: cloudOn ? "var(--warn-w)" : "var(--s4)", border: `1px solid ${cloudOn ? "var(--warn-b)" : "var(--s5)"}`, color: cloudOn ? "var(--warn-fg)" : "var(--fg2)", transition: `background-color .16s ${EASE},border-color .16s` }}>
                    <span style={privacyDot} />
                    <span style={{ fontSize: "11.5px", fontWeight: 600 }}>{cloudOn ? "Cloud enabled" : "100% Local"}</span>
                    <span style={{ marginLeft: "auto", opacity: 0.5, display: "grid", placeItems: "center" }}>
                      <Icon id="ap-shield" />
                    </span>
                  </div>
                  <button
                    onClick={() => goScreen("settings")}
                    style={{ width: "100%", marginTop: "7px", padding: "4px 5px", textAlign: "left", fontSize: "11px", color: "var(--fg5)", background: "transparent", border: "none", cursor: "pointer", borderRadius: "8px" }}
                  >
                    Privacy &amp; model settings →
                  </button>
                </div>
              </>
            )}
          </div>
        </aside>

        {/* Only offered when the sidebar is expanded; there is nothing to resize at
            62px, and on narrow screens the panes stack instead. */}
        {!narrow && sidebar && (
          <Resizer
            label="Sidebar width"
            width={sidebarW}
            onResize={setSidebarW}
            onReset={resetSidebarW}
            onActiveChange={setDraggingSidebar}
          />
        )}
        {/* Collapsed: no handle, but the 10px the container no longer supplies. */}
        {!narrow && !sidebar && <div style={{ flex: "none", width: "10px" }} />}

        {/* ---------- main ---------- */}
        <main style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: "10px", minHeight: 0 }}>
          <div style={topBar}>
            <div style={{ display: "flex", alignItems: "baseline", gap: "9px", minWidth: 0 }}>
              <span style={{ fontSize: "14px", fontWeight: 700, letterSpacing: "-.025em" }}>{SCREEN_TITLE[screen]}</span>
              <span style={{ fontSize: "11.5px", color: "var(--fg5)", fontVariantNumeric: "tabular-nums" }}>{screenMeta}</span>
            </div>
            <div style={{ flex: 1, display: "flex", justifyContent: "center", minWidth: 0 }}>
              <div style={{ position: "relative", width: "100%", maxWidth: "360px", display: "flex", alignItems: "center" }}>
                <span style={{ position: "absolute", left: "11px", display: "grid", placeItems: "center", color: "var(--fg5)", pointerEvents: "none" }}>
                  <Icon id="ap-search" />
                </span>
                <input
                  ref={searchRef}
                  value={q}
                  onChange={(e) => { setQ(e.target.value); goScreen("inbox"); }}
                  placeholder="Search all mail"
                  style={{ width: "100%", height: "30px", padding: "0 44px 0 32px", fontSize: "12.5px", border: "1px solid var(--s5)", borderRadius: "13px", background: "var(--s3)", outline: "none", transition: `border-color .16s ${EASE},background-color .16s` }}
                />
                <span style={{ position: "absolute", right: "9px", fontSize: "10.5px", fontWeight: 600, padding: "1px 6px", borderRadius: "8px", background: "var(--chip)", color: "var(--fg5)", pointerEvents: "none" }}>/</span>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", justifyContent: "flex-end", minWidth: 0 }}>
              {loading && <span style={{ fontSize: "11px", fontWeight: 600, letterSpacing: ".06em", textTransform: "uppercase", color: "var(--fg5)" }}>syncing</span>}
              <span style={{ display: "flex", alignItems: "center", gap: "6px", padding: "5px 11px", borderRadius: "12px", background: "var(--s3)", border: "1px solid var(--s4)", fontSize: "11.5px", fontWeight: 600, color: "var(--fg3)", whiteSpace: "nowrap" }}>
                <span style={privacyDot} />
                {cloudOn ? "Cloud on" : "On-device"}
              </span>
              <button
                onClick={toggleTheme}
                title={theme === "dark" ? "Switch to light" : "Switch to dark"}
                style={{ width: "28px", height: "28px", flex: "none", display: "grid", placeItems: "center", border: "1px solid var(--s4)", background: "var(--s3)", color: "var(--fg4)", borderRadius: "11px", cursor: "pointer", transition: `background-color .16s ${EASE}` }}
              >
                <Icon id={theme === "dark" ? "ap-sun" : "ap-moon"} size={14} />
              </button>
            </div>
          </div>

          <div style={contentWrap}>
            {screen === "inbox" && <Inbox {...shared} />}
            {screen === "digest" && <Digest {...shared} />}
            {screen === "ask" && <Ask {...shared} />}
            {screen === "queue" && <Queue {...shared} />}
            {screen === "settings" && <Settings {...shared} />}
          </div>
        </main>
      </div>

      {/* ---------- toast ---------- */}
      {toast && (
        <div style={{ position: "fixed", left: "50%", bottom: "22px", transform: "translateX(-50%)", zIndex: 40 }}>
          <div style={glass({ display: "flex", alignItems: "center", gap: "12px", padding: "10px 14px", borderRadius: "15px", background: "var(--s7)" })}>
            <span style={{ fontSize: "12.5px", fontWeight: 500 }}>{toast.text}</span>
            {toast.actionLabel && (
              <button
                onClick={toast.act}
                style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "12px", fontWeight: 600, color: ACC, background: "transparent", border: "none", cursor: "pointer" }}
              >
                <Icon id="ap-undo" size={12} />
                {toast.actionLabel}
              </button>
            )}
            <button onClick={() => setToast(null)} style={{ ...iconBtn, width: "22px", height: "22px" }} title="Dismiss">
              <Icon id="ap-x" size={11} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
