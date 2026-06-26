import { useState } from "react";
import { bundle } from "../data/bundle";
import type { CodelistSection } from "../data/types";
import { PageHeader, SectionHeader } from "../components/Layout";
import { Card, Badge } from "../components/ui";
import { DataTable } from "../components/Table";
import { SearchInput, RowCount } from "../components/filters";

export function CodelistsPage() {
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();

  return (
    <>
      <PageHeader
        title="Codelist mappings"
        subtitle="PhilGEPS status, method, and category labels translated to OCDS 1.1 closed codelists. Source: config/ocds_codelist_mappings.yaml. Applied at OCDS compile time."
      />

      <SectionHeader title="Defaults" subtitle="Release-wide constants." />
      <Card>
        <dl className="kv-list">
          {Object.entries(bundle.ocds_staged.defaults).map(([k, v]) => (
            <div key={k} style={{ display: "contents" }}>
              <dt className="mono">{k}</dt>
              <dd className="mono">{Array.isArray(v) ? v.join(", ") : v}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <SectionHeader title="Codelists" />
      <div className="toolbar">
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder="Search PhilGEPS label or OCDS code…"
          autoFocus
        />
        <span className="spacer" />
        <RowCount
          count={bundle.codelists.reduce(
            (n, c) => n + c.entries.filter((e) => matchesCodelist(e, q)).length,
            0,
          )}
          total={bundle.codelists.reduce((n, c) => n + c.entries.length, 0)}
        />
      </div>

      <div className="card-grid cols-2">
        {bundle.codelists.map((c) => (
          <CodelistCard key={c.name} codelist={c} query={q} />
        ))}
      </div>
    </>
  );
}

function matchesCodelist(e: { philgeps: string; ocds: string }, q: string): boolean {
  if (!q) return true;
  return `${e.philgeps} ${e.ocds}`.toLowerCase().includes(q);
}

function CodelistCard({ codelist, query }: { codelist: CodelistSection; query: string }) {
  const entries = codelist.entries.filter((e) => matchesCodelist(e, query));
  return (
    <Card>
      <div className="card-title">
        <Badge variant="purple">{codelist.name}</Badge>
        <span style={{ marginLeft: 6 }}>{codelist.label}</span>
      </div>
      {entries.length === 0 ? (
        <div className="empty-state" style={{ padding: "16px 8px" }}>
          No matching entries.
        </div>
      ) : (
        <DataTable head={["PhilGEPS label", "OCDS code"]}>
          {entries.map((e, i) => (
            <tr key={i}>
              <td>{e.philgeps}</td>
              <td>
                <Badge variant="blue">{e.ocds}</Badge>
              </td>
            </tr>
          ))}
        </DataTable>
      )}
    </Card>
  );
}
