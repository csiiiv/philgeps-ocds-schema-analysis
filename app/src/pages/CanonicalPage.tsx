import { useMemo, useState } from "react";
import { bundle, SCHEMA_KEY_LIST, SCHEMA_SHORT_KEYS } from "../data/bundle";
import type { CanonicalField, SchemaKey } from "../data/types";
import { PageHeader } from "../components/Layout";
import { DataTable, EmptyState } from "../components/Table";
import { SearchInput, SelectInput, ChipFilter, RowCount } from "../components/filters";
import { Badge, TypeBadge, SchemaPills, PathCode } from "../components/ui";
import { classNames, emDashIfEmpty, highlight, safeHtml } from "../components/helpers";

type TypeFilter = "string" | "decimal" | "integer" | "date" | "datetime" | "string_array" | "excluded" | "extension";
type SchemaFilter = SchemaKey;

export function CanonicalPage() {
  const fields = bundle.canonical_fields;
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<TypeFilter | "all">("all");
  const [schemaFilter, setSchemaFilter] = useState<SchemaFilter | "all">("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  const categories = useMemo(
    () =>
      Array.from(new Set(fields.map((f) => f.category).filter(Boolean))) as string[],
    [fields],
  );
  const [categoryFilter, setCategoryFilter] = useState<string | "all">("all");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return fields.filter((f) => {
      if (q) {
        const hay = [
          f.canonical_field,
          f.semantic_name ?? "",
          f.category ?? "",
          f.evolution_notes ?? "",
          ...Object.values(f.source_columns).filter(Boolean),
          ...f.ocds_paths,
        ]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (typeFilter !== "all") {
        if (typeFilter === "excluded" && !f.excluded) return false;
        if (typeFilter === "extension" && !f.canonical_ai.includes("[extension]")) return false;
        if (
          typeFilter !== "excluded" &&
          typeFilter !== "extension" &&
          f.field_type !== typeFilter
        )
          return false;
      }
      if (schemaFilter !== "all" && !f.present_in_schemas.includes(schemaFilter)) return false;
      if (categoryFilter !== "all" && f.category !== categoryFilter) return false;
      return true;
    });
  }, [fields, query, typeFilter, schemaFilter, categoryFilter]);

  return (
    <>
      <PageHeader
        title="Canonical fields"
        subtitle="The 53 normalized open-data fields. Each canonical field has one source column per schema (S1–S5), zero or more OCDS paths, and optional evolution notes. Click a row for full detail."
      />

      <div className="toolbar">
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder="Search field, column, OCDS path…"
          autoFocus
        />
        <SelectInput
          ariaLabel="Filter by schema"
          value={schemaFilter}
          onChange={setSchemaFilter}
          allLabel="All schemas"
          options={SCHEMA_KEY_LIST.map((k) => ({
            value: k,
            label: `${SCHEMA_SHORT_KEYS[k]} · ${bundle.schemas[k].period}`,
          }))}
        />
        <SelectInput
          ariaLabel="Filter by category"
          value={categoryFilter}
          onChange={setCategoryFilter}
          allLabel="All categories"
          options={categories.sort().map((c) => ({ value: c, label: c }))}
        />
        <span className="spacer" />
        <RowCount count={filtered.length} total={fields.length} />
      </div>

      <div className="toolbar" style={{ marginTop: -6 }}>
        <ChipFilter
          value={typeFilter}
          onChange={setTypeFilter}
          options={[
            { value: "string", label: "string" },
            { value: "decimal", label: "decimal" },
            { value: "integer", label: "integer" },
            { value: "date", label: "date" },
            { value: "datetime", label: "datetime" },
            { value: "string_array", label: "string[]" },
            { value: "extension", label: "extension" },
            { value: "excluded", label: "excluded" },
          ]}
        />
      </div>

      {filtered.length === 0 ? (
        <EmptyState>No canonical fields match the current filters.</EmptyState>
      ) : (
        <DataTable
          head={[
            "Canonical field",
            "Type",
            "S1–S5",
            "Category",
            "OCDS paths",
            "",
          ]}
          minWidth={860}
        >
          {filtered.map((f) => {
            const isExpanded = expanded === f.canonical_field;
            return (
              <FieldRow
                key={f.canonical_field}
                field={f}
                query={query}
                expanded={isExpanded}
                onToggle={() => setExpanded(isExpanded ? null : f.canonical_field)}
              />
            );
          })}
        </DataTable>
      )}
    </>
  );
}

function FieldRow({
  field,
  query,
  expanded,
  onToggle,
}: {
  field: CanonicalField;
  query: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr onClick={onToggle} style={{ cursor: "pointer" }}>
        <td>
          <span dangerouslySetInnerHTML={safeHtml(highlight(field.canonical_field, query))} />
          {field.excluded && (
            <span style={{ marginLeft: 6 }}>
              <Badge variant="amber">excluded</Badge>
            </span>
          )}
          {field.canonical_ai.includes("[extension]") && (
            <span style={{ marginLeft: 6 }}>
              <Badge variant="teal">extension</Badge>
            </span>
          )}
        </td>
        <td>
          <TypeBadge type={field.field_type} />
        </td>
        <td>
          <SchemaPills presentIn={field.present_in_schemas} titleFor={field.source_columns} />
        </td>
        <td className="muted">{field.category ?? "—"}</td>
        <td>
          {field.ocds_paths.length === 0 ? (
            <span className="em-dash">—</span>
          ) : (
            <span style={{ display: "inline-flex", gap: 4, flexWrap: "wrap" }}>
              {field.ocds_paths.slice(0, 2).map((p, i) => (
                <PathCode key={i} path={p} />
              ))}
              {field.ocds_paths.length > 2 && (
                <Badge variant="outline">+{field.ocds_paths.length - 2}</Badge>
              )}
            </span>
          )}
        </td>
        <td style={{ textAlign: "right", color: "var(--text-subtle)" }}>
          {expanded ? "▲" : "▼"}
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={6} style={{ padding: 0 }}>
            <ExpandedField field={field} />
          </td>
        </tr>
      )}
    </>
  );
}

function ExpandedField({ field }: { field: CanonicalField }) {
  return (
    <div className="expandable-content">
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginTop: 4 }}>
        <div>
          <h5 style={h5}>Semantic name</h5>
          <div>{field.semantic_name ?? "—"}</div>
          {field.evolution_notes && (
            <>
              <h5 style={h5}>Evolution notes</h5>
              <div className="muted">{field.evolution_notes}</div>
            </>
          )}
          <h5 style={h5}>Canonical AI hint</h5>
          <div className="mono" style={{ fontSize: 12 }}>
            {field.canonical_ai}
          </div>
        </div>
        <div>
          <h5 style={h5}>Source columns by schema</h5>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
            <tbody>
              {SCHEMA_KEY_LIST.map((k) => (
                <tr key={k}>
                  <td style={{ padding: "3px 8px 3px 0", width: 40 }}>
                    <span className={classNames("schema-pill", field.source_columns[k] && "on")}>
                      {SCHEMA_SHORT_KEYS[k]}
                    </span>
                  </td>
                  <td className="mono" style={{ padding: "3px 0", color: field.source_columns[k] ? "var(--text)" : "var(--text-subtle)" }}>
                    {emDashIfEmpty(field.source_columns[k])}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {field.ocds_paths.length > 0 && (
            <>
              <h5 style={h5}>OCDS paths</h5>
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {field.ocds_paths.map((p, i) => (
                  <PathCode key={i} path={p} />
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

const h5: React.CSSProperties = {
  margin: "10px 0 3px",
  fontSize: 11,
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: 0.4,
  color: "var(--text-muted)",
};
