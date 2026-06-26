import { bundle } from "../data/bundle";
import type { OcdsReleaseSummary } from "../data/types";
import { PageHeader, SectionHeader } from "../components/Layout";
import { Card, Badge } from "../components/ui";
import { JsonView, JsonBlock } from "../components/JsonView";

const ANCHOR_BLOCKS: { key: string; label: string; description: string }[] = [
  { key: "ocid", label: "Header", description: "ocid, release id, date, initiationType, tag" },
  { key: "planning", label: "planning", description: "Budget and project context" },
  { key: "buyer", label: "buyer", description: "Procuring entity" },
  { key: "tender", label: "tender", description: "Bid notice, periods, items" },
  { key: "awards", label: "awards", description: "Award decision, suppliers, items" },
  { key: "contracts", label: "contracts", description: "Signed contract, period, value" },
  { key: "bids", label: "bids", description: "Bidders (bids extension)" },
  { key: "parties", label: "parties", description: "Organizations and roles" },
  { key: "philgeps", label: "philgeps", description: "PhilGEPS extension block" },
];

export function ReleasePage() {
  const { package: pkg, release, summary } = bundle.ocds_release;

  return (
    <>
      <PageHeader
        title="OCDS release package"
        subtitle="What the final OCDS output looks like once the canonical → OCDS staging rules and codelist transforms are applied. This is a representative sample release — one line-item award against a single bid notice — compiled by walking config/canonical_to_ocds.yaml."
      />

      <SectionHeader
        title="Release overview"
        subtitle="Top-level facts about the compiled release and its package wrapper."
      />
      <div className="card-grid cols-4">
        <SummaryCard label="OCDS version" value={summary.version} mono />
        <SummaryCard label="Initiation" value={summary.initiation_type} mono />
        <SummaryCard label="Tag" value={(summary.tag ?? []).join(", ")} mono />
        <SummaryCard label="Language" value={summary.language} mono />
      </div>
      <div className="card-grid cols-4" style={{ marginTop: 14 }}>
        <CountCard label="Tender items" n={summary.tender_item_count} />
        <CountCard label="Awards" n={summary.award_count} />
        <CountCard label="Contracts" n={summary.contract_count} />
        <CountCard label="Parties" n={summary.party_count} />
      </div>

      <SectionHeader title="Identifiers" />
      <Card>
        <dl className="kv-list">
          <dt>ocid</dt>
          <dd className="mono">{summary.ocid}</dd>
          <dt>release id</dt>
          <dd className="mono">{summary.release_id}</dd>
          <dt>release date</dt>
          <dd className="mono">{summary.release_date}</dd>
          <dt>publisher</dt>
          <dd>{summary.publisher}</dd>
          <dt>extensions</dt>
          <dd>
            {summary.extensions.length === 0 ? (
              <span className="muted">none</span>
            ) : (
              summary.extensions.map((url) => (
                <div key={url}>
                  <a href={url} target="_blank" rel="noreferrer" className="mono">
                    {url.split("/").slice(-2, -1)[0]}
                  </a>
                </div>
              ))
            )}
          </dd>
        </dl>
      </Card>

      <SectionHeader
        title="Jump to block"
        subtitle="Each link scrolls to the highlighted JSON for that OCDS block."
      />
      <div className="block-jumps">
        {ANCHOR_BLOCKS.map((b) => {
          const present = blockIsPresent(release, b.key);
          return (
            <a
              key={b.key}
              href={present ? `#block-${b.key}` : undefined}
              className="block-jump"
              style={present ? undefined : { opacity: 0.4, cursor: "not-allowed" }}
              title={present ? b.description : "Not present in this release"}
            >
              {b.label}
              {!present && <span style={{ marginLeft: 2 }}>·</span>}
            </a>
          );
        })}
      </div>

      <SectionHeader
        title="Full package"
        subtitle="The complete release package wrapper, including publisher, license, and extensions."
      />
      <JsonView value={pkg} filename="ocds-release-package.json" />

      <SectionHeader
        title="Blocks"
        subtitle="Each OCDS block in the release, rendered separately with its own copy and download."
      />
      {ANCHOR_BLOCKS.filter((b) => b.key !== "ocid").map((b) => {
        const value = (release as Record<string, unknown>)[b.key];
        if (value === undefined) {
          return (
            <JsonBlock
              key={b.key}
              id={`block-${b.key}`}
              anchor={b.key}
              title={b.label}
              value={null}
              defaultExpanded={false}
            />
          );
        }
        return (
          <JsonBlock
            key={b.key}
            id={`block-${b.key}`}
            anchor={b.key}
            title={b.label}
            value={value}
          />
        );
      })}
    </>
  );
}

function blockIsPresent(release: Record<string, unknown>, key: string): boolean {
  return release[key] !== undefined;
}

function SummaryCard({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <Card>
      <div className="card-title">{label}</div>
      <div className="card-value" style={{ fontSize: 18 }}>
        <Badge variant="blue">{mono ? <span className="mono">{value}</span> : value}</Badge>
      </div>
    </Card>
  );
}

function CountCard({ label, n }: { label: string; n: number }) {
  return (
    <Card>
      <div className="card-title">{label}</div>
      <div className="card-value">{n}</div>
    </Card>
  );
}

export function getReleaseSummary(): OcdsReleaseSummary {
  return bundle.ocds_release.summary;
}
