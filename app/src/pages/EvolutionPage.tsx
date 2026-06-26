import { useMemo, useState } from "react";
import { bundle } from "../data/bundle";
import type { SemanticFieldEntry } from "../data/types";
import { PageHeader, SectionHeader } from "../components/Layout";
import { DataTable, EmptyState } from "../components/Table";
import { SearchInput, SelectInput, RowCount } from "../components/filters";
import { Badge } from "../components/ui";
import { highlight, safeHtml, isPresent } from "../components/helpers";

type ChangeType = "stable" | "added" | "removed" | "renamed" | "other";

function classifyChange(e: SemanticFieldEntry): ChangeType {
  const hasOld = isPresent(e.schema_1_2_2000_2020);
  const hasMid = isPresent(e.schema_3_2021_2024);
  const hasNew = isPresent(e.schema_4_5_2025_v2);
  const notes = (e.evolution_notes ?? "").toLowerCase();
  if (notes.includes("new")) return "added";
  if (notes.includes("removed")) return "removed";
  if (notes.includes("rename")) return "renamed";
  if (!hasOld && !hasMid && hasNew) return "added";
  if (hasOld && !hasNew && !hasMid) return "removed";
  if (hasOld && hasNew && e.schema_1_2_2000_2020 !== e.schema_4_5_2025_v2) return "renamed";
  if (hasOld && hasMid && hasNew && e.schema_1_2_2000_2020 === e.schema_4_5_2025_v2) return "stable";
  return "other";
}

export function EvolutionPage() {
  const groups = bundle.semantic_grouping;
  const [query, setQuery] = useState("");
  const [change, setChange] = useState<ChangeType | "all">("all");
  const [category, setCategory] = useState<string | "all">("all");

  const categories = useMemo(
    () => groups.map((g) => g.category).sort(),
    [groups],
  );

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return groups
      .filter((g) => category === "all" || g.category === category)
      .flatMap((g) =>
        g.fields
          .map((f) => ({ ...f, category: g.category, changeType: classifyChange(f) }))
          .filter((f) => {
            if (change !== "all" && f.changeType !== change) return false;
            if (q) {
              const hay = `${f.field_name} ${f.schema_1_2_2000_2020 ?? ""} ${f.schema_3_2021_2024 ?? ""} ${f.schema_4_5_2025_v2 ?? ""} ${f.evolution_notes ?? ""}`.toLowerCase();
              if (!hay.includes(q)) return false;
            }
            return true;
          }),
      );
  }, [groups, query, change, category]);

  const changeCounts = useMemo(() => {
    const all = groups.flatMap((g) => g.fields.map((f) => classifyChange(f)));
    const counts: Record<string, number> = {};
    for (const c of all) counts[c] = (counts[c] ?? 0) + 1;
    return counts;
  }, [groups]);

  return (
    <>
      <PageHeader
        title="Schema evolution"
        subtitle="Field-level change across 25 years. Each semantic field is shown with its column name in S1–S2 (2000–2020), S3 (2021–2024), and S4–S5 (2025/V2), plus a derived change classification."
      />

      <SectionHeader title="Change mix" />
      <div className="card-grid cols-5">
        {(["stable", "added", "renamed", "removed", "other"] as ChangeType[]).map((c) => (
          <ChangeCard key={c} type={c} count={changeCounts[c] ?? 0} />
        ))}
      </div>

      <div className="toolbar" style={{ marginTop: 14 }}>
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder="Search semantic field, column, notes…"
          autoFocus
        />
        <SelectInput
          ariaLabel="Filter by change type"
          value={change}
          onChange={setChange}
          allLabel="All changes"
          options={[
            { value: "stable", label: "Stable" },
            { value: "added", label: "Added" },
            { value: "renamed", label: "Renamed" },
            { value: "removed", label: "Removed" },
            { value: "other", label: "Other" },
          ]}
        />
        <SelectInput
          ariaLabel="Filter by category"
          value={category}
          onChange={setCategory}
          allLabel="All categories"
          options={categories.map((c) => ({ value: c, label: c }))}
        />
        <span className="spacer" />
        <RowCount count={rows.length} total={groups.reduce((n, g) => n + g.fields.length, 0)} />
      </div>

      {rows.length === 0 ? (
        <EmptyState>No fields match.</EmptyState>
      ) : (
        <DataTable head={["Field", "Change", "Category", "S1–S2", "S3", "S4–S5", "Notes"]} minWidth={960}>
          {rows.map((f, i) => (
            <tr key={i}>
              <td>
                <span dangerouslySetInnerHTML={safeHtml(highlight(f.field_name, query))} />
              </td>
              <td>
                <ChangeBadge type={f.changeType} />
              </td>
              <td className="muted">{f.category}</td>
              <td className="mono">{col(f.schema_1_2_2000_2020)}</td>
              <td className="mono">{col(f.schema_3_2021_2024)}</td>
              <td className="mono">{col(f.schema_4_5_2025_v2)}</td>
              <td className="muted" style={{ maxWidth: 220 }}>
                {f.evolution_notes ?? ""}
              </td>
            </tr>
          ))}
        </DataTable>
      )}
    </>
  );
}

function col(v: string | null | undefined) {
  if (!isPresent(v)) return <span className="em-dash">—</span>;
  return v;
}

const CHANGE_META: Record<ChangeType, { label: string; badge: "" | "green" | "amber" | "red" | "blue" | "purple" | "teal" | "outline"; dot: "" | "green" | "amber" | "red" | "blue" | "purple" }> = {
  stable: { label: "Stable", badge: "green", dot: "green" },
  added: { label: "Added", badge: "blue", dot: "blue" },
  renamed: { label: "Renamed", badge: "amber", dot: "amber" },
  removed: { label: "Removed", badge: "red", dot: "red" },
  other: { label: "Other", badge: "purple", dot: "purple" },
};

function ChangeBadge({ type }: { type: ChangeType }) {
  const m = CHANGE_META[type];
  return (
    <Badge variant={m.badge}>
      <span className={`dot ${m.dot}`} />
      {m.label}
    </Badge>
  );
}

function ChangeCard({ type, count }: { type: ChangeType; count: number }) {
  const m = CHANGE_META[type];
  return (
    <div className="card">
      <div className="card-title">
        <span className={`dot ${m.dot}`} />
        {m.label}
      </div>
      <div className="card-value">{count}</div>
    </div>
  );
}
