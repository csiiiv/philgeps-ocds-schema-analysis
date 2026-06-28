import { bundle } from "../data/bundle";
import { PageHeader, SectionHeader, navigate } from "../components/Layout";
import { Card, Badge } from "../components/ui";
import { SCHEMA_SHORT_KEYS } from "../data/bundle";
import { SCHEMA_KEY_LIST } from "../data/bundle";

export function OverviewPage() {
  const s = bundle.summary;
  const meta = bundle.metadata;
  return (
    <>
      <PageHeader
        title="PhilGEPS schema explorer"
        subtitle="Interactive reference for the evolution of Philippine government procurement open-data exports (2000–2025) and their mapping to a canonical field model and OCDS 1.1.5. Filter, search, and trace any column across schemas and into OCDS."
      />

      <SectionHeader title="At a glance" />

      <div className="card-grid cols-4">
        <SummaryCard
          label="Schema periods"
          value={s.schema_count}
          sub="S1–S5 (2000–2025)"
          onClick={() => navigate("periods")}
        />
        <SummaryCard
          label="Canonical fields"
          value={s.canonical_field_count}
          sub="Open-data normalized fields"
          onClick={() => navigate("canonical")}
        />
        <SummaryCard
          label="Crosswalk rows"
          value={s.crosswalk_row_count}
          sub={`${s.crosswalk_with_ocds} with OCDS path`}
          onClick={() => navigate("crosswalk")}
        />
        <SummaryCard
          label="OCDS blocks"
          value={s.staged_block_count}
          sub="Staged canonical → OCDS"
          onClick={() => navigate("staged")}
        />
      </div>

      <div className="card-grid cols-4" style={{ marginTop: 14 }}>
        <SummaryCard
          label="Mapped"
          value={s.crosswalk_mapped}
          sub="Open-data mapping"
          variant="green"
          onClick={() => navigate("crosswalk")}
        />
        <SummaryCard
          label="Derived"
          value={s.crosswalk_derived}
          sub="slug() identifiers"
          variant="purple"
          onClick={() => navigate("crosswalk")}
        />
        <SummaryCard
          label="Extension"
          value={s.crosswalk_extension}
          sub="PhilGEPS extension"
          variant="teal"
          onClick={() => navigate("crosswalk")}
        />
        <SummaryCard
          label="Omitted"
          value={s.crosswalk_omit}
          sub="Not in flat open CSV"
          variant="amber"
          onClick={() => navigate("crosswalk")}
        />
      </div>

      <SectionHeader
        title="Data flow"
        subtitle="Four layers move from raw exports to OCDS-ready records. A reference ETL pipeline can materialize the full corpus locally."
      />
      <div className="flow-diagram">
        <FlowStep
          title="1. Raw exports"
          body="Google Drive XLSX (2000–2020) and CSV (2021–2025 V1/V2). Not in this repo."
        />
        <FlowArrow />
        <FlowStep
          title="2. Schema analysis"
          body={`S1–S5 periods. Map by column name, never by index.`}
          onClick={() => navigate("periods")}
        />
        <FlowArrow />
        <FlowStep
          title="3. Canonical fields"
          body={`${s.canonical_field_count} normalized fields that any export year maps into.`}
          onClick={() => navigate("canonical")}
        />
        <FlowArrow />
        <FlowStep
          title="4. OCDS 1.1.5"
          body="Canonical → OCDS staged paths and codelist transforms."
          onClick={() => navigate("staged")}
        />
        {s.transform_available && (
          <>
            <FlowArrow />
            <FlowStep
              title="5. ETL output"
              body={
                s.transform_scope === "full_dataset"
                  ? `${(s.transform_release_count ?? 0).toLocaleString()} releases across ${s.transform_calendar_year_count ?? 0} years — browse in ETL Pipeline.`
                  : "Local transform output embedded — browse in ETL Pipeline."
              }
              onClick={() => navigate("etl-overview")}
            />
          </>
        )}
      </div>

      {s.transform_available && (
        <>
          <SectionHeader
            title="Transform output"
            subtitle="Stats from the latest embedded run report. Open ETL Pipeline for DQ findings and the Release browser."
          />
          <div className="card-grid cols-4">
            <SummaryCard
              label="Releases compiled"
              value={s.transform_release_count ?? 0}
              sub={
                s.transform_scope === "full_dataset"
                  ? `${(s.transform_calendar_year_count ?? 0).toLocaleString()} calendar years`
                  : "Single export run"
              }
              onClick={() => navigate("etl-overview")}
            />
            <SummaryCard
              label="Release browser"
              value={s.transform_calendar_year_count ?? 0}
              sub="Calendar years · #/etl-releases/{year}"
              variant="teal"
              onClick={() => navigate("etl-releases")}
            />
            {s.transform_scope === "full_dataset" && (
              <SummaryCard
                label="Source files"
                value={s.transform_source_file_count ?? 0}
                sub="Raw exports transformed"
                variant="purple"
                onClick={() => navigate("etl-overview")}
              />
            )}
          </div>
        </>
      )}

      <SectionHeader
        title="Schema periods"
        subtitle="Five export eras. Column count grew from 40 to 46 over 25 years."
      />
      <div className="table-wrap">
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>Key</th>
                <th>Period</th>
                <th>Format</th>
                <th>Cols</th>
                <th>Key change</th>
              </tr>
            </thead>
            <tbody>
              {SCHEMA_KEY_LIST.map((k) => {
                const p = bundle.schemas[k];
                return (
                  <tr key={k} onClick={() => navigate("periods")} style={{ cursor: "pointer" }}>
                    <td>
                      <Badge variant="blue">{SCHEMA_SHORT_KEYS[k]}</Badge>
                    </td>
                    <td className="mono">{p.period}</td>
                    <td className="mono muted">{p.format}</td>
                    <td className="mono">{p.columns}</td>
                    <td>{p.key_change}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <SectionHeader title="About this mapping" subtitle="" />
      <div className="card-grid cols-2">
        <Card>
          <div className="card-title">What is canonical?</div>
          <div className="card-body">
            A single normalized field set that hides the churn of column renames, removals, and
            additions across the five export eras. A canonical field like{" "}
            <code>procuring_entity</code> is sourced from <code>Organization Name</code> (S1–S2),
            <code> Procuring Entity</code> (S3), or <code>Procuring Entity (PE)</code> (S4–S5).
            <br />
            <br />
            Rule: <strong>always map by column name, never by column index.</strong>
          </div>
        </Card>
        <Card>
          <div className="card-title">What is OCDS staging?</div>
          <div className="card-body">
            Canonical fields are placed into OCDS 1.1.5 paths by block — <code>tender</code>,{" "}
            <code>awards</code>, <code>contracts</code>, <code>planning</code>, <code>buyer</code>,
            <code> bids</code>. PhilGEPS-specific fields with no OCDS home (e.g.{" "}
            <code>trade_agreement</code>) are emitted through a{" "}
            <code>philgeps_extension</code> block.
            <br />
            <br />
            Status and method codelists are translated via{" "}
            <code>config/ocds_codelist_mappings.yaml</code>.
          </div>
        </Card>
        {bundle.transform && (
          <Card interactive onClick={() => navigate("etl-overview")}>
            <div className="card-title">ETL pipeline output</div>
            <div className="card-body">
              When a local ETL run is embedded, the <strong>ETL Pipeline</strong> section shows
              pipeline overview, year/overall data quality, and a{" "}
              <strong>Release browser</strong> at <code>#/etl-releases/&#123;year&#125;</code>
              {bundle.transform.scope === "full_dataset" ? " (25 calendar years, ~3.6M releases)" : ""}
              — searchable releases with structured summaries and Raw JSON on demand.
            </div>
          </Card>
        )}
      </div>

      <SectionHeader title="Mapping metadata" />
      <div className="card">
        <dl className="kv-list">
          <dt>OCDS template</dt>
          <dd>{meta.ocds_template}</dd>
          <dt>Mapping version</dt>
          <dd>
            <Badge variant="blue">{meta.ocds_mapping_version}</Badge>
          </dd>
          <dt>OCID prefix</dt>
          <dd className="mono">{meta.ocid_prefix}</dd>
          <dt>Schema analysis date</dt>
          <dd className="mono">{meta.schema_analysis_date}</dd>
          <dt>Bundle generated</dt>
          <dd className="mono">{meta.generated_at}</dd>
        </dl>
      </div>
    </>
  );
}

function SummaryCard({
  label,
  value,
  sub,
  variant,
  onClick,
}: {
  label: string;
  value: number;
  sub: string;
  variant?: "green" | "amber" | "purple" | "teal";
  onClick?: () => void;
}) {
  return (
    <Card interactive onClick={onClick}>
      <div className="card-title">
        {variant && <span className={`dot ${variant}`} />}
        {label}
      </div>
      <div className="card-value">{value.toLocaleString()}</div>
      <div className="card-sub">{sub}</div>
    </Card>
  );
}

function FlowStep({ title, body, onClick }: { title: string; body: string; onClick?: () => void }) {
  return (
    <div className="flow-step" onClick={onClick} style={onClick ? { cursor: "pointer" } : undefined}>
      <h4>{title}</h4>
      <p>{body}</p>
    </div>
  );
}

function FlowArrow() {
  return <div className="flow-arrow">→</div>;
}
