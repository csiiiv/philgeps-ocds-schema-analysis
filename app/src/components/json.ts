// JSON syntax highlighter + helpers for copy/download.
// Produces an HTML string with span-wrapped tokens; consumed via dangerouslySetInnerHTML.

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/**
 * Render an arbitrary JS value as pretty-printed, syntax-highlighted HTML.
 * Mimics JSON.stringify(value, null, 2) with colored spans.
 */
export function highlightJson(value: unknown, indent = 0): string {
  const pad = "  ".repeat(indent);
  if (value === null) return `<span class="json-null">null</span>`;
  if (typeof value === "boolean")
    return `<span class="json-bool">${value}</span>`;
  if (typeof value === "number")
    return `<span class="json-number">${value}</span>`;
  if (typeof value === "string") {
    const needsQuote = true;
    const escaped = escapeHtml(value);
    return needsQuote
      ? `<span class="json-string">"${escaped}"</span>`
      : escapeHtml(value);
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return `<span class="json-punct">[]</span>`;
    const inner = value
      .map((v) => `${pad}  ${highlightJson(v, indent + 1)}`)
      .join(`<span class="json-punct">,</span>\n`);
    return `<span class="json-punct">[</span>\n${inner}\n${pad}<span class="json-punct">]</span>`;
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const keys = Object.keys(obj);
    if (keys.length === 0) return `<span class="json-punct">{}</span>`;
    const inner = keys
      .map((k) => {
        const keyHtml = `<span class="json-key">"${escapeHtml(k)}"</span>`;
        return `${pad}  ${keyHtml}<span class="json-punct">: </span>${highlightJson(obj[k], indent + 1)}`;
      })
      .join(`<span class="json-punct">,</span>\n`);
    return `<span class="json-punct">{</span>\n${inner}\n${pad}<span class="json-punct">}</span>`;
  }
  return escapeHtml(String(value));
}

export function highlightJsonString(jsonString: string): string {
  // Fallback: tokenize an already-stringified JSON string.
  return escapeHtml(jsonString)
    .replace(
      /(&quot;(?:\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\&])*?&quot;)(\s*:)/g,
      '<span class="json-key">$1</span>$2',
    )
    .replace(
      /:\s*(&quot;(?:\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\&])*?&quot;)/g,
      (_m, s) => `: <span class="json-string">${s}</span>`,
    )
    .replace(/:\s*(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g, ': <span class="json-number">$1</span>')
    .replace(/:\s*(true|false)/g, ': <span class="json-bool">$1</span>')
    .replace(/:\s*null/g, ': <span class="json-null">null</span>');
}

export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // fall through to legacy path
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

export function downloadText(
  filename: string,
  text: string,
  mime = "application/json",
): void {
  const blob = new Blob([text], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function prettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}
