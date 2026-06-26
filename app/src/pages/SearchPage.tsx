import { useMemo, useState } from "react";
import { bundle, SCHEMA_KEY_LIST, SCHEMA_SHORT_KEYS } from "../data/bundle";
import { PageHeader, SectionHeader, navigate } from "../components/Layout";
import { Card, Badge, PathCode } from "../components/ui";
import { SearchInput } from "../components/filters";
import { highlight, safeHtml } from "../components/helpers";

interface SearchHit {
  id: string;
  group: string;
  title: string;
  subtitle: string;
  match: string;
  href: string;
}

export function SearchPage() {
  const [query, setQuery] = useState("");
  const hits = useMemo(() => buildHits(query.trim().toLowerCase()), [query]);

  return (
    <>
      <PageHeader
        title="Global search"
        subtitle="Search across canonical fields, OCDS paths, source columns, codelists, and PhilGEPS labels in one place."
      />

      <div className="toolbar">
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder="Search anything…"
          autoFocus
          key="search-page-input"
        />
        <span style={{ minWidth: 1, flex: 1 }} />
      </div>

      {query.trim() === "" ? (
        <Card>
          <div className="card-body muted">Type to search.</div>
        </Card>
      ) : hits.length === 0 ? (
        <Card>
          <div className="card-body muted">No matches for “{query}”.</div>
        </Card>
      ) : (
        <>
          <SectionHeader title={`${hits.length} match${hits.length === 1 ? "" : "es"}`} />
          <div className="card-grid cols-2">
            {hits.map((h) => (
              <HitCard key={h.id} hit={h} query={query} />
            ))}
          </div>
        </>
      )}
    </>
  );
}

function buildHits(q: string): SearchHit[] {
  if (!q) return [];
  const out: SearchHit[] = [];

  for (const f of bundle.canonical_fields) {
    const fields = [f.canonical_field, f.semantic_name ?? "", ...f.ocds_paths];
    for (const p of f.ocds_paths) {
      if (p.toLowerCase().includes(q)) {
        out.push({
          id: `cf-ocds-${f.canonical_field}-${p}`,
          group: "Canonical field · OCDS path",
          title: f.canonical_field,
          subtitle: f.semantic_name ?? "",
          match: p,
          href: "#/canonical",
        });
      }
    }
    for (const s of SCHEMA_KEY_LIST) {
      const col = f.source_columns[s];
      if (col && col.toLowerCase().includes(q)) {
        out.push({
          id: `cf-col-${f.canonical_field}-${s}`,
          group: `Canonical field · ${SCHEMA_SHORT_KEYS[s]} source column`,
          title: f.canonical_field,
          subtitle: f.semantic_name ?? "",
          match: col,
          href: "#/canonical",
        });
      }
    }
    if (fields.some((x) => x.toLowerCase().includes(q))) {
      out.push({
        id: `cf-${f.canonical_field}`,
        group: "Canonical field",
        title: f.canonical_field,
        subtitle: f.semantic_name ?? f.category ?? "",
        match: f.canonical_field,
        href: "#/canonical",
      });
    }
  }

  for (const r of bundle.ocds_crosswalk) {
    const hay = [r.ocds_field, r.philgeps_1_5, r.philgeps_2_0, r.v2_csv, r.v1_csv];
    for (const f of hay) {
      if (f && f !== "—" && f.toLowerCase().includes(q)) {
        out.push({
          id: `cw-${r.ocds_field}-${f}`,
          group: "Crosswalk row",
          title: r.ocds_field === "—" ? "(no OCDS path)" : r.ocds_field,
          subtitle: r.canonical,
          match: f,
          href: "#/crosswalk",
        });
        break;
      }
    }
  }

  for (const b of bundle.ocds_staged.blocks) {
    for (const p of b.paths) {
      if (p.path.toLowerCase().includes(q) || p.canonical.toLowerCase().includes(q)) {
        out.push({
          id: `stg-${b.block}-${p.path}`,
          group: `OCDS staged · ${b.block}`,
          title: p.path,
          subtitle: `→ ${p.canonical}`,
          match: p.path,
          href: "#/staged",
        });
      }
    }
  }

  for (const c of bundle.codelists) {
    for (const e of c.entries) {
      if (e.philgeps.toLowerCase().includes(q) || e.ocds.toLowerCase().includes(q)) {
        out.push({
          id: `cl-${c.name}-${e.philgeps}`,
          group: `Codelist · ${c.label}`,
          title: e.philgeps,
          subtitle: `→ ${e.ocds}`,
          match: e.philgeps,
          href: "#/codelists",
        });
      }
    }
  }

  return out.slice(0, 80);
}

function HitCard({ hit, query }: { hit: SearchHit; query: string }) {
  return (
    <Card interactive onClick={() => navigate(hit.href.replace(/^#\/?/, ""))}>
      <div className="card-title">
        <Badge variant="outline">{hit.group}</Badge>
      </div>
      <div className="mono" style={{ fontWeight: 600, marginTop: 4 }}>
        <span dangerouslySetInnerHTML={safeHtml(highlight(hit.title, query))} />
      </div>
      {hit.subtitle && (
        <div className="muted" style={{ marginTop: 2, fontSize: 12.5 }}>
          {hit.subtitle}
        </div>
      )}
      <div style={{ marginTop: 8 }}>
        <PathCode path={hit.match} />
      </div>
    </Card>
  );
}
