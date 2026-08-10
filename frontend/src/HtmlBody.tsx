/** Renders an email's HTML the way a mail client does — inside a locked-down iframe.
 *
 *  Why an iframe rather than dangerouslySetInnerHTML:
 *
 *  1. **Scripts cannot run.** The `sandbox` attribute omits `allow-scripts`, so the
 *     browser refuses to execute anything in the frame — a guarantee independent of
 *     the server-side sanitiser. Two layers, either alone sufficient.
 *  2. **CSS cannot leak.** Emails ship thousands of lines of CSS with generic selectors
 *     (`table { width: 100% }`). Injected into the page, that would restyle the app.
 *     A frame is a separate document, so it cannot reach us.
 *  3. **A CSP blocks remote fetches**, so a missed URL still cannot phone home.
 *
 *  `allow-same-origin` IS present and is safe *because* `allow-scripts` is not: no code
 *  runs inside, and the parent needs same-origin access to measure content height for
 *  auto-sizing. (`allow-scripts` + `allow-same-origin` together is the dangerous combo —
 *  that pair lets framed code reach out and touch the parent.)
 */

import { useEffect, useRef, useState } from "react";

interface Props {
  html: string;
  /** Remote images already loaded? Drives the CSP we inject. */
  imagesLoaded: boolean;
}

/** Wrap the email in a minimal document: a CSP, and typography that inherits the app. */
function buildDoc(html: string, imagesLoaded: boolean): string {
  // Images are already neutralised server-side; this is defence in depth, and it also
  // catches CSS-based fetches the sanitiser's url() stripping might have missed.
  const csp = [
    "default-src 'none'",
    "style-src 'unsafe-inline'",
    imagesLoaded ? "img-src https: data:" : "img-src data:",
    "form-action 'none'",
  ].join("; ");

  return `<!doctype html><html><head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<base target="_blank">
<style>
  html,body{margin:0;padding:0;background:transparent;
    font-family:'Plus Jakarta Sans',system-ui,-apple-system,sans-serif;
    font-size:13.5px;line-height:1.6;color:#111;
    -webkit-font-smoothing:antialiased;overflow-x:hidden}
  /* Senders assume a fixed-width desktop client; keep wide tables from
     forcing a horizontal scrollbar inside the reading pane. */
  img,table,td{max-width:100%!important;height:auto}
  table{border-collapse:collapse}
  a{color:#2563eb}
  *{word-break:break-word;overflow-wrap:anywhere}
</style></head><body>${html}</body></html>`;
}

export function HtmlBody({ html, imagesLoaded }: Props) {
  const ref = useRef<HTMLIFrameElement | null>(null);
  const [height, setHeight] = useState(320);

  useEffect(() => {
    const frame = ref.current;
    if (!frame) return;

    // Measure after load, then again shortly after: images and fonts settle late and
    // change the height, and with no script inside the frame it cannot tell us itself.
    const measure = () => {
      const doc = frame.contentDocument;
      if (!doc?.body) return;
      const h = Math.max(doc.body.scrollHeight, doc.documentElement?.scrollHeight ?? 0);
      if (h > 0) setHeight(h + 8);
    };

    frame.addEventListener("load", measure);
    const timers = [120, 400, 1000].map((ms) => window.setTimeout(measure, ms));
    return () => {
      frame.removeEventListener("load", measure);
      timers.forEach(clearTimeout);
    };
  }, [html, imagesLoaded]);

  return (
    <iframe
      ref={ref}
      title="Email content"
      // No allow-scripts: nothing in here can execute, whatever the sender sent.
      sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox"
      srcDoc={buildDoc(html, imagesLoaded)}
      style={{
        display: "block",
        width: "100%",
        height: `${height}px`,
        border: "none",
        background: "#fff",
        borderRadius: "12px",
        colorScheme: "light", // emails assume a light background; don't let dark mode invert them
      }}
    />
  );
}
