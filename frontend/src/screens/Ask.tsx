/** Ask — natural-language question over the inbox.
 *
 *  Phase 4 wires this to embeddings + ChromaDB. Until then it does an honest local
 *  keyword search over the already-synced messages and says so, rather than pretending
 *  to be a semantic model. */

import { useState } from "react";
import { Icon } from "../Sprite";
import type { Message } from "../api";
import type { SharedProps } from "../types";
import { EASE, btn, catColor, glass } from "../ui";

const CHIPS = [
  "when is my package arriving?",
  "show me receipts this month",
  "anything I need to reply to?",
  "what did McAfee want?",
];

export function Ask(p: SharedProps) {
  const { live, goScreen, select } = p;
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<{ q: string; cites: Message[] } | null>(null);

  const run = (raw: string) => {
    const query = raw.trim();
    if (!query) return;
    setBusy(true);
    setAnswer(null);
    // Keyword match across what the local model already extracted.
    window.setTimeout(() => {
      const words = query.toLowerCase().split(/\s+/).filter((w) => w.length > 3);
      const scored = live
        .map((e) => {
          const hay = `${e.sender} ${e.subject} ${e.tldr} ${e.cat}`.toLowerCase();
          return { e, score: words.filter((w) => hay.includes(w)).length };
        })
        .filter((x) => x.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 4)
        .map((x) => x.e);
      setAnswer({ q: query, cites: scored });
      setBusy(false);
    }, 260);
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

        {answer && !busy && (
          <div style={glass({ marginTop: "9px", padding: "17px 18px" })}>
            <div style={{ fontSize: "11px", fontWeight: 700, letterSpacing: ".07em", textTransform: "uppercase", color: "var(--fg5)" }}>
              {answer.q}
            </div>
            <p style={{ margin: "10px 0 0", fontSize: "14px", lineHeight: 1.6, color: "var(--fg1)", textWrap: "pretty" }}>
              {answer.cites.length
                ? `Found ${answer.cites.length} matching email${answer.cites.length === 1 ? "" : "s"} by searching the summaries already generated on this machine. Open them below.`
                : "Nothing matched. Semantic search arrives in Phase 4 — right now this only matches keywords against stored summaries."}
            </p>

            {answer.cites.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "5px", marginTop: "13px" }}>
                {answer.cites.map((e) => (
                  <button
                    key={e.id}
                    onClick={() => { goScreen("inbox"); select(e.id); }}
                    style={{ display: "flex", alignItems: "center", gap: "9px", padding: "10px 13px", borderRadius: "15px", background: "var(--s2)", border: "1px solid var(--s4)", cursor: "pointer", textAlign: "left", transition: `background-color .16s ${EASE}` }}
                  >
                    <span style={{ width: "6px", height: "6px", borderRadius: "99px", flex: "none", background: catColor(e.cat) }} />
                    <span style={{ fontSize: "12px", fontWeight: 600, flex: "none" }}>{e.sender}</span>
                    <span style={{ fontSize: "12px", color: "var(--fg4)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {e.tldr || e.subject}
                    </span>
                    <span style={{ marginLeft: "auto", fontSize: "11px", color: "var(--fg5)", flex: "none" }}>{e.time}</span>
                  </button>
                ))}
              </div>
            )}

            <div style={{ marginTop: "13px", paddingTop: "11px", borderTop: "1px solid var(--rule)", fontSize: "11px", color: "var(--fg5)", lineHeight: 1.55 }}>
              Keyword search over locally-stored summaries. True semantic search (embeddings
              + ChromaDB) lands in Phase 4.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
