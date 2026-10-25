/** Reply composer, docked at the foot of the reading pane.
 *
 *  Two ways to change the draft, because they suit different edits: type directly for
 *  a word or a date, describe the change for anything structural. Both write to the
 *  same text.
 *
 *  Every revision pushes the previous version onto a stack. Without that, one vague
 *  instruction silently destroys a draft that was nearly right, and there is no way
 *  back — which makes people stop trying instructions at all.
 *
 *  The draft is autosaved per message id. Generating takes 3s on a cloud model and up
 *  to 20s locally; losing that to an accidental reload is not acceptable.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "./Sprite";
import { api } from "./api";
import { EASE } from "./ui";

/** The instructions worth a single click. Everything else goes in the text field. */
const CHIPS = [
  { label: "Shorter", instruction: "Make it shorter without dropping any commitment I made." },
  { label: "Warmer", instruction: "Make the tone warmer and more personal." },
  { label: "More formal", instruction: "Make the tone more formal and businesslike." },
  { label: "Decline", instruction: "Turn this into a polite decline, keeping it brief." },
];

const key = (id: string) => `mailorg.draft.${id}`;

export function DraftComposer({
  targetId, to, onClose, flash,
}: {
  targetId: string;
  to: string;
  onClose: () => void;
  flash: (text: string, actionLabel?: string, act?: () => void) => void;
}) {
  const [body, setBody] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState<"generating" | "revising" | "saving" | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const started = useRef(false);

  // Restore an in-progress draft, or generate a first one. The ref guard stops React's
  // development double-effect from firing two generations (and two model calls).
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    let saved: string | null = null;
    try { saved = localStorage.getItem(key(targetId)); } catch { /* private mode */ }
    if (saved) { setBody(saved); return; }
    setBusy("generating");
    api.draft(targetId)
      .then((r) => setBody(r.body))
      .catch((e: unknown) => {
        flash(e instanceof Error ? e.message : "Could not draft a reply");
        onClose();
      })
      .finally(() => setBusy(null));
  }, [targetId, flash, onClose]);

  useEffect(() => {
    try {
      if (body) localStorage.setItem(key(targetId), body);
    } catch { /* storage unavailable or full — the draft simply is not restorable */ }
  }, [body, targetId]);

  const revise = useCallback(async (instruction: string) => {
    const text = instruction.trim();
    if (!text || !body.trim() || busy) return;
    setBusy("revising");
    try {
      const r = await api.reviseDraft(targetId, body, text);
      setHistory((h) => [...h, body]);
      setBody(r.body);
      setFeedback("");
    } catch (e) {
      flash(e instanceof Error ? e.message : "Could not revise the draft");
    } finally {
      setBusy(null);
    }
  }, [body, busy, targetId, flash]);

  const undo = () => {
    setHistory((h) => {
      if (!h.length) return h;
      setBody(h[h.length - 1]);
      return h.slice(0, -1);
    });
  };

  const discard = () => {
    try { localStorage.removeItem(key(targetId)); } catch { /* nothing to clear */ }
    onClose();
  };

  const save = async () => {
    if (!body.trim() || busy) return;
    setBusy("saving");
    try {
      await api.saveDraft(targetId, body);
      try { localStorage.removeItem(key(targetId)); } catch { /* nothing to clear */ }
      flash(`Saved to Gmail drafts — reply to ${to}`);
      onClose();
    } catch (e) {
      flash(e instanceof Error ? e.message : "Could not save the draft");
    } finally {
      setBusy(null);
    }
  };

  const working = busy !== null;

  return (
    <div style={{
      flex: "none", borderTop: "1px solid var(--rule)", background: "var(--s2)",
      padding: collapsed ? "10px 26px" : "12px 26px 14px",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "9px" }}>
        <Icon id="ap-reply" size={13} style={{ color: "var(--fg5)", flex: "none" }} />
        <span style={{ fontSize: "12px", fontWeight: 600, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          Reply to {to}
        </span>
        {busy === "generating" && <span style={{ fontSize: "11px", color: "var(--fg5)" }}>drafting…</span>}
        {busy === "revising" && <span style={{ fontSize: "11px", color: "var(--fg5)" }}>revising…</span>}
        {busy === "saving" && <span style={{ fontSize: "11px", color: "var(--fg5)" }}>saving…</span>}
        <button
          onClick={() => setCollapsed((c) => !c)}
          title={collapsed ? "Expand" : "Collapse"}
          style={{ marginLeft: "auto", flex: "none", background: "transparent", border: "none", color: "var(--fg5)", cursor: "pointer", padding: "3px", display: "grid", placeItems: "center" }}
        >
          <Icon id="ap-chev-d" size={13} style={{ transform: collapsed ? "rotate(180deg)" : "none", transition: `transform .2s ${EASE}` }} />
        </button>
        <button
          onClick={discard}
          title="Discard this draft"
          style={{ flex: "none", background: "transparent", border: "none", color: "var(--fg5)", cursor: "pointer", padding: "3px", display: "grid", placeItems: "center" }}
        >
          <Icon id="ap-x" size={13} />
        </button>
      </div>

      {!collapsed && (
        <>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            disabled={busy === "generating"}
            placeholder={busy === "generating" ? "" : "Your reply…"}
            rows={5}
            style={{
              width: "100%", marginTop: "10px", padding: "11px 13px", borderRadius: "12px",
              background: "var(--s1)", border: "1px solid var(--edge)", color: "var(--fg1)",
              fontSize: "13px", lineHeight: 1.65, resize: "vertical", outline: "none",
              opacity: busy === "generating" ? 0.5 : 1,
            }}
          />

          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "9px", flexWrap: "wrap" }}>
            {CHIPS.map((c) => (
              <button
                key={c.label}
                onClick={() => revise(c.instruction)}
                disabled={working || !body.trim()}
                style={{
                  padding: "4px 10px", borderRadius: "99px", border: "1px solid var(--edge)",
                  background: "transparent", color: "var(--fg4)", fontSize: "11px",
                  cursor: working || !body.trim() ? "not-allowed" : "pointer",
                  opacity: working || !body.trim() ? 0.45 : 1,
                }}
              >
                {c.label}
              </button>
            ))}
            {history.length > 0 && (
              <button
                onClick={undo}
                disabled={working}
                style={{
                  marginLeft: "auto", display: "flex", alignItems: "center", gap: "5px",
                  padding: "4px 10px", borderRadius: "99px", border: "1px solid var(--edge)",
                  background: "transparent", color: "var(--fg4)", fontSize: "11px",
                  cursor: working ? "not-allowed" : "pointer", opacity: working ? 0.45 : 1,
                }}
              >
                <Icon id="ap-undo" size={11} />Undo ({history.length})
              </button>
            )}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "7px", marginTop: "10px" }}>
            <input
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") revise(feedback); }}
              disabled={working}
              placeholder="What should change?"
              style={{
                flex: 1, minWidth: 0, padding: "8px 12px", borderRadius: "11px",
                background: "var(--s1)", border: "1px solid var(--edge)", color: "var(--fg1)",
                fontSize: "12.5px", outline: "none",
              }}
            />
            <button
              onClick={save}
              disabled={working || !body.trim()}
              style={{
                flex: "none", display: "flex", alignItems: "center", gap: "6px",
                padding: "8px 15px", borderRadius: "11px", border: "none",
                background: "var(--acc)", color: "var(--acc-on)",
                fontSize: "12.5px", fontWeight: 600,
                cursor: working || !body.trim() ? "not-allowed" : "pointer",
                opacity: working || !body.trim() ? 0.5 : 1,
              }}
            >
              <Icon id="ap-check" size={12} />Save to Gmail
            </button>
          </div>

          <p style={{ margin: "9px 0 0", fontSize: "11px", color: "var(--fg5)", lineHeight: 1.55 }}>
            Saves to your Gmail drafts. Nothing is ever sent.
          </p>
        </>
      )}
    </div>
  );
}
