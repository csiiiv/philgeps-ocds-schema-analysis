import { useMemo, useState } from "react";
import { bundle, SCHEMA_KEY_LIST, SCHEMA_SHORT_KEYS } from "../data/bundle";
import type { SchemaKey } from "../data/types";
import { PageHeader, SectionHeader } from "../components/Layout";
import { Card, Badge, PathCode } from "../components/ui";
import { SearchInput, SelectInput } from "../components/filters";

interface LookupResult {
  schemaKey: SchemaKey;
  sourceColumn: string;
  canonical: string;
  canonicalField: (typeof bundle.canonical_fields)[number] | undefined;
}

export function LookupPage() {
  const [schema, setSchema] = useState<SchemaKey | "all">("all");
  const [query, setQuery] = useState("");

  const results = useMemo<LookupResult[]>(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const schemas: SchemaKey[] = schema === "all" ? SCHEMA_KEY_LIST : [schema];
    const out: LookupResult[] = [];
    for (const k of schemas) {
      const cols = bundle.schemas[k].source_columns;
      for (const [col, canonical] of Object.entries(cols)) {
        if (col.toLowerCase().includes(q)) {
          out.push({
            schemaKey: k,
            sourceColumn: col,
            canonical,
            canonicalField: bundle.canonical_fields.find((f) => f.canonical_field === canonical),
          });
        }
      }
    }
    return out.slice(0, 60);
  }, [schema, query]);

  return (
    <>
      <PageHeader
        title="Source column lookup"
        subtitle="The ingest-author tool: paste a CSV header (or part of one), optionally filter by schema, and see which canonical field it normalizes to and which OCDS path it eventually feeds."
      />

      <div className="toolbar">
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder="e.g. Procuring Entity, UOM, Awardee…"
          autoFocus
        />
        <SelectInput
          ariaLabel="Filter by schema"
          value={schema}
          onChange={setSchema}
          allLabel="All schemas"
          options={SCHEMA_KEY_LIST.map((k) => ({
            value: k,
            label: `${SCHEMA_SHORT_KEYS[k]} · ${bundle.schemas[k].period}`,
          }))}
        />
      </div>

      {query.trim() === "" ? (
        <Card>
          <div className="card-body muted">
            Start typing a column header to see matches across schemas.
          </div>
        </Card>
      ) : results.length === 0 ? (
        <Card>
          <div className="card-body muted">
            No source column matches “{query}”{schema !== "all" ? ` in ${SCHEMA_SHORT_KEYS[schema]}` : ""}.
          </div>
        </Card>
      ) : (
        <>
          <SectionHeader
            title={`${results.length}${results.length === 60 ? "+" : ""} match${results.length === 1 ? "" : "es"}`}
          />
          <div className="card-grid cols-2">
            {results.map((r, i) => (
              <LookupCard key={i} result={r} />
            ))}
          </div>
        </>
      )}
    </>
  );
}

function LookupCard({ result }: { result: LookupResult }) {
  const { schemaKey, sourceColumn, canonical, canonicalField } = result;
  return (
    <Card>
      <div className="card-title">
        <Badge variant="blue">{SCHEMA_SHORT_KEYS[schemaKey]}</Badge>
        <span className="mono">{sourceColumn}</span>
      </div>
      <div style={{ marginTop: 6 }}>
        <span className="muted" style={{ fontSize: 12 }}>
          canonical →
        </span>{" "}
        <a href="#/canonical" className="mono" style={{ fontWeight: 600 }}>
          {canonical}
        </a>
        {canonicalField && (
          <>
            {canonicalField.field_type && (
              <span style={{ marginLeft: 6 }}>
                <Badge variant="outline">{canonicalField.field_type}</Badge>
              </span>
            )}
            {canonicalField.excluded && (
              <span style={{ marginLeft: 6 }}>
                <Badge variant="amber">excluded</Badge>
              </span>
            )}
          </>
        )}
      </div>
      {canonicalField && canonicalField.ocds_paths.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div className="muted" style={{ fontSize: 12, marginBottom: 4 }}>
            OCDS paths
          </div>
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            {canonicalField.ocds_paths.map((p, i) => (
              <PathCode key={i} path={p} />
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
