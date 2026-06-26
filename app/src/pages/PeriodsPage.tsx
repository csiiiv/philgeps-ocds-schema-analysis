import { useMemo, useState } from "react";
import { bundle, SCHEMA_KEY_LIST, SCHEMA_SHORT_KEYS } from "../data/bundle";
import type { SchemaKey } from "../data/types";
import { PageHeader, SectionHeader } from "../components/Layout";
import { DataTable, EmptyState } from "../components/Table";
import { SearchInput, RowCount } from "../components/filters";
import { Badge, PathCode } from "../components/ui";
import { highlight, safeHtml } from "../components/helpers";

export function PeriodsPage() {
  const [selected, setSelected] = useState<SchemaKey>("schema_4");
  const [query, setQuery] = useState("");

  const period = bundle.schemas[selected];
  const allColumns = useMemo(
    () => Object.entries(period.source_columns).sort(([a], [b]) => a.localeCompare(b)),
    [period],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return allColumns;
    return allColumns.filter(([col, canonical]) =>
      `${col} ${canonical}`.toLowerCase().includes(q),
    );
  }, [allColumns, query]);

  return (
    <>
      <PageHeader
        title="Schema periods (S1–S5)"
        subtitle="Five export eras spanning 25 years. Pick a schema to see every source column and the canonical field it normalizes to."
      />

      <div className="card-grid cols-5">
        {SCHEMA_KEY_LIST.map((k) => (
          <PeriodCard key={k} schemaKey={k} active={selected === k} onClick={() => setSelected(k)} />
        ))}
      </div>

      <SectionHeader
        title={`${SCHEMA_SHORT_KEYS[selected]} — ${period.period} columns`}
        subtitle={`${period.format} · ${period.columns} columns · ${period.key_change}`}
      />

      <div className="toolbar">
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder={`Search ${SCHEMA_SHORT_KEYS[selected]} columns…`}
          autoFocus
        />
        <span className="spacer" />
        <RowCount count={filtered.length} total={allColumns.length} />
      </div>

      {filtered.length === 0 ? (
        <EmptyState>No columns match.</EmptyState>
      ) : (
        <DataTable head={["Source column", "Canonical field"]} minWidth={520}>
          {filtered.map(([col, canonical]) => {
            const canonicalField = bundle.canonical_fields.find((f) => f.canonical_field === canonical);
            return (
              <tr key={col}>
                <td className="mono">
                  <span dangerouslySetInnerHTML={safeHtml(highlight(col, query))} />
                </td>
                <td>
                  <a href={`#/canonical`} className="mono">
                    <span dangerouslySetInnerHTML={safeHtml(highlight(canonical, query))} />
                  </a>
                  {canonicalField && canonicalField.ocds_paths.length > 0 && (
                    <span style={{ marginLeft: 8, display: "inline-flex", gap: 4, flexWrap: "wrap" }}>
                      {canonicalField.ocds_paths.slice(0, 2).map((p, i) => (
                        <PathCode key={i} path={p} />
                      ))}
                      {canonicalField.ocds_paths.length > 2 && (
                        <Badge variant="outline">+{canonicalField.ocds_paths.length - 2}</Badge>
                      )}
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </DataTable>
      )}
    </>
  );
}

function PeriodCard({
  schemaKey,
  active,
  onClick,
}: {
  schemaKey: SchemaKey;
  active: boolean;
  onClick: () => void;
}) {
  const p = bundle.schemas[schemaKey];
  return (
    <div
      onClick={onClick}
      className="card interactive"
      style={{
        cursor: "pointer",
        borderColor: active ? "var(--accent)" : undefined,
        boxShadow: active ? "0 0 0 1px var(--accent)" : undefined,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <Badge variant={active ? "blue" : "outline"}>{SCHEMA_SHORT_KEYS[schemaKey]}</Badge>
        <span className="muted mono" style={{ fontSize: 12 }}>{p.period}</span>
      </div>
      <div style={{ fontSize: 13, color: "var(--text-muted)" }}>{p.format}</div>
      <div style={{ fontSize: 12, color: "var(--text-subtle)", marginTop: 6 }}>{p.key_change}</div>
      <div style={{ fontSize: 22, fontWeight: 600, marginTop: 8 }}>{p.columns} cols</div>
    </div>
  );
}
