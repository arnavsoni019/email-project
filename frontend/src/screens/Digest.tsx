/** Digest — what needs attention, what's worth knowing, and what was filtered out. */

import { useState } from "react";
import { Icon } from "../Sprite";
import type { SharedProps } from "../types";
import { EASE, catColor, glass, reveal } from "../ui";

export function Digest(p: SharedProps) {
  const { live, goScreen, select } = p;
  const [noiseOpen, setNoiseOpen] = useState(false);

  const action = live.filter((e) => e.prio === "action");
  const fyi = live.filter((e) => e.prio === "fyi");
  const noise = live.filter((e) => e.prio === "ignore");

  const open = (id: string) => { goScreen("inbox"); select(id); };

  const tiles = [
    { label: "Conversations", value: live.length, note: "in the inbox" },
    { label: "Needs action", value: action.length, note: action.length === 1 ? "one real task" : "tasks waiting" },
    { label: "Filtered out", value: noise.length, note: `${Math.round((noise.length / Math.max(live.length, 1)) * 100)}% was noise` },
  ];

  return (
    <div style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
      <div style={{ maxWidth: "800px", margin: "0 auto", padding: "2px 4px 24px" }}>
        <div style={{ display: "flex", alignItems: "flex-end", gap: "12px", flexWrap: "wrap", padding: "6px 6px 16px" }}>
          <div>
            <div style={{ fontSize: "11.5px", fontWeight: 700, letterSpacing: ".1em", textTransform: "uppercase", color: "var(--fg5)" }}>
              Daily digest
            </div>
            <h1 style={{ margin: "9px 0 0", fontSize: "25px", fontWeight: 600, letterSpacing: "-.03em" }}>
              {new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })}
            </h1>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "9px" }}>
          {tiles.map((t) => (
            <div key={t.label} style={glass({ padding: "14px 16px", display: "flex", flexDirection: "column", gap: "3px" })}>
              <div style={{ fontSize: "11.5px", fontWeight: 600, color: "var(--fg4)" }}>{t.label}</div>
              <div style={{ fontSize: "27px", fontWeight: 600, letterSpacing: "-.03em", fontVariantNumeric: "tabular-nums", lineHeight: 1.15 }}>
                {t.value}
              </div>
              <div style={{ fontSize: "11.5px", color: "var(--fg5)" }}>{t.note}</div>
            </div>
          ))}
        </div>

        {/* needs attention */}
        <div style={glass({ marginTop: "9px", overflow: "hidden" })}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "15px 17px 11px" }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "99px", background: "var(--acc)" }} />
            <span style={{ fontSize: "13.5px", fontWeight: 600, letterSpacing: "-.015em" }}>Needs your attention</span>
            <span style={{ fontSize: "12px", color: "var(--fg5)", fontVariantNumeric: "tabular-nums" }}>{action.length}</span>
          </div>
          <div style={{ padding: "0 9px 9px", display: "flex", flexDirection: "column", gap: "3px" }}>
            {action.length ? action.map((e) => (
              <button
                key={e.id}
                onClick={() => open(e.id)}
                style={{ display: "flex", alignItems: "flex-start", gap: "11px", padding: "12px 13px", borderRadius: "15px", background: "transparent", border: "none", textAlign: "left", cursor: "pointer", transition: `background-color .16s ${EASE}` }}
              >
                <span style={{ width: "18px", height: "18px", flex: "none", marginTop: "1px", display: "grid", placeItems: "center", border: "1px solid var(--edge)", borderRadius: "7px", background: "var(--s4)" }} />
                <span style={{ minWidth: 0 }}>
                  <span style={{ display: "block", fontSize: "13px", fontWeight: 600 }}>{e.tldr || e.subject}</span>
                  <span style={{ display: "block", fontSize: "11.5px", color: "var(--fg5)", marginTop: "3px" }}>
                    {e.sender} · {e.time}
                  </span>
                </span>
              </button>
            )) : (
              <div style={{ padding: "16px 13px", fontSize: "12.5px", color: "var(--fg5)" }}>
                Nothing needs a reply. Everything is read-only or noise.
              </div>
            )}
          </div>
        </div>

        {/* worth knowing */}
        <div style={glass({ marginTop: "9px", overflow: "hidden" })}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "15px 17px 11px" }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "99px", border: "1px solid var(--edge2)" }} />
            <span style={{ fontSize: "13.5px", fontWeight: 600, letterSpacing: "-.015em" }}>Worth knowing</span>
            <span style={{ fontSize: "12px", color: "var(--fg5)", fontVariantNumeric: "tabular-nums" }}>{fyi.length}</span>
          </div>
          <div style={{ padding: "0 9px 9px", display: "flex", flexDirection: "column", gap: "2px" }}>
            {fyi.map((e) => (
              <button
                key={e.id}
                onClick={() => open(e.id)}
                style={{ display: "flex", alignItems: "center", gap: "10px", padding: "11px 13px", borderRadius: "15px", background: "transparent", border: "none", textAlign: "left", cursor: "pointer", transition: `background-color .16s ${EASE}` }}
              >
                <span style={{ width: "6px", height: "6px", borderRadius: "99px", flex: "none", background: catColor(e.cat) }} />
                <span style={{ fontSize: "12.5px", flex: "1 1 auto", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {e.tldr || e.subject}
                </span>
                <span style={{ fontSize: "11px", color: "var(--fg5)", flex: "none" }}>{e.time}</span>
              </button>
            ))}
          </div>
        </div>

        {/* filtered out */}
        <button
          onClick={() => setNoiseOpen((v) => !v)}
          style={{ width: "100%", marginTop: "9px", display: "flex", alignItems: "center", gap: "9px", padding: "14px 17px", borderRadius: "20px", border: "1px dashed var(--edge)", background: "transparent", cursor: "pointer", textAlign: "left", transition: `background-color .16s ${EASE}` }}
        >
          <span style={{ display: "grid", placeItems: "center", color: "var(--fg5)", transform: noiseOpen ? "rotate(90deg)" : "none", transition: `transform .22s ${EASE}` }}>
            <Icon id="ap-chev-r" />
          </span>
          <span style={{ fontSize: "12.5px", color: "var(--fg4)" }}>Filtered out ({noise.length})</span>
          <span style={{ marginLeft: "auto", fontSize: "11.5px", fontWeight: 600, color: "var(--acc)" }}>
            {noiseOpen ? "hide" : "show"}
          </span>
        </button>
        <div style={reveal(noiseOpen, "1400px")}>
          <div style={{ display: "flex", flexDirection: "column", gap: "5px", paddingTop: "7px" }}>
            {noise.map((e) => (
              <button
                key={e.id}
                onClick={() => open(e.id)}
                style={{ display: "flex", alignItems: "center", gap: "10px", padding: "10px 14px", borderRadius: "14px", border: "1px solid var(--s2)", background: "var(--s1)", cursor: "pointer", textAlign: "left" }}
              >
                <span style={{ width: "6px", height: "6px", borderRadius: "99px", flex: "none", background: catColor(e.cat), opacity: 0.55 }} />
                <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--fg4)", flex: "none", maxWidth: "92px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {e.sender}
                </span>
                <span style={{ fontSize: "12px", color: "var(--fg5)", flex: "1 1 auto", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {e.tldr || e.subject}
                </span>
                <span style={{ fontSize: "11px", color: "var(--fg5)", flex: "none" }}>{e.time}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
