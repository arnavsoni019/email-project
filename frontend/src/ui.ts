/** Style helpers ported VERBATIM from the Aurora Pro design file.
 *  Values here mirror `design/email-lookup/mailorg - Aurora Pro.dc.html` exactly —
 *  if you change one, the UI stops matching the approved design. */

import type { CSSProperties } from "react";

export const ACC = "var(--acc)";
export const EASE = "cubic-bezier(.32,.72,0,1)";

export const CAT_COLORS: Record<string, string> = {
  Work: "var(--cat-work)",
  Newsletters: "var(--cat-news)",
  Receipts: "var(--cat-rec)",
  Social: "var(--cat-soc)",
  Finance: "var(--cat-fin)",
  Personal: "var(--cat-per)",
  Travel: "var(--cat-tra)",
  Urgent: "var(--cat-urg)",
};

export const catColor = (n: string) => CAT_COLORS[n] ?? "var(--cat-none)";

export const PRIO_LABEL: Record<string, string> = {
  action: "needs a reply",
  fyi: "FYI",
  ignore: "ignore",
};

/** The signature surface: blurred, bordered, softly shadowed. */
export function glass(extra: CSSProperties = {}): CSSProperties {
  return {
    borderRadius: "20px",
    background: "var(--s3)",
    backdropFilter: "blur(20px) saturate(170%)",
    WebkitBackdropFilter: "blur(20px) saturate(170%)",
    border: "1px solid var(--s5)",
    boxShadow: "0 1px 1px var(--sh2),0 12px 30px -20px var(--sh9)",
    ...extra,
  };
}

export function btn(kind: string): CSSProperties {
  const small = kind.indexOf("small") === 0;
  const base: CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    height: small ? "30px" : "32px",
    padding: "0 13px",
    borderRadius: "13px",
    fontSize: small ? "12px" : "12.5px",
    fontWeight: 600,
    cursor: "pointer",
    whiteSpace: "nowrap",
    transition: `background-color .16s ${EASE},opacity .16s`,
  };
  if (kind.indexOf("primary") > -1) {
    return { ...base, border: `1px solid ${ACC}`, background: ACC, color: "var(--acc-on)" };
  }
  return {
    ...base,
    border: "1px solid var(--s5)",
    background: "var(--s4)",
    color: "var(--fg2)",
    fontWeight: 500,
  };
}

export function pill(dim: boolean): CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: "5px",
    padding: "3px 9px 3px 7px",
    borderRadius: "11px",
    background: "var(--chip)",
    fontSize: "11px",
    fontWeight: 600,
    color: dim ? "var(--fg4)" : "var(--fg3)",
    flex: "none",
  };
}

export function navStyle(on: boolean, wide: boolean): CSSProperties {
  return {
    display: "flex",
    alignItems: "center",
    gap: "9px",
    width: "100%",
    height: "32px",
    padding: wide ? "0 10px" : "0",
    justifyContent: wide ? "flex-start" : "center",
    border: "none",
    borderRadius: "13px",
    background: on ? "var(--s8)" : "transparent",
    color: on ? "var(--fg1)" : "var(--fg3)",
    fontSize: "12.5px",
    fontWeight: on ? 600 : 500,
    textAlign: "left",
    cursor: "pointer",
    boxShadow: on ? "0 1px 2px var(--sh5)" : "none",
    transition: `background-color .16s ${EASE}`,
  };
}

export const navIconStyle = (on: boolean): CSSProperties => ({
  display: "grid",
  placeItems: "center",
  flex: "none",
  color: on ? ACC : "var(--fg5)",
  transition: `opacity .16s ${EASE}`,
});

export const badgeStyle: CSSProperties = {
  marginLeft: "auto",
  minWidth: "18px",
  padding: "1px 5px",
  borderRadius: "99px",
  background: ACC,
  color: "var(--acc-on)",
  fontSize: "10.5px",
  fontWeight: 700,
  textAlign: "center",
  fontVariantNumeric: "tabular-nums",
};

export function sideBtn(on: boolean): CSSProperties {
  return {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    width: "100%",
    height: "28px",
    padding: "0 9px",
    border: "none",
    borderRadius: "11px",
    background: on ? "var(--acc-w2)" : "transparent",
    color: "var(--fg3)",
    fontSize: "12px",
    textAlign: "left",
    cursor: "pointer",
    transition: `background-color .16s ${EASE}`,
  };
}

/** Collapsible container used for the correct-panel, thread history and cloud tasks. */
export const reveal = (open: boolean, max: string): CSSProperties => ({
  maxHeight: open ? max : "0px",
  opacity: open ? 1 : 0,
  overflow: "hidden",
  transition: `max-height .24s ${EASE},opacity .18s ${EASE}`,
});

/** Sidebar priority marker: dot (action), ring (fyi), DASH (ignore). */
export function prioMark(id: string): CSSProperties {
  if (id === "action") {
    return { width: "6px", height: "6px", borderRadius: "99px", background: ACC, flex: "none" };
  }
  if (id === "fyi") {
    return { width: "6px", height: "6px", borderRadius: "99px", border: "1px solid var(--edge2)", flex: "none" };
  }
  return { width: "8px", height: "2px", borderRadius: "2px", background: "var(--edge2)", flex: "none" };
}

export const prioLabelStyle = (id: string, on: boolean): CSSProperties => ({
  fontSize: "12px",
  fontWeight: on ? 600 : 500,
  color: id === "ignore" ? "var(--fg4)" : "var(--fg2)",
});

export const catLabelStyle = (count: number, on: boolean): CSSProperties => ({
  fontSize: "12px",
  fontWeight: on ? 600 : 500,
  color: count ? "var(--fg3)" : "var(--fg5)",
});

export const catCountStyle = (count: number): CSSProperties => ({
  marginLeft: "auto",
  fontSize: "11px",
  color: "var(--fg5)",
  fontVariantNumeric: "tabular-nums",
  opacity: count ? 1 : 0.6,
});

/** Priority pill in the reading pane — accent-filled only for "action". */
export const selPrioPill = (prio: string): CSSProperties => ({
  display: "inline-flex",
  alignItems: "center",
  padding: "3px 9px",
  borderRadius: "11px",
  fontSize: "11px",
  fontWeight: 600,
  background: prio === "action" ? "var(--acc-w2)" : "var(--chip)",
  color: prio === "action" ? "var(--acc-t)" : "var(--fg4)",
});

export const PRIO_READER_LABEL: Record<string, string> = {
  action: "needs a reply",
  fyi: "fyi",
  ignore: "noise",
};

/** Selectable chip used in the Correct panel. */
export const chipStyle = (on: boolean): CSSProperties => ({
  display: "inline-flex",
  alignItems: "center",
  gap: "6px",
  padding: "5px 10px",
  fontSize: "11.5px",
  fontWeight: on ? 600 : 500,
  border: `1px solid ${on ? ACC : "var(--s5)"}`,
  borderRadius: "12px",
  background: on ? "var(--acc-w2)" : "var(--s4)",
  color: "var(--fg2)",
  cursor: "pointer",
  transition: `background-color .16s ${EASE},border-color .16s`,
});

export const sectionLabel: CSSProperties = {
  padding: "0 5px 7px",
  fontSize: "10.5px",
  fontWeight: 700,
  letterSpacing: ".09em",
  textTransform: "uppercase",
  color: "var(--fg5)",
};

export const iconBtn: CSSProperties = {
  width: "24px",
  height: "24px",
  display: "grid",
  placeItems: "center",
  border: "1px solid var(--s5)",
  background: "var(--s5)",
  borderRadius: "9px",
  color: "var(--fg4)",
  cursor: "pointer",
  transition: `background-color .16s ${EASE}`,
};
