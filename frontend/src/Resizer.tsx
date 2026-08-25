/** Draggable divider between panes, plus the hook that remembers each width.
 *
 *  The handle occupies the 10px gap the design already leaves between panes, so the
 *  layout metrics are unchanged — the parent sets `gap: 0` and the Resizer supplies
 *  exactly that spacing back.
 *
 *  Pointer events rather than mouse events: one code path covers mouse, pen and touch,
 *  and `setPointerCapture` keeps the drag tracking even when the cursor moves off the
 *  4px-wide handle, which it immediately does. Without capture, dragging fast would
 *  drop the pane the moment you outran it.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { EASE } from "./ui";

const HANDLE = 10; // matches the design's inter-pane gap

function clamp(n: number, min: number, max: number) {
  return Math.min(max, Math.max(min, n));
}

/** A pane width that survives reload. */
export function usePaneWidth(key: string, initial: number, min: number, max: number) {
  const [width, setWidth] = useState<number>(() => {
    try {
      const stored = window.localStorage.getItem(`mailorg.pane.${key}`);
      if (stored) return clamp(parseInt(stored, 10) || initial, min, max);
    } catch {
      /* private windows and blocked site-data throw on access, not just on write */
    }
    return initial;
  });

  // Persist after the drag settles rather than on every pointermove.
  useEffect(() => {
    const t = window.setTimeout(() => {
      try {
        window.localStorage.setItem(`mailorg.pane.${key}`, String(width));
      } catch {
        /* not important enough to surface */
      }
    }, 250);
    return () => window.clearTimeout(t);
  }, [key, width]);

  const set = useCallback((n: number) => setWidth(clamp(n, min, max)), [min, max]);
  const reset = useCallback(() => setWidth(initial), [initial]);
  return { width, set, reset };
}

interface Props {
  /** Current width of the pane being resized, read when the drag starts. */
  width: number;
  onResize: (next: number) => void;
  /** Double-click restores the design's default. */
  onReset?: () => void;
  /** Lets the parent drop its width transition while dragging. */
  onActiveChange?: (active: boolean) => void;
  label: string;
}

export function Resizer({ width, onResize, onReset, onActiveChange, label }: Props) {
  const [active, setActive] = useState(false);
  const [hover, setHover] = useState(false);
  const start = useRef({ x: 0, w: 0 });

  const setDragging = useCallback((on: boolean) => {
    setActive(on);
    onActiveChange?.(on);
  }, [onActiveChange]);

  // Suppress text selection for the whole document while dragging — otherwise the
  // pointer sweeping across the list highlights every row it crosses.
  useEffect(() => {
    if (!active) return;
    const prev = document.body.style.userSelect;
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
    return () => {
      document.body.style.userSelect = prev;
      document.body.style.cursor = "";
    };
  }, [active]);

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      tabIndex={0}
      onPointerDown={(e) => {
        e.currentTarget.setPointerCapture(e.pointerId);
        start.current = { x: e.clientX, w: width };
        setDragging(true);
      }}
      onPointerMove={(e) => {
        if (!active) return;
        onResize(start.current.w + (e.clientX - start.current.x));
      }}
      onPointerUp={(e) => {
        e.currentTarget.releasePointerCapture(e.pointerId);
        setDragging(false);
      }}
      onPointerCancel={() => setDragging(false)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onFocus={() => setHover(true)}
      onBlur={() => setHover(false)}
      onDoubleClick={onReset}
      // Keyboard parity: a pointer-only control is unusable without a mouse.
      onKeyDown={(e) => {
        const step = e.shiftKey ? 32 : 8;
        if (e.key === "ArrowLeft") { e.preventDefault(); onResize(width - step); }
        if (e.key === "ArrowRight") { e.preventDefault(); onResize(width + step); }
        if (e.key === "Enter") onReset?.();
      }}
      title={`${label} — drag to resize, double-click to reset`}
      style={{
        flex: "none",
        width: `${HANDLE}px`,
        alignSelf: "stretch",
        cursor: "col-resize",
        display: "grid",
        placeItems: "center",
        // The hit area is the full 10px; only a 2px line inside it ever paints, so the
        // divider stays invisible until you go looking for it.
        background: "transparent",
        touchAction: "none", // stop the browser claiming the gesture as a scroll
      }}
    >
      {/* Only a 2px line ever paints, and only while hovered or dragging, so the
          divider stays invisible until you go looking for it. */}
      <span
        style={{
          width: "2px",
          height: active ? "100%" : "34px",
          borderRadius: "99px",
          background: active ? "var(--acc)" : "var(--edge)",
          opacity: active || hover ? 1 : 0,
          transition: `opacity .16s ${EASE}, height .18s ${EASE}, background-color .16s ${EASE}`,
        }}
      />
    </div>
  );
}
