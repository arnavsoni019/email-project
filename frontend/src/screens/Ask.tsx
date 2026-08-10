/** Ask — natural-language question over the inbox.
 *
 *  Real semantic search (Phase 4): the question is embedded and matched against the
 *  ChromaDB index, then a local model answers from the retrieved emails and cites them.
 *  Sources are shown so every claim can be checked against the email it came from. */

import { useState } from "react";
import { Icon } from "../Sprite";
import { api, type AskResult } from "../api";
import type { SharedProps } from "../types";
import { EASE, btn, catColor, glass } from "../ui";

const CHIPS = [
  "anything I need to reply to?",
  "any job or internship opportunities?",
  "did anything happen with my account security?",
  "what are my recent orders?",
];

export function Ask(p: SharedProps) {
  const { live, goScreen, select } = p;
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<AskResult | null>(null);

  const run = async (raw: string) => {
    const query = raw.trim();
    if (!query) return;
    setBusy(true);
    setAnswer(null);
    setError(null);
    try {
      setAnswer(await api.ask(query));
    } catch {
      // The most likely cause is an empty index, so point at the fix rather than
      // showing a bare status code.
      setError("Couldn't reach the local model. Is the index built, and Ollama running?");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
      <div style={{ maxWidth: "720px", margin: "0 auto", padding: "2px 4px 24px" }}>
        <div style={glass({ padding: "17px 18px" })}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
            <span style={{ color: "var(--acc-t)", display: "grid", placeItems: "center" }}>
              <Icon id="ap-ask" />
            </span>
            <span style={{ fontSize: "13.5px", fontWeight: 600, letterSpacing: "-.015em" }}>
              Ask your inbox
            </span>
            <span style={{ marginLeft: "auto", fontSize: "11px", color: "var(--fg5)" }}>
              {live.length} emails · on-device
            </span>
          </div>

          <form
            onSubmit={(e) => { e.preventDefault(); run(q); }}
            style={{ display: "flex", gap: "8px" }}
          >
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Ask anything about your mail…"
              style={{ flex: 1, height: "36px", padding: "0 13px", borderRadius: "14px", border: "1px solid var(--s5)", background: "var(--s4)", fontSize: "13.5px", outline: "none", transition: `border-color .16s ${EASE},background-color .16s` }}
            />
            <button type="submit" style={btn("primary")}>Ask</button>
          </form>

          <div style={{ display: "flex", flexWrap: "wrap", gap: "5px", marginTop: "12px" }}>
            {CHIPS.map((c) => (
              <button
                key={c}
                onClick={() => { setQ(c); run(c); }}
                style={{ padding: "5px 11px", borderRadius: "12px", border: "1px solid var(--s5)", background: "var(--s3)", color: "var(--fg3)", fontSize: "11.5px", cursor: "pointer", transition: `background-color .16s ${EASE}` }}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {busy && (
          <div style={glass({ marginTop: "9px", padding: "17px 18px", animation: "apSkel 1.4s ease-in-out infinite" })}>
            <div style={{ height: "11px", width: "70%", borderRadius: "6px", background: "var(--rule)" }} />
            <div style={{ height: "11px", width: "45%", borderRadius: "6px", background: "var(--rule)", marginTop: "9px" }} />
          </div>
        )}

        {error && !busy && (
          <div style={glass({ marginTop: "9px", padding: "15px 18px", fontSize: "13px", color: "var(--warn-t)" })}>
            {error}
          </div>
        )}

        {answer && !busy && (
          <div style={glass({ marginTop: "9px", padding: "17px 18px" })}>
            <div style={{ fontSize: "11px", fontWeight: 700, letterSpacing: ".07em", textTransform: "uppercase", color: "var(--fg5)" }}>
              {answer.question}
            </div>
            <p style={{ margin: "10px 0 0", fontSize: "14px", lineHeight: 1.6, color: "var(--fg1)", textWrap: "pretty", whiteSpace: "pre-wrap" }}>
              {answer.answer}
            </p>

            {answer.sources.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "5px", marginTop: "13px" }}>
                {/* Cited sources first: those are the ones the answer actually rests on. */}
                {[...answer.sources].sort((a, b) => Number(b.cited) - Number(a.cited)).map((s) => (
                  <button
                    key={s.messageId}
                    onClick={() => { goScreen("inbox"); select(s.messageId); }}
                    title={`distance ${s.distance}`}
                    style={{ display: "flex", alignItems: "center", gap: "9px", padding: "10px 13px", borderRadius: "15px", background: s.cited ? "var(--s2)" : "transparent", border: `1px solid ${s.cited ? "var(--acc-b1)" : "var(--s4)"}`, cursor: "pointer", textAlign: "left", opacity: s.cited ? 1 : 0.55, transition: `background-color .16s ${EASE}` }}
                  >
                    <span style={{ fontSize: "10.5px", fontWeight: 700, color: s.cited ? "var(--acc-t)" : "var(--fg5)", fontVariantNumeric: "tabular-nums", flex: "none" }}>
                      [{s.n}]
                    </span>
                    <span style={{ width: "6px", height: "6px", borderRadius: "99px", flex: "none", background: catColor(s.category) }} />
                    <span style={{ fontSize: "12px", fontWeight: 600, flex: "none" }}>{s.sender}</span>
                    <span style={{ fontSize: "12px", color: "var(--fg4)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {s.subject}
                    </span>
                  </button>
                ))}
              </div>
            )}

            <div style={{ marginTop: "13px", paddingTop: "11px", borderTop: "1px solid var(--rule)", fontSize: "11px", color: "var(--fg5)", lineHeight: 1.55 }}>
              Semantic search over {live.length} emails — embedded with nomic-embed-text and
              answered locally. Highlighted sources were cited; faded ones were retrieved
              but unused.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
