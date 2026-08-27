/** Inbox — 3-pane. Ported from the Aurora Pro design (list rows have two variants:
 *  "full" for action/fyi, and a compact "quiet" row for ignore). */

import { memo, useCallback, useState, type CSSProperties } from "react";
import { HtmlBody } from "../HtmlBody";
import { Resizer, usePaneWidth } from "../Resizer";
import { Icon } from "../Sprite";
import type { Message } from "../api";
import type { SharedProps } from "../types";
import {
  ACC, EASE, PRIO_READER_LABEL, btn, catColor, chipStyle, glass, iconBtn, pill,
  reveal, selPrioPill,
} from "../ui";

function rowStyles(e: Message, sel: boolean, hov: boolean, gone: boolean) {
  const ig = e.prio === "ignore";
  const act = e.prio === "action";
  const bg = sel ? "var(--s7)" : hov ? "var(--s6)" : ig ? "var(--s1)" : "var(--s3)";
  return {
    ig,
    act,
    bubble: {
      display: "block",
      padding: gone ? "0 16px" : ig ? "11px 15px" : "15px 16px",
      borderRadius: ig ? "16px" : "20px",
      background: bg,
      backdropFilter: "blur(18px) saturate(165%)",
      WebkitBackdropFilter: "blur(18px) saturate(165%)",
      border: `1px solid ${sel ? "var(--acc-b3)" : act ? "var(--acc-b2)" : "var(--s5)"}`,
      boxShadow: sel
        ? "0 1px 1px var(--sh3),0 14px 30px -20px var(--sh10)"
        : hov
          ? "0 1px 1px var(--sh2),0 12px 26px -20px var(--sh9)"
          : "0 1px 1px var(--sh1),0 8px 20px -20px var(--sh8)",
      cursor: "pointer",
      maxHeight: gone ? "0px" : "170px",
      opacity: gone ? 0 : 1,
      overflow: "hidden",
      transform: hov && !sel ? "translateY(-1px)" : "none",
      transition: `background-color .16s ${EASE},border-color .16s,box-shadow .16s,transform .16s,opacity .22s ${EASE},max-height .22s ${EASE},padding .22s ${EASE}`,
    } as CSSProperties,
    unread: {
      width: "6px", height: "6px", borderRadius: "99px", flex: "none",
      background: e.unread ? ACC : "transparent",
    } as CSSProperties,
    senderStyle: {
      fontSize: "12.5px", fontWeight: 600, color: ig ? "var(--fg4)" : "var(--fg2)",
      flex: "none", maxWidth: ig ? "92px" : "150px",
      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
    } as CSSProperties,
    timeStyle: {
      marginLeft: ig ? "0" : "auto", fontSize: "11.5px", color: "var(--fg5)",
      fontVariantNumeric: "tabular-nums", flex: "none",
    } as CSSProperties,
    tldrStyle: (ig
      ? {
          margin: 0, fontSize: "12px", lineHeight: 1.45, color: "var(--fg5)",
          flex: "1 1 auto", minWidth: 0, overflow: "hidden",
          textOverflow: "ellipsis", whiteSpace: "nowrap",
        }
      : {
          margin: 0, fontSize: "14px", lineHeight: 1.5, letterSpacing: "-.012em",
          color: "var(--fg1)", display: "-webkit-box", WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical", overflow: "hidden",
        }) as CSSProperties,
    subjStyle: {
      fontSize: "11.5px", color: "var(--fg5)", flex: "1 1 auto", minWidth: 0,
      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
    } as CSSProperties,
    catDot: {
      width: "6px", height: "6px", borderRadius: "99px", flex: "none",
      background: catColor(e.cat), opacity: ig ? 0.55 : 1,
    } as CSSProperties,
    actStyle: {
      display: "flex", gap: "3px", marginLeft: "auto", minWidth: ig ? "26px" : "50px",
      justifyContent: "flex-end", opacity: hov ? 1 : 0,
      pointerEvents: hov ? "auto" : "none", transition: `opacity .16s ${EASE}`,
    } as CSSProperties,
  };
}

const groupOf = (t: string) =>
  !t.includes("d") ? "Today" : t === "1d" ? "Yesterday" : "Earlier";

/** One list row.
 *
 *  Memoised: hover lives in the app shell, so without this every mouse move between
 *  rows re-rendered the whole tree (sidebar, top bar and all rows). Now only the two
 *  rows whose hover state actually changed re-render. */
const Row = memo(function Row({
  e, selected, hovered, gone, onSelect, onHover, onArchive, onLabel,
}: {
  e: Message;
  selected: boolean;
  hovered: boolean;
  gone: boolean;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  onArchive: (id: string) => void;
  onLabel: (e: Message) => void;
}) {
  const st = rowStyles(e, selected, hovered, gone);
  return (
    <article
      onClick={() => onSelect(e.id)}
      onMouseEnter={() => onHover(e.id)}
      onMouseLeave={() => onHover(null)}
      style={st.bubble}
    >
      {!st.ig ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "7px", minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: 0 }}>
            <span style={st.unread} />
            <span style={st.senderStyle}>{e.sender}</span>
            {st.act && (
              <span style={{ fontSize: "11px", fontWeight: 600, color: ACC, flex: "none" }}>
                needs a reply
              </span>
            )}
            <span title={e.exact} style={st.timeStyle}>{e.time}</span>
          </div>
          <p style={st.tldrStyle}>{e.tldr}</p>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: 0 }}>
            <span style={pill(false)}><span style={st.catDot} />{e.cat}</span>
            <span title={e.subject} style={st.subjStyle}>{e.subject}</span>
            <span style={st.actStyle}>
              <button
                onClick={(ev) => { ev.stopPropagation(); onArchive(e.id); }}
                title="Archive · e"
                style={iconBtn}
              >
                <Icon id="ap-archive" size={12} />
              </button>
              <button
                onClick={(ev) => { ev.stopPropagation(); onLabel(e); }}
                title="Propose a label"
                style={iconBtn}
              >
                <Icon id="ap-tag" size={12} />
              </button>
            </span>
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", alignItems: "center", gap: "9px", minWidth: 0 }}>
          <span style={st.catDot} />
          <span style={st.senderStyle}>{e.sender}</span>
          <span style={st.tldrStyle}>{e.tldr}</span>
          <span title={e.exact} style={st.timeStyle}>{e.time}</span>
          <span style={st.actStyle}>
            <button
              onClick={(ev) => { ev.stopPropagation(); onArchive(e.id); }}
              title="Archive · e"
              style={iconBtn}
            >
              <Icon id="ap-archive" size={12} />
            </button>
          </span>
        </div>
      )}
    </article>
  );
});

export function Inbox(p: SharedProps) {
  const {
    messages, sel, selId, hover, archiving, loading, narrow, selOut,
    setHover, select, archive, propose, prioFilter, catFilter, clearFilter, back, stats,
  } = p;
  const [correcting, setCorrecting] = useState(false);
  const [showEarlier, setShowEarlier] = useState(false);
  // Held as an id rather than a boolean so selecting another message collapses back to
  // the summary automatically — no effect needed, and no stale "expanded" flag.
  const [originalFor, setOriginalFor] = useState<string | null>(null);
  const showOriginal = !!sel && originalFor === sel.id;
  // 340px is the design's list width. The lower bound keeps a row's sender + time
  // legible; the upper bound leaves the reader usable.
  const { width: listW, set: setListW, reset: resetListW } = usePaneWidth("list", 340, 280, 620);

  // Stable identity so memoised rows don't re-render on every parent render.
  const onLabel = useCallback(
    (e: Message) =>
      propose("label", e.id, `Requested from the inbox list. Suggested label ${e.cat}.`, { labelName: `mailorg/${e.cat}` }),
    [propose],
  );

  // Wide layout gives the list an explicit width so the divider can drive it; the
  // reader takes whatever is left. Narrow layout still stacks one pane at a time.
  const listPanel = glass(
    narrow
      ? { flex: "1 1 auto", minWidth: 0, display: "flex", flexDirection: "column", overflow: "hidden" }
      : { flex: "none", width: `${listW}px`, display: "flex", flexDirection: "column", overflow: "hidden" },
  );
  const readerPanel = glass(
    narrow
      ? { flex: "1 1 auto", minWidth: 0, overflow: "hidden" }
      : { flex: "1 1 auto", minWidth: 0, overflow: "hidden" },
  );

  const hasFilter = !!(prioFilter || catFilter);
  const filterLabel = prioFilter
    ? { action: "Needs Action", fyi: "FYI", ignore: "Ignore" }[prioFilter] ?? prioFilter
    : catFilter ?? "All mail";

  const groups = ["Today", "Yesterday", "Earlier"]
    .map((k) => ({ label: k, rows: messages.filter((m) => groupOf(m.time) === k) }))
    .filter((g) => g.rows.length);

  const showList = !narrow || !sel;
  const showReader = !narrow || !!sel;

  // gap:0 in the wide layout because the Resizer supplies the 10px spacing itself.
  return (
    <div style={{ flex: 1, minHeight: 0, display: "flex", gap: narrow ? "10px" : 0 }}>
      {showList && (
        <section style={listPanel}>
          <div style={{ flex: "none", display: "flex", alignItems: "center", gap: "8px", padding: "13px 16px 10px" }}>
            <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: ".09em", textTransform: "uppercase", color: "var(--fg5)" }}>
              {filterLabel}
            </span>
            {hasFilter && (
              <button
                onClick={clearFilter}
                style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "11px", fontWeight: 600, color: ACC, background: "transparent", border: "none", cursor: "pointer", padding: "2px 4px", borderRadius: "8px" }}
              >
                <Icon id="ap-x" size={10} />clear
              </button>
            )}
            <span style={{ marginLeft: "auto", fontSize: "11px", color: "var(--fg5)", fontVariantNumeric: "tabular-nums" }}>
              {messages.length}
            </span>
          </div>

          <div style={{ flex: 1, overflowY: "auto", padding: "0 10px 12px", minHeight: 0 }}>
            {loading && (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {[0, 1, 2, 3, 4].map((i) => (
                  <div key={i} style={{ display: "flex", flexDirection: "column", gap: "8px", padding: "15px 16px", borderRadius: "20px", background: "var(--s2)", border: "1px solid var(--s4)", animation: `apSkel 1.5s ${EASE} infinite`, animationDelay: `${i * 90}ms` }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <div style={{ height: "14px", width: "62px", borderRadius: "8px", background: "var(--rule)" }} />
                      <div style={{ marginLeft: "auto", height: "9px", width: "22px", borderRadius: "6px", background: "var(--rule)" }} />
                    </div>
                    <div style={{ height: "11px", width: "94%", borderRadius: "6px", background: "var(--rule)" }} />
                    <div style={{ height: "11px", width: "62%", borderRadius: "6px", background: "var(--rule)" }} />
                  </div>
                ))}
              </div>
            )}

            {!loading && groups.map((g) => (
              <div key={g.label}>
                <div style={{ padding: "12px 6px 7px", fontSize: "10.5px", fontWeight: 700, letterSpacing: ".11em", textTransform: "uppercase", color: "var(--fg5)" }}>
                  {g.label}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {g.rows.map((e) => (
                    <Row
                      key={e.id}
                      e={e}
                      selected={selId === e.id}
                      hovered={hover === e.id}
                      gone={archiving === e.id}
                      onSelect={select}
                      onHover={setHover}
                      onArchive={archive}
                      onLabel={onLabel}
                    />
                  ))}
                </div>
              </div>
            ))}

            {!loading && !messages.length && (
              <div style={{ padding: "44px 20px", textAlign: "center" }}>
                <div style={{ width: "32px", height: "32px", margin: "0 auto 12px", display: "grid", placeItems: "center", borderRadius: "11px", background: "var(--s4)", color: "var(--fg5)" }}>
                  <Icon id="ap-inbox" size={15} />
                </div>
                <div style={{ fontSize: "13px", fontWeight: 600 }}>
                  {catFilter ? `Nothing in ${catFilter}` : "Inbox zero"}
                </div>
                <div style={{ fontSize: "12px", color: "var(--fg5)", marginTop: "5px", lineHeight: 1.55 }}>
                  {catFilter
                    ? "Local triage has not filed anything here in the last 30 days."
                    : "Everything has been archived or handled."}
                </div>
              </div>
            )}
          </div>
        </section>
      )}

      {/* Only when both panes are on screen — there is nothing to divide otherwise. */}
      {!narrow && showList && showReader && (
        <Resizer
          label="List width"
          width={listW}
          onResize={setListW}
          onReset={resetListW}
        />
      )}

      {showReader && (
        <section style={readerPanel}>
          {sel ? (
            <div style={{
              display: "flex", flexDirection: "column", height: "100%", minHeight: 0,
              opacity: selOut ? 0 : 1,
              transform: selOut ? "translateY(6px)" : "none",
              transition: `opacity .1s ${EASE},transform .24s ${EASE}`,
            }}>
              <div style={{ flex: 1, overflowY: "auto", padding: "22px 26px 10px", minHeight: 0 }}>
                <div style={{ maxWidth: "660px" }}>
                  {narrow && (
                    <button
                      onClick={back}
                      style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "14px", fontSize: "12px", fontWeight: 600, color: "var(--fg4)", background: "transparent", border: "none", padding: 0, cursor: "pointer" }}
                    >
                      <Icon id="ap-chev-r" style={{ transform: "rotate(180deg)" }} />All mail
                    </button>
                  )}
                  <h1 style={{ margin: 0, fontSize: "18px", fontWeight: 600, letterSpacing: "-.025em", lineHeight: 1.35, textWrap: "pretty" }}>
                    {sel.subject}
                  </h1>
                  <div style={{ display: "flex", alignItems: "baseline", gap: "9px", marginTop: "10px", flexWrap: "wrap" }}>
                    <span style={{ fontSize: "13px", fontWeight: 600 }}>{sel.sender}</span>
                    <span style={{ fontSize: "11.5px", color: "var(--fg5)" }}>{sel.email}</span>
                    <span style={{ marginLeft: "auto", fontSize: "11.5px", color: "var(--fg5)" }}>{sel.exact}</span>
                  </div>

                  <div style={{ marginTop: "18px", padding: "14px 16px", borderRadius: "18px", background: "var(--acc-w1)", border: "1px solid var(--acc-b1)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "7px" }}>
                      <span style={{ color: "var(--acc-t)", display: "grid", placeItems: "center" }}>
                        <Icon id="ap-spark" />
                      </span>
                      <span style={{ fontSize: "11px", fontWeight: 700, letterSpacing: ".07em", textTransform: "uppercase", color: "var(--acc-t)" }}>
                        Summary
                      </span>
                      <span style={{ marginLeft: "auto", fontSize: "11px", color: "var(--acc-dim)" }}>
                        {p.settings?.model_light ?? "local"} · on-device
                      </span>
                    </div>
                    <p style={{ margin: "9px 0 0", fontSize: "14.5px", lineHeight: 1.55, letterSpacing: "-.01em", color: "var(--fg1)", textWrap: "pretty" }}>
                      {sel.tldr || "Not processed yet."}
                    </p>
                    <div style={{ display: "flex", alignItems: "center", gap: "7px", marginTop: "12px", flexWrap: "wrap" }}>
                      <span style={pill(false)}>
                        <span style={{ width: "6px", height: "6px", borderRadius: "99px", background: catColor(sel.cat) }} />
                        {sel.cat || "uncategorised"}
                      </span>
                      <span style={selPrioPill(sel.prio)}>
                        {PRIO_READER_LABEL[sel.prio] ?? sel.prio}
                      </span>
                      <button
                        onClick={() => setCorrecting((v) => !v)}
                        style={{ display: "flex", alignItems: "center", gap: "5px", marginLeft: "auto", fontSize: "11.5px", fontWeight: 600, color: "var(--fg4)", background: "transparent", border: "none", cursor: "pointer", padding: "3px 5px", borderRadius: "9px" }}
                      >
                        <Icon id="ap-pencil" size={11} />
                        {correcting ? "Done" : "Correct"}
                      </button>
                    </div>

                    <div style={reveal(correcting, "340px")}>
                      <div style={{ paddingTop: "12px", marginTop: "12px", borderTop: "1px solid var(--rule)" }}>
                        <div style={{ fontSize: "10.5px", fontWeight: 700, letterSpacing: ".09em", textTransform: "uppercase", color: "var(--fg5)", marginBottom: "7px" }}>
                          Category
                        </div>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
                          {(stats?.categories ?? []).map((c) => (
                            <button key={c.n} style={chipStyle(sel.cat === c.n)}>
                              <span style={{ width: "6px", height: "6px", borderRadius: "99px", background: catColor(c.n) }} />
                              {c.n}
                            </button>
                          ))}
                        </div>
                        <div style={{ fontSize: "10.5px", fontWeight: 700, letterSpacing: ".09em", textTransform: "uppercase", color: "var(--fg5)", margin: "12px 0 7px" }}>
                          Priority
                        </div>
                        <div style={{ display: "flex", gap: "5px", flexWrap: "wrap" }}>
                          {[
                            { id: "action", t: "Needs action" },
                            { id: "fyi", t: "FYI" },
                            { id: "ignore", t: "Ignore" },
                          ].map((pr) => (
                            <button key={pr.id} style={{ ...chipStyle(sel.prio === pr.id), padding: "5px 11px" }}>
                              {pr.t}
                            </button>
                          ))}
                        </div>
                        <div style={{ fontSize: "11px", color: "var(--fg5)", marginTop: "10px", lineHeight: 1.55 }}>
                          Corrections stay on this machine and re-weight the local triage model.
                        </div>
                      </div>
                    </div>
                  </div>

                  {sel.earlier.length > 0 && (
                    <div>
                      <button
                        onClick={() => setShowEarlier((v) => !v)}
                        style={{ width: "100%", marginTop: "16px", display: "flex", alignItems: "center", gap: "9px", padding: "11px 14px", borderRadius: "16px", border: "1px solid var(--s5)", background: "var(--s2)", cursor: "pointer", transition: `background-color .16s ${EASE}` }}
                      >
                        <span style={{ display: "grid", placeItems: "center", color: "var(--fg5)", transform: showEarlier ? "rotate(90deg)" : "none", transition: `transform .22s ${EASE}` }}>
                          <Icon id="ap-chev-r" />
                        </span>
                        <span style={{ fontSize: "12.5px", color: "var(--fg3)" }}>
                          {sel.earlier.length} earlier message{sel.earlier.length === 1 ? "" : "s"} in this thread
                        </span>
                        <span style={{ marginLeft: "auto", fontSize: "11.5px", fontWeight: 600, color: ACC }}>
                          {showEarlier ? "hide" : "show"}
                        </span>
                      </button>
                      <div style={reveal(showEarlier, "600px")}>
                      <div style={{ display: "flex", flexDirection: "column", gap: "5px", paddingTop: "7px" }}>
                        {sel.earlier.map((m, i) => (
                          <div key={i} style={{ display: "flex", gap: "9px", padding: "10px 13px", borderRadius: "15px", background: "var(--s2)", border: "1px solid var(--s4)" }}>
                            <span style={{ fontSize: "12px", fontWeight: 600, flex: "none" }}>{m.who}</span>
                            <span style={{ fontSize: "12px", color: "var(--fg4)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.line}</span>
                            <span style={{ marginLeft: "auto", fontSize: "11px", color: "var(--fg5)", flex: "none" }}>{m.when}</span>
                          </div>
                        ))}
                      </div>
                      </div>
                    </div>
                  )}

                  {/* Reading is summary-first: the point of the product is not to
                      reproduce the sender's poster, it is to say what matters. The
                      faithful render stays one click away for when it isn't enough. */}
                  <div style={{ marginTop: "20px", paddingTop: "18px", borderTop: "1px solid var(--rule)" }}>
                    {showOriginal && sel.blockedImages > 0 && (
                      <div style={{ display: "flex", alignItems: "center", gap: "9px", padding: "9px 13px", marginBottom: "12px", borderRadius: "13px", background: "var(--warn-w)", border: "1px solid var(--warn-b)", fontSize: "12px", color: "var(--warn-fg)" }}>
                        <span>
                          {sel.blockedImages} remote image{sel.blockedImages === 1 ? "" : "s"} blocked —
                          loading them tells the sender you opened this.
                        </span>
                        <button
                          onClick={() => p.loadImages(sel.id)}
                          style={{ marginLeft: "auto", flex: "none", padding: "4px 11px", borderRadius: "10px", border: "1px solid var(--warn-b)", background: "transparent", color: "var(--warn-t)", fontSize: "11.5px", fontWeight: 600, cursor: "pointer" }}
                        >
                          Load images
                        </button>
                      </div>
                    )}

                    {showOriginal && sel.html ? (
                      <HtmlBody html={sel.html} imagesLoaded={sel.imagesLoaded} />
                    ) : (
                      // overflowWrap keeps long URLs from forcing a horizontal scrollbar.
                      <div style={{ fontSize: "13.5px", lineHeight: 1.75, color: "var(--fg2)", whiteSpace: "pre-line", textWrap: "pretty", maxWidth: "62ch", overflowWrap: "anywhere", wordBreak: "break-word" }}>
                        {sel.body}
                      </div>
                    )}

                    {sel.html && (
                      <button
                        onClick={() => setOriginalFor(showOriginal ? null : sel.id)}
                        style={{ display: "flex", alignItems: "center", gap: "7px", marginTop: "16px", padding: "7px 13px", borderRadius: "13px", border: "1px solid var(--s5)", background: "var(--s3)", color: "var(--fg3)", fontSize: "12px", fontWeight: 600, cursor: "pointer", transition: `background-color .16s ${EASE}` }}
                      >
                        <span style={{ display: "grid", placeItems: "center", color: "var(--fg5)", transform: showOriginal ? "rotate(180deg)" : "none", transition: `transform .22s ${EASE}` }}>
                          <Icon id="ap-chev-d" size={13} />
                        </span>
                        {showOriginal ? "Hide original" : "Show original email"}
                        {!showOriginal && sel.blockedImages > 0 && (
                          <span style={{ fontSize: "11px", fontWeight: 500, color: "var(--fg5)" }}>
                            · {sel.blockedImages} images
                          </span>
                        )}
                      </button>
                    )}
                  </div>
                  <div style={{ height: "16px" }} />
                </div>
              </div>

              <div style={{ flex: "none", padding: "12px 26px", borderTop: "1px solid var(--rule)", display: "flex", alignItems: "center", gap: "7px", flexWrap: "wrap" }}>
                <button
                  onClick={() => propose("draft", sel.id, "Requested from the reading pane.")}
                  style={btn("primary")}
                >
                  <Icon id="ap-reply" />Draft reply
                </button>
                <button
                  onClick={() => propose("label", sel.id, `Requested from the reading pane. Suggested label ${sel.cat}.`, { labelName: `mailorg/${sel.cat}` })}
                  style={btn("ghost")}
                >
                  <Icon id="ap-tag" style={{ opacity: 0.55 }} />Label
                </button>
                <button onClick={() => archive(sel.id)} style={btn("ghost")}>
                  <Icon id="ap-archive" style={{ opacity: 0.55 }} />Archive
                </button>
                <span style={{ marginLeft: "auto", fontSize: "11px", color: "var(--fg5)", maxWidth: "230px", lineHeight: 1.45 }}>
                  Every action is proposed — nothing changes until you approve it.
                </span>
              </div>
            </div>
          ) : (
            <div style={{ height: "100%", display: "grid", placeItems: "center", padding: "24px" }}>
              <div style={{ textAlign: "center", maxWidth: "250px" }}>
                <div style={{ width: "34px", height: "34px", margin: "0 auto 12px", display: "grid", placeItems: "center", borderRadius: "12px", background: "var(--s4)", color: "var(--fg5)" }}>
                  <Icon id="ap-inbox" size={16} />
                </div>
                <div style={{ fontSize: "13px", fontWeight: 600 }}>Nothing open</div>
                <div style={{ fontSize: "12px", color: "var(--fg5)", marginTop: "6px", lineHeight: 1.6 }}>
                  Pick a message, or press{" "}
                  <span style={{ fontSize: "11px", fontWeight: 600, padding: "1px 6px", borderRadius: "8px", background: "var(--chip)" }}>j</span>
                  {" / "}
                  <span style={{ fontSize: "11px", fontWeight: 600, padding: "1px 6px", borderRadius: "8px", background: "var(--chip)" }}>k</span>
                  {" "}to move.
                </div>
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
