/** Proposed Actions — the propose→approve gate.
 *
 *  The agent only ever INSERTs rows here; nothing reaches Gmail until approved, and
 *  applying approved actions is Phase 5. Each card shows the rationale so a decision
 *  is never blind. */

import { Icon } from "../Sprite";
import type { SharedProps } from "../types";
import { EASE, btn, glass } from "../ui";

const TYPE_LABEL: Record<string, string> = {
  archive: "Archive",
  label: "Add label",
  draft: "Draft reply",
};

export function Queue(p: SharedProps) {
  const { proposals, live, resolve, goScreen, select } = p;
  const pending = proposals.filter((x) => x.status === "proposed");
  const decided = proposals.filter((x) => x.status !== "proposed");

  const senderFor = (targetId: string) => live.find((m) => m.id === targetId);

  return (
    <div style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
      <div style={{ maxWidth: "760px", margin: "0 auto", padding: "2px 4px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "6px 6px 14px" }}>
          <div>
            <div style={{ fontSize: "11.5px", fontWeight: 700, letterSpacing: ".1em", textTransform: "uppercase", color: "var(--fg5)" }}>
              Awaiting approval
            </div>
            <h1 style={{ margin: "9px 0 0", fontSize: "22px", fontWeight: 600, letterSpacing: "-.03em" }}>
              {pending.length} proposal{pending.length === 1 ? "" : "s"} waiting
            </h1>
          </div>
        </div>

        {pending.length === 0 && (
          <div style={glass({ padding: "44px 20px", textAlign: "center" })}>
            <div style={{ width: "34px", height: "34px", margin: "0 auto 12px", display: "grid", placeItems: "center", borderRadius: "12px", background: "var(--s4)", color: "var(--fg5)" }}>
              <Icon id="ap-queue" size={16} />
            </div>
            <div style={{ fontSize: "13px", fontWeight: 600 }}>Nothing proposed</div>
            <div style={{ fontSize: "12px", color: "var(--fg5)", marginTop: "6px", lineHeight: 1.6, maxWidth: "320px", margin: "6px auto 0" }}>
              Use <strong>Label</strong> or <strong>Draft reply</strong> on a message and it
              will queue here for your approval. The agent never writes to Gmail directly.
            </div>
          </div>
        )}

        <div style={{ display: "flex", flexDirection: "column", gap: "9px" }}>
          {pending.map((pr) => {
            const msg = senderFor(pr.targetId);
            return (
              <div key={pr.id} style={glass({ padding: "16px 17px" })}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "4px 11px", borderRadius: "12px", fontSize: "11.5px", fontWeight: 600, background: "var(--acc-w2)", color: "var(--acc-t)" }}>
                    <Icon id={pr.type === "archive" ? "ap-archive" : pr.type === "label" ? "ap-tag" : "ap-reply"} size={12} />
                    {TYPE_LABEL[pr.type] ?? pr.type}
                  </span>
                  {msg && (
                    <button
                      onClick={() => { goScreen("inbox"); select(msg.id); }}
                      style={{ display: "flex", alignItems: "baseline", gap: "7px", background: "transparent", border: "none", cursor: "pointer", padding: 0, minWidth: 0 }}
                    >
                      <span style={{ fontSize: "12.5px", fontWeight: 600, color: "var(--fg2)" }}>{msg.sender}</span>
                      <span style={{ fontSize: "11.5px", color: "var(--fg5)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "300px" }}>
                        {msg.subject}
                      </span>
                    </button>
                  )}
                </div>

                <p style={{ margin: "11px 0 0", fontSize: "13px", lineHeight: 1.6, color: "var(--fg2)", textWrap: "pretty" }}>
                  {pr.rationale || "No rationale recorded."}
                </p>

                {/* Approving a reply you have not read is not a review, so the draft is
                    shown in full rather than summarised or hidden behind the card. */}
                {pr.type === "draft" && typeof pr.payload?.body === "string" && (
                  <div style={{ marginTop: "11px", padding: "11px 13px", borderRadius: "12px", background: "var(--s2)", border: "1px solid var(--s4)" }}>
                    <div style={{ fontSize: "10.5px", fontWeight: 700, letterSpacing: ".09em", textTransform: "uppercase", color: "var(--fg5)", marginBottom: "7px" }}>
                      Draft to {String(pr.payload.to ?? "unknown recipient")}
                    </div>
                    <p style={{ margin: 0, fontSize: "12.5px", lineHeight: 1.65, color: "var(--fg2)", whiteSpace: "pre-wrap" }}>
                      {pr.payload.body as string}
                    </p>
                  </div>
                )}

                <div style={{ display: "flex", alignItems: "center", gap: "7px", marginTop: "14px", flexWrap: "wrap" }}>
                  <button onClick={() => resolve(pr.id, true)} style={btn("small primary")}>
                    <Icon id="ap-check" size={12} />Approve
                  </button>
                  <button onClick={() => resolve(pr.id, false)} style={btn("small ghost")}>
                    <Icon id="ap-x" size={12} />Reject
                  </button>
                  <span style={{ marginLeft: "auto", fontSize: "11px", color: "var(--fg5)" }}>
                    proposed locally
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {decided.length > 0 && (
          <>
            <div style={{ padding: "20px 6px 9px", fontSize: "10.5px", fontWeight: 700, letterSpacing: ".09em", textTransform: "uppercase", color: "var(--fg5)" }}>
              Decided
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
              {decided.map((pr) => (
                <div
                  key={pr.id}
                  style={{ display: "flex", alignItems: "center", gap: "10px", padding: "11px 14px", borderRadius: "14px", background: "var(--s1)", border: "1px solid var(--s2)", opacity: 0.72, transition: `opacity .22s ${EASE}` }}
                >
                  <span style={{ display: "inline-flex", alignItems: "center", gap: "5px", padding: "3px 9px", borderRadius: "11px", fontSize: "11px", fontWeight: 600, background: "var(--chip)", color: "var(--fg3)" }}>
                    {TYPE_LABEL[pr.type] ?? pr.type}
                  </span>
                  <span style={{ fontSize: "12px", color: "var(--fg4)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {senderFor(pr.targetId)?.subject ?? pr.targetId}
                  </span>
                  <span style={{ marginLeft: "auto", fontSize: "10.5px", fontWeight: 700, letterSpacing: ".09em", textTransform: "uppercase", color: pr.status === "approved" ? "var(--ok-t)" : "var(--fg5)" }}>
                    {pr.status}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
