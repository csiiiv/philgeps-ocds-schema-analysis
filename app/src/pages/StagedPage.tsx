import { useState } from "react";
import { bundle, getCanonicalField } from "../data/bundle";
import type { StagedBlock, GeneratedFieldSpec } from "../data/types";
import { PageHeader, SectionHeader } from "../components/Layout";
import { Card, Badge, PathCode, SchemaPills, TypeBadge } from "../components/ui";
import { SearchInput, RowCount } from "../components/filters";
import { highlight, safeHtml } from "../components/helpers";

const BLOCK_DESCRIPTIONS: Record<string, string> = {
  planning: "Pre-solicitation budget and project context. Emitted when any planning trigger is non-null.",
  buyer: "The procuring entity (organization). Identifier sourced from UACS code.",
  tender: "The bid notice: opportunities, periods, items, classifications.",
  awards: "Contract award decision and supplier.",
  contracts: "Signed contract and its period / value.",
  bids: "Bidders list, emitted through the bids extension.",
  philgeps_extension: "PhilGEPS-specific fields with no native OCDS home (future registered extension).",
};

export function StagedPage() {
  const staged = bundle.ocds_staged;
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();

  const filteredBlocks = staged.blocks
    .map((b) => ({
      ...b,
      paths: b.paths.filter(
        (p) =>
          !q ||
          p.path.toLowerCase().includes(q) ||
          p.canonical.toLowerCase().includes(q),
      ),
    }))
    .filter((b) => b.paths.length > 0 || !q);

  return (
    <>
      <PageHeader
        title="OCDS staged output"
        subtitle="How canonical fields are placed into OCDS 1.1.5 paths, block by block. This is the live rendering of config/canonical_to_ocds.yaml — the canonical → OCDS staging rules an OCDS compiler consumes. Includes compiler-generated fields, planning triggers, and defaults."
      />

      <SectionHeader
        title="Compiler configuration"
        subtitle="Release-wide settings sourced from the YAML header."
      />
      <div className="card-grid cols-3">
        <Card>
          <div className="card-title">Mapping version</div>
          <div className="card-value" style={{ fontSize: 20 }}>
            <Badge variant="blue">{staged.version}</Badge>
          </div>
        </Card>
        <Card>
          <div className="card-title">OCID prefix</div>
          <div className="card-value mono" style={{ fontSize: 18 }}>
            {staged.ocid_prefix}
          </div>
        </Card>
        <Card>
          <div className="card-title">Extensions</div>
          <div style={{ fontSize: 12.5 }}>
            {staged.extensions.length === 0 ? (
              <span className="muted">None</span>
            ) : (
              staged.extensions.map((url) => (
                <div key={url}>
                  <a href={url} target="_blank" rel="noreferrer" className="mono">
                    {url.split("/").slice(-2, -1)[0]}
                  </a>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      <SectionHeader title="Defaults" subtitle="From config/ocds_codelist_mappings.yaml." />
      <Card>
        <dl className="kv-list">
          {Object.entries(staged.defaults).map(([k, v]) => (
            <div key={k} style={{ display: "contents" }}>
              <dt className="mono">{k}</dt>
              <dd className="mono">{Array.isArray(v) ? v.join(", ") : v}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <SectionHeader title="Generated fields" subtitle="Emitted by the compiler, not read from canonical rows." />
      <div className="card-grid cols-3">
        {staged.generated.map((g) => (
          <GeneratedCard key={g.field} spec={g} />
        ))}
      </div>

      <SectionHeader title="Planning triggers" subtitle="If any of these canonical fields is non-null, the planning block is emitted." />
      <Card>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {staged.planning_triggers.map((t) => (
            <Badge key={t} variant="outline">
              {t}
            </Badge>
          ))}
        </div>
      </Card>

      <SectionHeader
        title="OCDS blocks"
        subtitle="Each block lists its OCDS paths and the canonical field that fills them."
      />
      <div className="toolbar">
        <SearchInput
          value={query}
          onChange={setQuery}
          placeholder="Filter paths or canonical fields…"
          autoFocus
        />
        <span className="spacer" />
        <RowCount count={filteredBlocks.reduce((n, b) => n + b.paths.length, 0)} total={staged.blocks.reduce((n, b) => n + b.paths.length, 0)} />
      </div>

      <div className="card-grid cols-2">
        {filteredBlocks.map((b) => (
          <BlockCard key={b.block} block={b} query={q} />
        ))}
      </div>
    </>
  );
}

function GeneratedCard({ spec }: { spec: GeneratedFieldSpec }) {
  const detail = formatSpec(spec.spec);
  return (
    <Card>
      <div className="card-title">
        <PathCode path={spec.field} />
      </div>
      <div style={{ marginTop: 6 }}>
        {Array.isArray(detail) ? (
          <>
            <span className="muted" style={{ fontSize: 12 }}>
              from:
            </span>{" "}
            {detail.map((d, i) => (
              <Badge key={i} variant="outline">
                {d}
              </Badge>
            ))}
          </>
        ) : (
          <span className="mono">{detail}</span>
        )}
      </div>
    </Card>
  );
}

function formatSpec(spec: unknown): string | string[] {
  if (typeof spec === "string") return spec;
  if (spec && typeof spec === "object") {
    const s = spec as Record<string, unknown>;
    if (Array.isArray(s.from)) return s.from as string[];
    if (Array.isArray(s.prefer)) return s.prefer as string[];
  }
  return JSON.stringify(spec);
}

function BlockCard({ block, query }: { block: StagedBlock; query: string }) {
  return (
    <Card>
      <div className="card-title">
        <Badge variant="purple">{block.block}</Badge>
        <span style={{ marginLeft: 6, fontSize: 11.5, color: "var(--text-subtle)" }}>
          {block.paths.length} path{block.paths.length === 1 ? "" : "s"}
        </span>
      </div>
      <div style={{ fontSize: 12.5, color: "var(--text-muted)", marginBottom: 10 }}>
        {BLOCK_DESCRIPTIONS[block.block] ?? ""}
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
        <tbody>
          {block.paths.map((p, i) => {
            const canonicalField = getCanonicalField(p.canonical);
            return (
              <tr key={i}>
                <td style={{ padding: "5px 8px 5px 0", verticalAlign: "top", width: "44%" }}>
                  <PathCode path={p.path} />
                </td>
                <td style={{ padding: "5px 0", verticalAlign: "top" }}>
                  <span className="mono">→</span>
                </td>
                <td style={{ padding: "5px 0 5px 8px", verticalAlign: "top" }}>
                  <span
                    className="mono"
                    dangerouslySetInnerHTML={safeHtml(highlight(p.canonical, query))}
                  />
                  {canonicalField && (
                    <div style={{ marginTop: 3, display: "flex", gap: 4, alignItems: "center", flexWrap: "wrap" }}>
                      <TypeBadge type={canonicalField.field_type} />
                      <SchemaPills presentIn={canonicalField.present_in_schemas} />
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}
