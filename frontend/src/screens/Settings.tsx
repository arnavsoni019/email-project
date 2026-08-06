/** Settings — privacy gate, models, categories, account.
 *
 *  The cloud gate is deliberately READ-ONLY here: it lives in .env / config.py and is
 *  enforced server-side by Settings.may_use_cloud(). A web page cannot flip it, which
 *  is the point — the privacy boundary is not reachable from the browser. */

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
  const { settings, stats } = p;
  const cloudOn = !!settings?.cloud_enabled;
  const allowed = settings?.cloud_allowed_tasks ?? [];

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
            <span style={{ marginLeft: "auto", fontSize: "10.5px", fontWeight: 700, letterSpacing: ".09em", textTransform: "uppercase", color: cloudOn ? "var(--warn-t)" : "var(--ok-t)" }}>
              {cloudOn ? "cloud" : "local"}
            </span>
          </div>

          <p style={{ margin: "12px 0 0", fontSize: "12px", lineHeight: 1.6, color: "var(--fg4)" }}>
            {cloudOn
              ? "Cloud models are allowed for the ticked tasks below. Everything else still runs locally."
              : "Every summary, category and answer is produced by a local model — no email text, header or attachment leaves this machine."}
          </p>

          <div style={{ marginTop: "14px", display: "flex", flexDirection: "column", gap: "2px" }}>
            {TASKS.map((t) => {
              const on = cloudOn && allowed.includes(t.id);
              return (
                <div key={t.id} style={{ display: "flex", alignItems: "center", gap: "10px", width: "100%", padding: "9px 11px", borderRadius: "13px" }}>
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
                </div>
              );
            })}
          </div>

          <div style={{ marginTop: "12px", padding: "11px 13px", borderRadius: "13px", background: "var(--s2)", border: "1px solid var(--s4)", display: "flex", gap: "9px" }}>
            <span style={{ color: "var(--fg5)", flex: "none", marginTop: "1px" }}><Icon id="ap-shield" size={13} /></span>
            <span style={{ fontSize: "11.5px", color: "var(--fg4)", lineHeight: 1.6 }}>
              This gate is read-only from the browser by design. It is set in{" "}
              <code style={{ fontSize: "11px", padding: "1px 5px", borderRadius: "6px", background: "var(--chip)" }}>.env</code>{" "}
              (<code style={{ fontSize: "11px", padding: "1px 5px", borderRadius: "6px", background: "var(--chip)" }}>CLOUD_ENABLED</code>,{" "}
              <code style={{ fontSize: "11px", padding: "1px 5px", borderRadius: "6px", background: "var(--chip)" }}>CLOUD_ALLOWED_TASKS</code>)
              and enforced server-side, so a web page can never widen it.
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
