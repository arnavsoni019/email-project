/** Settings — privacy gate, models, categories, account.
 *
 *  The cloud switch is live, but it can only ever move WITHIN the ceiling set in .env
 *  (CLOUD_ALLOWED_TASKS). The server intersects on both write and read, so a task the
 *  machine's owner never permitted cannot be enabled from a browser — the boundary
 *  stays server-side while the day-to-day choice sits where the user can reach it. */

import { useState } from "react";
import { api } from "../api";
import { Icon } from "../Sprite";
import type { SharedProps } from "../types";
import { EASE, catColor, glass } from "../ui";

// One entry per task name passed to get_llm(task) in the backend. A task missing here
// is still cloud-eligible if .env permits it, but has no switch — so the screen would
// under-report where text goes. Keep this list in step with the get_llm call sites.
const TASKS = [
  { id: "categorise", t: "Categorise", note: "sender + subject only" },
  { id: "summarise", t: "Summarise", note: "full email body" },
  { id: "triage", t: "Triage", note: "full email body" },
  { id: "propose", t: "Action rationales", note: "sender + subject + category" },
  { id: "draft", t: "Draft replies", note: "thread history" },
  { id: "ask", t: "Ask", note: "matched emails" },
];

/** Two-state segmented control: Local | Cloud.
 *
 *  A solid block slides between two halves: green on Local, amber on Cloud, with dark
 *  ink on top. Flat fill, tight radius, one short transition — no glow, no bounce, no
 *  translucent surface. The state is a colour you can name from across the room, and
 *  the label says where the text goes rather than making "on" mean something. */
function Segmented({ value, onChange, disabled, small, title }: {
  value: "local" | "cloud";
  onChange: (v: "local" | "cloud") => void;
  disabled?: boolean;
  small?: boolean;
  title?: string;
}) {
  const cloud = value === "cloud";
  const radius = small ? "7px" : "8px";

  const seg = (id: "local" | "cloud", label: string, icon: string) => {
    const on = value === id;
    return (
      <button
        className={`seg-btn${on ? "" : " seg-btn--off"}`}
        onClick={() => !disabled && onChange(id)}
        disabled={disabled}
        aria-pressed={on}
        style={{
          // Above the thumb, which is absolutely positioned behind both halves.
          position: "relative", zIndex: 1,
          display: "flex", alignItems: "center", justifyContent: "center",
          gap: small ? "5px" : "6px",
          padding: small ? "3.5px 11px" : "6px 15px",
          border: "none", background: "transparent", borderRadius: radius,
          // Dark ink on the solid fill; muted grey when flat. No tinted text — the fill
          // carries the colour, so the label stays plain.
          color: on ? "var(--seg-ink)" : "var(--fg4)",
          fontSize: small ? "10.5px" : "12px", fontWeight: on ? 650 : 500,
          letterSpacing: "-.005em",
          cursor: disabled ? "not-allowed" : "pointer",
          whiteSpace: "nowrap",
        }}
      >
        <Icon id={icon} size={small ? 10 : 12} style={{ flex: "none" }} />
        {label}
      </button>
    );
  };

  return (
    <div title={title} style={{
      // Equal columns are what make translateX(100%) land exactly on the other half.
      position: "relative", display: "inline-grid", gridTemplateColumns: "1fr 1fr",
      flex: "none", padding: "2px", borderRadius: small ? "9px" : "10px",
      background: "var(--s3)", border: "1px solid var(--edge)",
      opacity: disabled ? 0.45 : 1,
      transition: `opacity .18s ${EASE}`,
    }}>
      {/* A single solid block that slides. The fill colour crossfades green -> amber as
          it travels, so the colour change and the movement are one gesture. */}
      <span
        aria-hidden
        className="seg-thumb"
        style={{
          position: "absolute", top: "2px", bottom: "2px", left: "2px",
          width: "calc(50% - 2px)", borderRadius: radius,
          background: cloud ? "var(--warn)" : "var(--ok)",
          transform: cloud ? "translateX(100%)" : "translateX(0)",
          transition: `transform .22s ${EASE},background-color .22s ${EASE}`,
        }}
      />
      {seg("local", "Local", "ap-monitor")}
      {seg("cloud", "Cloud", "ap-cloud")}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={glass({ marginTop: "9px", overflow: "hidden" })}>
      <div style={{ padding: "15px 17px 4px", fontSize: "13.5px", fontWeight: 600, letterSpacing: "-.015em" }}>
        {title}
      </div>
      <div style={{ padding: "8px 17px 16px" }}>{children}</div>
    </div>
  );
}

export function Settings(p: SharedProps) {
  const { settings, stats, reloadSettings } = p;
  const [busy, setBusy] = useState(false);
  const cloudOn = !!settings?.cloud_enabled;
  const allowed = settings?.cloud_allowed_tasks ?? [];
  // What .env permits the switch to reach. Empty = the switch is inert by design.
  const ceiling = settings?.cloud_allowed_ceiling ?? [];
  const configurable = !!settings?.cloud_configurable;
  const keyPresent = !!settings?.cloud_key_present;

  const save = async (patch: { cloud_enabled?: boolean; cloud_allowed_tasks?: string[] }) => {
    setBusy(true);
    try {
      await api.saveSettings(patch);
      await reloadSettings();
    } finally {
      setBusy(false);
    }
  };

  // Explicit target state rather than a toggle: the segmented control says which side
  // was clicked, so clicking "Local" on an already-local row is a no-op instead of
  // silently flipping it to cloud.
  const setTask = (id: string, cloud: boolean) => {
    if (!ceiling.includes(id)) return; // outside the ceiling — server would reject anyway
    const next = cloud
      ? Array.from(new Set([...allowed, id]))
      : allowed.filter((x) => x !== id);
    save({ cloud_allowed_tasks: next });
  };

  return (
    <div style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
      <div style={{ maxWidth: "720px", margin: "0 auto", padding: "2px 4px 24px" }}>
        <div style={{ padding: "6px 6px 8px" }}>
          <div style={{ fontSize: "11.5px", fontWeight: 700, letterSpacing: ".1em", textTransform: "uppercase", color: "var(--fg5)" }}>
            Privacy &amp; models
          </div>
          <h1 style={{ margin: "9px 0 0", fontSize: "22px", fontWeight: 600, letterSpacing: "-.03em" }}>Settings</h1>
        </div>

        {/* privacy */}
        <Section title="Cloud AI">
          {/* Surface stays neutral in both states — the dot and the control carry the
              signal, so turning cloud on no longer floods the panel with one colour. */}
          <div style={{ display: "flex", alignItems: "center", gap: "11px", padding: "10px 12px", borderRadius: "14px", background: "var(--s2)", border: "1px solid var(--s4)" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "99px", flex: "none", background: cloudOn ? "var(--warn)" : "var(--ok)", transition: "background-color .16s ease" }} />
            <span style={{ fontSize: "13px", fontWeight: 600 }}>
              {cloudOn ? "Cloud enabled" : "Off — everything runs on this machine"}
            </span>
            <div style={{ marginLeft: "auto" }}>
              <Segmented
                value={cloudOn ? "cloud" : "local"}
                onChange={(v) => save({ cloud_enabled: v === "cloud" })}
                disabled={!configurable || busy}
                title={configurable ? undefined : "Set CLOUD_ALLOWED_TASKS in .env to enable this switch"}
              />
            </div>
          </div>

          {cloudOn && !keyPresent && (
            <div style={{ marginTop: "10px", padding: "9px 12px", borderRadius: "12px", background: "var(--warn-w)", border: "1px solid var(--warn-b)", fontSize: "11.5px", color: "var(--warn-fg)", lineHeight: 1.55 }}>
              No API key configured — cloud tasks will fail rather than silently fall back
              to local, so you always know where text went. Set <code>CLOUD_API_KEY</code> in{" "}
              <code>.env</code>.
            </div>
          )}

          <p style={{ margin: "12px 0 0", fontSize: "12px", lineHeight: 1.6, color: "var(--fg4)" }}>
            {cloudOn
              ? "Cloud models are allowed for the ticked tasks below. Everything else still runs locally."
              : "Every summary, category and answer is produced by a local model — no email text, header or attachment leaves this machine."}
          </p>

          <div style={{ marginTop: "14px", display: "flex", flexDirection: "column", gap: "2px" }}>
            {TASKS.map((t) => {
              const on = cloudOn && allowed.includes(t.id);
              // Outside the .env ceiling: shown, but permanently local so the user can
              // see the full surface rather than wondering what is missing.
              const reachable = ceiling.includes(t.id);
              return (
                // A div, not a button: the row now contains its own buttons, and
                // nesting interactive elements breaks both HTML and keyboard nav.
                <div
                  key={t.id}
                  title={reachable ? undefined : `Not permitted by CLOUD_ALLOWED_TASKS in .env`}
                  style={{ display: "flex", alignItems: "center", gap: "10px", width: "100%", padding: "7px 11px", borderRadius: "13px", opacity: reachable ? 1 : 0.5 }}
                >
                  <span style={{ minWidth: 0 }}>
                    <span style={{ display: "block", fontSize: "12.5px", fontWeight: 500 }}>{t.t}</span>
                    <span style={{ display: "block", fontSize: "11px", color: "var(--fg5)", marginTop: "2px" }}>{t.note}</span>
                  </span>
                  <div style={{ marginLeft: "auto" }}>
                    <Segmented
                      small
                      value={on ? "cloud" : "local"}
                      onChange={(v) => setTask(t.id, v === "cloud")}
                      disabled={!reachable || !cloudOn || busy}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ marginTop: "12px", padding: "11px 13px", borderRadius: "13px", background: "var(--s2)", border: "1px solid var(--s4)", display: "flex", gap: "9px" }}>
            <span style={{ color: "var(--fg5)", flex: "none", marginTop: "1px" }}><Icon id="ap-shield" size={13} /></span>
            <span style={{ fontSize: "11.5px", color: "var(--fg4)", lineHeight: 1.6 }}>
              These switches can only move <em>within</em> the ceiling set in{" "}
              <code style={{ fontSize: "11px", padding: "1px 5px", borderRadius: "6px", background: "var(--chip)" }}>.env</code>{" "}
              (<code style={{ fontSize: "11px", padding: "1px 5px", borderRadius: "6px", background: "var(--chip)" }}>CLOUD_ALLOWED_TASKS</code>).
              The server intersects with it on every write and every read, so a task you
              did not permit there can never be enabled from a browser.
              {ceiling.length === 0
                ? " Nothing is permitted yet, so these controls are inert."
                : ` Permitted: ${ceiling.join(", ")}.`}
              {settings?.cloud_model && (
                <>
                  {" "}Cloud requests would go to{" "}
                  <code style={{ fontSize: "11px", padding: "1px 5px", borderRadius: "6px", background: "var(--chip)" }}>{settings.cloud_model}</code>{" "}
                  via {new URL(settings.cloud_base_url ?? "https://openrouter.ai").host}.
                </>
              )}
            </span>
          </div>
        </Section>

        {/* models */}
        <Section title="Local models">
          <div style={{ display: "flex", alignItems: "center", gap: "9px", marginBottom: "12px" }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "99px", background: settings?.ollama_connected ? "var(--ok)" : "var(--warn)" }} />
            <span style={{ fontSize: "12.5px", fontWeight: 600 }}>
              {settings?.ollama_connected ? "Ollama connected" : "Ollama unreachable"}
            </span>
            <span style={{ marginLeft: "auto", fontSize: "11px", color: "var(--fg5)" }}>{settings?.ollama_host}</span>
          </div>
          {[
            { label: "Light · resident · bulk work", value: settings?.model_light },
            { label: "Heavy · on demand · detail extraction", value: settings?.model_heavy },
          ].map((m) => (
            <div key={m.label} style={{ display: "flex", alignItems: "center", gap: "10px", padding: "11px 13px", borderRadius: "14px", background: "var(--s2)", border: "1px solid var(--s4)", marginBottom: "5px" }}>
              <span style={{ fontSize: "12.5px", fontWeight: 600, fontFamily: "ui-monospace,monospace" }}>{m.value}</span>
              <span style={{ marginLeft: "auto", fontSize: "11px", color: "var(--fg5)" }}>{m.label}</span>
            </div>
          ))}
        </Section>

        {/* categories */}
        <Section title="Categories">
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
            {(stats?.categories ?? []).map((c) => (
              <span key={c.n} style={{ display: "inline-flex", alignItems: "center", gap: "7px", padding: "6px 12px", borderRadius: "12px", background: "var(--s2)", border: "1px solid var(--s4)", fontSize: "12px" }}>
                <span style={{ width: "7px", height: "7px", borderRadius: "99px", background: catColor(c.n) }} />
                {c.n}
                <span style={{ color: "var(--fg5)", fontVariantNumeric: "tabular-nums" }}>{c.k}</span>
              </span>
            ))}
          </div>
        </Section>

        {/* account */}
        <Section title="Account">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontSize: "12.5px", fontWeight: 600 }}>{stats?.account || "not synced"}</span>
            <span style={{ marginLeft: "auto", fontSize: "11px", color: "var(--fg5)", fontVariantNumeric: "tabular-nums" }}>
              {stats?.total ?? 0} messages · {stats?.unprocessed ?? 0} unprocessed
            </span>
          </div>
          <div style={{ marginTop: "10px", fontSize: "11.5px", color: "var(--fg5)", lineHeight: 1.6 }}>
            Gmail access is read-only (<code style={{ fontSize: "11px", padding: "1px 5px", borderRadius: "6px", background: "var(--chip)" }}>gmail.readonly</code>).
            Sync and processing run from the CLI: <code style={{ fontSize: "11px", padding: "1px 5px", borderRadius: "6px", background: "var(--chip)" }}>python -m mailorg.sync</code> then{" "}
            <code style={{ fontSize: "11px", padding: "1px 5px", borderRadius: "6px", background: "var(--chip)" }}>python -m mailorg.pipelines.run</code>.
          </div>
        </Section>
      </div>
    </div>
  );
}
