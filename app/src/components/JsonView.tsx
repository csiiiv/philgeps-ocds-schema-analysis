import { useState, type ReactNode } from "react";
import { classNames } from "./helpers";
import { copyText, downloadText, highlightJson, prettyJson } from "./json";

/** Lazy-rendered JSON — only highlights when the parent panel is open. */
export function LazyJsonView({
  value,
  maxHeight = "70vh",
  filename = "release.json",
}: {
  value: unknown;
  maxHeight?: string;
  filename?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="json-wrap">
      {!open ? (
        <button type="button" className="btn" style={{ margin: "8px 12px" }} onClick={() => setOpen(true)}>
          Load JSON
        </button>
      ) : (
        <>
          <div className="json-scroll" style={{ maxHeight }}>
            <pre dangerouslySetInnerHTML={{ __html: highlightJson(value) }} />
          </div>
          <JsonActions text={prettyJson(value)} filename={filename} />
        </>
      )}
    </div>
  );
}

/** Pretty, syntax-highlighted, scrollable JSON viewer. */
export function JsonView({
  value,
  maxHeight = "70vh",
  filename = "release.json",
}: {
  value: unknown;
  maxHeight?: string;
  filename?: string;
}) {
  const html = highlightJson(value);
  const text = prettyJson(value);
  return (
    <div className="json-wrap">
      <div className="json-scroll" style={{ maxHeight }}>
        <pre dangerouslySetInnerHTML={{ __html: html }} />
      </div>
      <JsonActions text={text} filename={filename} />
    </div>
  );
}

/** A highlighted JSON block with a heading and anchor id. */
export function JsonBlock({
  id,
  title,
  anchor,
  value,
  defaultExpanded = true,
}: {
  id?: string;
  title: ReactNode;
  anchor?: string;
  value: unknown;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const text = prettyJson(value);
  return (
    <div className="json-block" id={id}>
      <div className="json-block-header">
        {anchor && <span className="anchor">{anchor}</span>}
        <span>{title}</span>
        <button
          className="btn"
          style={{ marginLeft: "auto", padding: "2px 8px", fontSize: 12 }}
          onClick={() => setExpanded((e) => !e)}
        >
          {expanded ? "Hide" : "Show"}
        </button>
      </div>
      {expanded && (
        <div className="json-wrap">
          <div className="json-scroll" style={{ maxHeight: "50vh" }}>
            <pre dangerouslySetInnerHTML={{ __html: highlightJson(value) }} />
          </div>
          <JsonActions text={text} filename={`${anchor ?? "block"}.json`} />
        </div>
      )}
    </div>
  );
}

function JsonActions({ text, filename }: { text: string; filename: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        padding: "8px 12px",
        borderTop: "1px solid var(--border)",
        background: "var(--bg-elevated)",
      }}
    >
      <button
        className={classNames("btn", copied && "copied")}
        onClick={async () => {
          const ok = await copyText(text);
          if (ok) {
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }
        }}
      >
        {copied ? "Copied ✓" : "Copy JSON"}
      </button>
      <button className="btn" onClick={() => downloadText(filename, text)}>
        Download {filename}
      </button>
      <span style={{ flex: 1 }} />
      <span className="row-count">{(text.length / 1024).toFixed(1)} KB</span>
    </div>
  );
}
