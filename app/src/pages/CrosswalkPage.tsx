import { useMemo, useState } from "react";
import { bundle } from "../data/bundle";
import type { CrosswalkRow, CrosswalkStatus } from "../data/types";
import { PageHeader, SectionHeader } from "../components/Layout";
import { DataTable, EmptyState } from "../components/Table";
import { SearchInput, ChipFilter, RowCount, SelectInput } from "../components/filters";
import { Badge, Dot, PathCode, EmDash } from "../components/ui";
import { statusMeta, highlight, safeHtml, isPresent } from "../components/helpers";

export function CrosswalkPage() {
  const rows = bundle.ocds_crosswalk;
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<CrosswalkStatus | "all">("all");
  const [block, setBlock] = useState<string | "all">("all");

  const blocks = useMemo(
    () => Array.from(new Set(rows.map((r) => r.ocds_block))).sort(),
    [rows],
  );

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const r of rows) counts[r.status] = (counts[r.status] ?? 0) + 1;
    return counts;
  }, [rows]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return rows.filter((r) => {
      if (q) {
        const hay = [
          r.ocds_field,
          r.philgeps_1_5,
          r.philgeps_2_0,
          r.v2_csv,
          r.v1_csv,
          r.canonical,
        ]
          .join(" ")
          .toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (status !== "all" && r.status !== status) return false;
      if (block !== "all" && r.ocds_block !== block) return false;
      return true;
    });
  }, [rows, query, status, block]);

  return (
    <>
      <PageHeader
        title="OCDS ↔ PhilGEPS crosswalk"
        subtitle="151-row join of OCDS paths against PhilGEPS 1.5, PhilGEPS 2.0, V2 CSV, V1 CSV, and the canonical field. The interactive replacement for the giant markdown table in references/PHILGEPS_OCDS_CSV_CROSSWALK.md."
      />

      <SectionHeader title="Filter by status" subtitle="Counts shown next to each chip." />
      <ChipFilter
        value={status}
        onChange={setStatus}
        options={[
          { value: "mapped", label: "Mapped", count: statusCounts.mapped ?? 0, dot: "green" },
          { value: "omit", label: "Omit", count: statusCounts.omit ?? 0, dot: "gray" },
          { value: "derived", label: "Derived", count: statusCounts.derived ?? 0, dot: "purple" },
          { value: "extension", label: "Extension", count: statusCounts.extension ?? 0, dot: "blue" },
          { value: "constant", label: "Constant", count: statusCounts.constant ?? 0, dot: "blue" },
          { value: "unmapped", label: "Unmapped", count: statusCounts.unmapped ?? 0, dot: "amber" },
        ]}
      />

      <div className="toolbar" style={{ marginTop: 14 }}>
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder="Search OCDS path, PhilGEPS column, canonical…"
          autoFocus
        />
        <SelectInput
          ariaLabel="Filter by OCDS block"
          value={block}
          onChange={setBlock}
          allLabel="All OCDS blocks"
          options={blocks.map((b) => ({ value: b, label: `${b}/` }))}
        />
        <span className="spacer" />
        <RowCount count={filtered.length} total={rows.length} />
      </div>

      {filtered.length === 0 ? (
        <EmptyState>No crosswalk rows match the current filters.</EmptyState>
      ) : (
        <DataTable
          head={["OCDS path", "Status", "PhilGEPS 1.5", "PhilGEPS 2.0", "V2 CSV", "V1 CSV", "Canonical resolution"]}
          minWidth={1100}
        >
          {filtered.map((row, i) => (
            <CrosswalkRowView key={i} row={row} query={query} />
          ))}
        </DataTable>
      )}
    </>
  );
}

function CrosswalkRowView({ row, query }: { row: CrosswalkRow; query: string }) {
  const meta = statusMeta(row.status);
  const hasOcds = row.ocds_field !== "—";
  return (
    <tr>
      <td>
        {hasOcds ? (
          <PathCode path={row.ocds_field} />
        ) : (
          <span className="muted mono" style={{ fontStyle: "italic" }}>
            (no OCDS path)
          </span>
        )}
      </td>
      <td>
        <Badge variant={meta.badge}>
          <Dot variant={meta.dot} />
          {meta.label}
        </Badge>
      </td>
      <td className="mono">{cell(row.philgeps_1_5, query)}</td>
      <td className="mono">{cell(row.philgeps_2_0, query)}</td>
      <td className="mono">{cell(row.v2_csv, query)}</td>
      <td className="mono">{cell(row.v1_csv, query)}</td>
      <td className="muted">{highlightAndClean(row.canonical, query)}</td>
    </tr>
  );
}

function cell(value: string, query: string) {
  if (!isPresent(value)) return <EmDash />;
  return <span dangerouslySetInnerHTML={safeHtml(highlight(value, query))} />;
}

function highlightAndClean(value: string, query: string) {
  return <span dangerouslySetInnerHTML={safeHtml(highlight(value, query))} />;
}
