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
import { catColor, glass } from "../ui";

const TASKS = [
  { id: "categorise", t: "Categorise", note: "sender + subject only" },
  { id: "summarise", t: "Summarise", note: "full email body" },
  { id: "triage", t: "Triage", note: "full email body" },
  { id: "draft", t: "Draft replies", note: "thread history" },
  { id: "ask", t: "Ask", note: "matched emails" },
];

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

  const toggleTask = (id: string) => {
    if (!ceiling.includes(id)) return; // outside the ceiling — server would reject anyway
    const next = allowed.includes(id) ? allowed.filter((x) => x !== id) : [...allowed, id];
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
          <div style={{ display: "flex", alignItems: "center", gap: "11px", padding: "9px 11px", borderRadius: "14px", background: cloudOn ? "var(--warn-w)" : "var(--s2)", border: `1px solid ${cloudOn ? "var(--warn-b)" : "var(--s4)"}` }}>
            <span style={{ width: "8px", height: "8px", borderRadius: "99px", flex: "none", background: cloudOn ? "var(--warn)" : "var(--ok)" }} />
            <span style={{ fontSize: "13px", fontWeight: 600 }}>
              {cloudOn ? "Cloud enabled" : "Off — everything runs on this machine"}
            </span>
            <button
              onClick={() => save({ cloud_enabled: !cloudOn })}
              disabled={!configurable || busy}
              title={configurable ? undefined : "Set CLOUD_ALLOWED_TASKS in .env to enable this switch"}
              aria-pressed={cloudOn}
              style={{ marginLeft: "auto", flex: "none", width: "40px", height: "22px", padding: "2px", borderRadius: "99px", border: `1px solid ${cloudOn ? "var(--warn-b)" : "var(--edge)"}`, background: cloudOn ? "var(--warn)" : "var(--s5)", cursor: configurable && !busy ? "pointer" : "not-allowed", opacity: configurable ? 1 : 0.45, transition: "background-color .18s ease" }}
            >
              <span style={{ display: "block", width: "16px", height: "16px", borderRadius: "99px", background: "var(--s1)", transform: cloudOn ? "translateX(18px)" : "translateX(0)", transition: "transform .18s cubic-bezier(.32,.72,0,1)" }} />
            </button>
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
                <button
                  key={t.id}
                  onClick={() => toggleTask(t.id)}
                  disabled={!reachable || !cloudOn || busy}
                  title={reachable ? undefined : `Not permitted by CLOUD_ALLOWED_TASKS in .env`}
                  style={{ display: "flex", alignItems: "center", gap: "10px", width: "100%", padding: "9px 11px", borderRadius: "13px", border: "none", background: "transparent", textAlign: "left", cursor: reachable && cloudOn && !busy ? "pointer" : "not-allowed", opacity: reachable ? 1 : 0.5 }}
                >
                  <span style={{ width: "17px", height: "17px", flex: "none", display: "grid", placeItems: "center", border: `1px solid ${on ? "var(--warn)" : "var(--edge)"}`, borderRadius: "6px", background: on ? "var(--warn)" : "var(--s4)", color: "var(--s9)" }}>
                    {on && <Icon id="ap-check" size={11} />}
                  </span>
                  <span style={{ minWidth: 0 }}>
                    <span style={{ display: "block", fontSize: "12.5px", fontWeight: 500 }}>{t.t}</span>
                    <span style={{ display: "block", fontSize: "11px", color: "var(--fg5)", marginTop: "2px" }}>{t.note}</span>
                  </span>
                  <span style={{ marginLeft: "auto", fontSize: "10.5px", fontWeight: 700, letterSpacing: ".09em", textTransform: "uppercase", color: on ? "var(--warn-t)" : "var(--ok-t)" }}>
                    {on ? "cloud" : "local"}
                  </span>
                </button>
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
