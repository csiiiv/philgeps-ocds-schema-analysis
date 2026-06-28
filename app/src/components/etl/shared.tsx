import { useMemo, useState, type ReactNode } from "react";
import { bundle } from "../../data/bundle";
import type {
  TransformBundle,
  TransformRuleCount,
  TransformIssueGroupCount,
  TransformQuarantinedIssue,
  TransformQuarantinedSample,
  TransformYearSummary,
  RowAccounting,
} from "../../data/types";
import { PageHeader, SectionHeader } from "../Layout";
import { Card, Badge } from "../ui";
import { LazyJsonView, JsonView } from "../JsonView";

export const PIPELINE_STAGES: { n: number; label: string; desc: string }[] = [
  { n: 1, label: "Detect schema", desc: "Match header columns to S1–S5 marker sets" },
  { n: 2, label: "Map to canonical", desc: "Apply config/schema_mappings.yaml per detected schema" },
  { n: 3, label: "Data-quality gate", desc: "scripts/_data_quality.py inspects each row; errors quarantine" },
  { n: 4, label: "Group by process", desc: "bid_reference_no → solicitation_no → award_reference_no" },
  { n: 5, label: "Compile to OCDS", desc: "ocid/id from bid first; solicitation fallback" },
  { n: 6, label: "Resolve id collisions", desc: "Composite release.id + display_id_collision DQ when needed" },
  { n: 7, label: "Validate & write", desc: "Shape pre-flight; optional libcoveocds via --run-ocds-validate" },
  { n: 8, label: "Merge by year", desc: "merge_ocds_by_year.py dedupes by ocid per calendar year" },
  { n: 9, label: "Aggregate report", desc: "aggregate_dataset_report.py → combined.report.json" },
];

export const ETL_DOC_LINKS = [
  { label: "ETL pipeline", path: "docs/ETL_PIPELINE.md", desc: "End-to-end operator reference" },
  { label: "OCDS id generation", path: "docs/OCDS_ID_GENERATION.md", desc: "ocid / release.id policy and collision handling" },
  { label: "Transform rules", path: "docs/TRANSFORM.md", desc: "Per-row mapping and DQ rules" },
  { label: "Architectural decisions", path: "docs/ARCHITECTURAL_DECISIONS.md", desc: "ADR log — grouping, ocid, reports" },
  { label: "Process identity", path: "docs/PROCESS_IDENTITY_ANALYSIS.md", desc: "Bid vs solicitation analysis" },
  { label: "Validation", path: "docs/VALIDATION.md", desc: "OCDS validation layers" },
] as const;

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function severityBadge(sev: string): { variant: string; label: string } {
  if (sev === "error") return { variant: "red", label: "error" };
  if (sev === "warning") return { variant: "amber", label: "warning" };
  return { variant: "blue", label: "info" };
}

const ROW_INDEX_PREVIEW = 4;

function formatRowIndexPreview(
  indices: number[] | undefined,
  omitted = 0,
  max = ROW_INDEX_PREVIEW,
): string | null {
  if (!indices?.length && !omitted) return null;
  const total = (indices?.length ?? 0) + omitted;
  if (!indices?.length) return `${total.toLocaleString()} rows`;
  if (indices.length <= max && !omitted) return indices.join(", ");
  const head = indices.slice(0, max).join(", ");
  const tailOmitted = indices.length > max ? indices.length - max : 0;
  const extra = tailOmitted + omitted;
  if (extra <= 0) return head;
  return `${head} (+${extra.toLocaleString()} more)`;
}

function sampleKey(s: TransformQuarantinedSample): string {
  if (s.row_index != null) return `row:${s.row_index}`;
  return `award:${s.award_reference_no ?? "?"}:${s.row_indices?.join(",") ?? ""}`;
}

function messagePattern(message: string): string {
  return message
    .replace(/^(row \d+|award [^:]+):\s*/i, "")
    .replace(/\[[\d,\s]+\]/g, "[rows]")
    .trim();
}

function issueGroupLabel(issue: TransformQuarantinedIssue): string {
  const pattern = messagePattern(issue.message);
  if (pattern.startsWith("`")) return pattern;
  if (issue.field) return `\`${issue.field}\` — ${pattern}`;
  return pattern;
}

interface DqIssueGroup {
  key: string;
  label: string;
  samples: TransformQuarantinedSample[];
  totalCount?: number;
}

interface DqRuleGroup {
  rule: string;
  totalCount: number | undefined;
  sampleCount: number;
  issueGroups: DqIssueGroup[];
}

function buildSampleTree(
  samples: TransformQuarantinedSample[],
  ruleCounts: TransformRuleCount[],
  severity: TransformQuarantinedIssue["severity"],
  issueGroupCounts: TransformIssueGroupCount[] = [],
): DqRuleGroup[] {
  const countByRule = Object.fromEntries(
    ruleCounts.filter((r) => r.severity === severity).map((r) => [r.rule, r.count]),
  );
  const countByIssueGroup = Object.fromEntries(
    issueGroupCounts
      .filter((e) => e.severity === severity)
      .map((e) => [`${e.rule}|${e.field}|${e.pattern}`, e.count]),
  );

  const byRule = new Map<
    string,
    Map<string, { label: string; samples: TransformQuarantinedSample[]; seen: Set<string> }>
  >();

  for (const sample of samples) {
    for (const issue of sample.issues) {
      if (issue.severity !== severity) continue;
      const pattern = messagePattern(issue.message);
      const issueKey = `${issue.field}|${pattern}`;

      let issueMap = byRule.get(issue.rule);
      if (!issueMap) {
        issueMap = new Map();
        byRule.set(issue.rule, issueMap);
      }

      let group = issueMap.get(issueKey);
      if (!group) {
        group = { label: issueGroupLabel(issue), samples: [], seen: new Set() };
        issueMap.set(issueKey, group);
      }

      const key = sampleKey(sample);
      if (!group.seen.has(key)) {
        group.seen.add(key);
        group.samples.push(sample);
      }
    }
  }

  return [...byRule.entries()]
    .map(([rule, issueMap]) => {
      const allSamples = issueMap.values();
      const uniqueKeys = new Set<string>();
      for (const g of allSamples) {
        for (const s of g.samples) uniqueKeys.add(sampleKey(s));
      }
      return {
        rule,
        totalCount: countByRule[rule],
        sampleCount: uniqueKeys.size,
        issueGroups: [...issueMap.entries()].map(([key, g]) => {
          let totalCount = countByIssueGroup[`${rule}|${key}`];
          if (totalCount == null && issueMap.size === 1 && countByRule[rule] != null) {
            totalCount = countByRule[rule];
          }
          return {
            key,
            label: g.label,
            samples: g.samples,
            totalCount,
          };
        }),
      };
    })
    .sort((a, b) => (b.totalCount ?? 0) - (a.totalCount ?? 0));
}

function TreeChevron() {
  return <span className="dq-tree-chevron" aria-hidden />;
}

function sampleTitle(s: TransformQuarantinedSample): string {
  if (s.row_index != null) return `Row ${s.row_index}`;
  const ref = s.award_reference_no ?? "?";
  const count = (s.row_indices?.length ?? 0) + (s.row_indices_omitted ?? 0);
  if (count === 0) return `Award ${ref}`;
  if (count === 1) return `Award ${ref} · row ${s.row_indices![0]}`;
  return `Award ${ref} · ${count.toLocaleString()} rows`;
}

function DqIssuesTable({ issues }: { issues: TransformQuarantinedIssue[] }) {
  if (issues.length === 0) return null;
  return (
    <div className="dq-sample-issues">
      <div className="muted dq-sample-context-label">Issues</div>
      <div className="table-wrap">
        <table className="data-table dq-sample-issues-table">
          <thead>
            <tr>
              <th>Rule</th>
              <th>Field</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            {issues.map((issue, idx) => (
              <tr key={`${issue.rule}-${issue.field}-${idx}`}>
                <td className="mono">{issue.rule}</td>
                <td className="mono">{issue.field}</td>
                <td className="mono">{String(issue.value ?? "—")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DqRowContext({ sample }: { sample: TransformQuarantinedSample }) {
  const entry = sample.row_entry;
  const raw = sample.raw_row;
  const hasRowData = Boolean(entry || raw);

  const entryRows = entry ? Object.entries(entry) : [];
  const rawRows = raw ? Object.entries(raw) : [];

  if (!hasRowData) {
    return (
      <div className="dq-sample-context">
        <p className="muted dq-sample-missing-context">
          Row context not embedded for this sample. Re-run the transform to capture canonical
          and source fields.
        </p>
        <DqIssuesTable issues={sample.issues} />
      </div>
    );
  }

  return (
    <div className="dq-sample-context">
      <DqIssuesTable issues={sample.issues} />
      {entryRows.length > 0 && (
        <>
          <div className="muted dq-sample-context-label">Canonical fields</div>
          <dl className="kv-list release-kv dq-sample-kv">
            {entryRows.map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd className="mono">{String(value)}</dd>
              </div>
            ))}
          </dl>
        </>
      )}
      {rawRows.length > 0 && (
        <>
          <div className="muted dq-sample-context-label">Source row</div>
          <dl className="kv-list release-kv dq-sample-kv">
            {rawRows.slice(0, 30).map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd className="mono">{value}</dd>
              </div>
            ))}
          </dl>
        </>
      )}
    </div>
  );
}

function DqSampleLeaf({
  sample,
  index,
  badgeVariant,
  badgeLabel,
}: {
  sample: TransformQuarantinedSample;
  index: number;
  badgeVariant: "red" | "amber" | "outline" | "blue";
  badgeLabel: string;
}) {
  const rowPreview = formatRowIndexPreview(sample.row_indices, sample.row_indices_omitted ?? 0);

  return (
    <details className="dq-tree-node dq-tree-sample">
      <summary className="dq-tree-summary dq-tree-summary-leaf">
        <TreeChevron />
        <div className="dq-sample-summary-text">
          <span className="mono dq-sample-title">{sampleTitle(sample)}</span>
          {rowPreview && (
            <span className="muted dq-sample-rows-preview">Rows {rowPreview}</span>
          )}
        </div>
        <Badge variant={badgeVariant}>{badgeLabel}</Badge>
      </summary>
      <div className="dq-tree-body">
        <DqRowContext sample={sample} />
        <details className="dq-sample-json">
          <summary className="muted dq-sample-json-toggle">Full sample JSON</summary>
          <LazyJsonView value={sample} maxHeight="16rem" filename={`dq-sample-${index}.json`} />
        </details>
      </div>
    </details>
  );
}

function DqSampleTree({
  samples,
  ruleCounts,
  issueGroupCounts = [],
  severity,
  badgeVariant,
  badgeLabel,
  keyPrefix,
  samplesOmitted = 0,
}: {
  samples: TransformQuarantinedSample[];
  ruleCounts: TransformRuleCount[];
  issueGroupCounts?: TransformIssueGroupCount[];
  severity: TransformQuarantinedIssue["severity"];
  badgeVariant: "red" | "amber" | "outline" | "blue";
  badgeLabel: string | ((sample: TransformQuarantinedSample) => string);
  keyPrefix: string;
  samplesOmitted?: number;
}) {
  const tree = useMemo(
    () => buildSampleTree(samples, ruleCounts, severity, issueGroupCounts),
    [samples, ruleCounts, severity, issueGroupCounts],
  );

  if (tree.length === 0) return null;

  return (
    <Card className="dq-tree-root">
      <div className="dq-tree">
        {tree.map((ruleGroup) => (
          <details key={`${keyPrefix}-${ruleGroup.rule}`} className="dq-tree-node dq-tree-rule">
            <summary className="dq-tree-summary">
              <TreeChevron />
              <span className="mono dq-tree-rule-name">{ruleGroup.rule}</span>
              {ruleGroup.totalCount != null && (
                <span className="muted dq-tree-meta">
                  {ruleGroup.totalCount.toLocaleString()} in run
                </span>
              )}
              <Badge variant={badgeVariant === "outline" ? "outline" : badgeVariant}>
                {ruleGroup.sampleCount} sample{ruleGroup.sampleCount === 1 ? "" : "s"}
              </Badge>
            </summary>
            <div className="dq-tree-children">
              {ruleGroup.issueGroups.map((issueGroup) => (
                <details
                  key={`${keyPrefix}-${ruleGroup.rule}-${issueGroup.key}`}
                  className="dq-tree-node dq-tree-issue"
                >
                  <summary className="dq-tree-summary">
                    <TreeChevron />
                    <span className="dq-tree-issue-label">{issueGroup.label}</span>
                    {issueGroup.totalCount != null && (
                      <span className="muted dq-tree-meta">
                        {issueGroup.totalCount.toLocaleString()} in run
                      </span>
                    )}
                    <Badge variant="outline">
                      {issueGroup.samples.length} sample
                      {issueGroup.samples.length === 1 ? "" : "s"}
                    </Badge>
                  </summary>
                  <div className="dq-tree-children">
                    {issueGroup.samples.map((s, i) => (
                      <DqSampleLeaf
                        key={`${keyPrefix}-${sampleKey(s)}`}
                        sample={s}
                        index={i}
                        badgeVariant={badgeVariant}
                        badgeLabel={
                          typeof badgeLabel === "function" ? badgeLabel(s) : badgeLabel
                        }
                      />
                    ))}
                  </div>
                </details>
              ))}
            </div>
          </details>
        ))}
      </div>
      {samplesOmitted > 0 && (
        <p className="muted dq-tree-omitted">
          Showing {samples.length} sample{samples.length === 1 ? "" : "s"}. +
          {samplesOmitted.toLocaleString()} more not loaded — see{" "}
          <code className="mono">.dq.json</code> for the full report.
        </p>
      )}
    </Card>
  );
}

export function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <Card>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {hint && <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{hint}</div>}
    </Card>
  );
}

export function PipelineDiagram() {
  return (
    <div className="pipeline">
      {PIPELINE_STAGES.map((stage, i) => (
        <div key={stage.n} className="pipeline-stage">
          <div className="pipeline-node">
            <span className="pipeline-num">{stage.n}</span>
            <div className="pipeline-text">
              <div className="pipeline-label">{stage.label}</div>
              <div className="pipeline-desc">{stage.desc}</div>
            </div>
          </div>
          {i < PIPELINE_STAGES.length - 1 && <div className="pipeline-arrow" aria-hidden>↓</div>}
        </div>
      ))}
    </div>
  );
}

export function RunSummaryStats({ t }: { t: TransformBundle }) {
  const isFullDataset = t.scope === "full_dataset";
  const committedPct = useMemo(() => {
    if (!t.rows_seen) return 0;
    return Math.round((t.rows_committed / t.rows_seen) * 100);
  }, [t.rows_seen, t.rows_committed]);

  if (isFullDataset) {
    return (
      <div className="card-grid cols-4">
        <StatCard
          label="Source files"
          value={String(t.source_file_count ?? 0)}
          hint={`${(t.calendar_year_count ?? 0).toLocaleString()} calendar years`}
        />
        <StatCard label="Raw input" value={formatBytes(t.input_bytes)} hint="All PhilGEPS exports" />
        <StatCard
          label="Rows seen"
          value={t.rows_seen.toLocaleString()}
          hint={`${t.rows_committed.toLocaleString()} committed (${committedPct}%)`}
        />
        <StatCard
          label="Releases compiled"
          value={t.compiled_release_count.toLocaleString()}
          hint={`${(t.package_mb_total ?? 0).toLocaleString()} MB in by_year/`}
        />
      </div>
    );
  }

  return (
    <div className="card-grid cols-4">
      <StatCard
        label="Input file"
        value={t.input_file.split(/[\\/]/).pop() ?? t.input_file}
        hint={formatBytes(t.input_bytes)}
      />
      <StatCard
        label="Schema detected"
        value={t.schema_detected}
        hint={`${t.mapped_column_count} columns mapped`}
      />
      <StatCard label="Rows seen" value={t.rows_seen.toLocaleString()} />
      <StatCard
        label="Releases compiled"
        value={t.compiled_release_count.toLocaleString()}
        hint={`${t.rows_committed.toLocaleString()} rows committed (${committedPct}%)`}
      />
    </div>
  );
}

export function YearsTable({ years }: { years: TransformYearSummary[] }) {
  return (
    <Card>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Year</th>
              <th>Releases</th>
              <th>Sources</th>
              <th>Package</th>
              <th>Warnings</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {years.map((y) => (
              <tr key={y.year}>
                <td className="mono">{y.year}</td>
                <td>{y.compiled_release_count.toLocaleString()}</td>
                <td>{y.source_file_count}</td>
                <td>{y.package_mb.toLocaleString()} MB</td>
                <td>{(y.severity_counts.warning ?? 0).toLocaleString()}</td>
                <td>
                  <Badge variant={y.all_passed ? "green" : "amber"}>
                    {y.all_passed ? "pass" : "review"}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export function RowAccountingPanel({ accounting }: { accounting: RowAccounting | undefined }) {
  if (!accounting?.breakdown?.length) return null;

  const rowsSeen = accounting.rows_seen;
  const finalStep = accounting.breakdown[accounting.breakdown.length - 1];

  return (
    <>
      <SectionHeader
        title="Row → release accounting"
        subtitle="How raw PhilGEPS rows become OCDS releases for this scope."
      />
      {accounting.estimated && (
        <Card>
          <p className="muted" style={{ fontSize: 13, margin: 0 }}>
            Compile-stage counters are <strong>estimated</strong> from{" "}
            <code className="mono">unawarded_tender</code> rule counts until sources are
            re-transformed with explicit <code className="mono">compile_accounting</code>.
          </p>
        </Card>
      )}
      <Card>
        <div className="row-accounting-summary">
          <span>
            <strong>{rowsSeen.toLocaleString()}</strong> raw rows
          </span>
          <span className="row-accounting-arrow" aria-hidden>→</span>
          <span>
            <strong>{finalStep.count.toLocaleString()}</strong> {finalStep.label.toLowerCase()}
          </span>
        </div>
        <div className="table-wrap" style={{ marginTop: 12 }}>
          <table className="data-table row-accounting-table">
            <thead>
              <tr>
                <th>Stage</th>
                <th style={{ textAlign: "right" }}>Count</th>
                <th>% of rows seen</th>
              </tr>
            </thead>
            <tbody>
              {accounting.breakdown.map((step) => {
                const pct = rowsSeen ? Math.round((step.count / rowsSeen) * 1000) / 10 : 0;
                const showPct = step.id === "rows_seen" || step.id.startsWith("rows_") || step.id === "quarantined" || step.id.startsWith("excluded");
                return (
                  <tr key={step.id} className={`row-accounting-${step.id}`}>
                    <td>
                      <div>{step.label}</div>
                      <div className="muted" style={{ fontSize: 12 }}>{step.detail}</div>
                    </td>
                    <td className="mono" style={{ textAlign: "right" }}>
                      {step.count.toLocaleString()}
                    </td>
                    <td className="muted" style={{ fontSize: 12 }}>
                      {showPct && rowsSeen ? `${pct}%` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}

export function DataQualityPanel({ t }: { t: TransformBundle }) {
  const sc = t.severity_counts;
  const topRules: TransformRuleCount[] = t.rule_counts.slice(0, 8);
  const samples: TransformQuarantinedSample[] = t.quarantined_samples;
  const warningSamples: TransformQuarantinedSample[] = t.warning_samples ?? [];
  const infoSamples: TransformQuarantinedSample[] = t.info_samples ?? [];

  return (
    <>
      <div className="card-grid cols-3">
        <StatCard label="Errors" value={sc.error} hint="Rows blocked from OCDS compilation" />
        <StatCard label="Warnings" value={sc.warning} hint="Suspicious but compilable" />
        <StatCard label="Info" value={sc.info} hint="Noteworthy but benign" />
      </div>

      {topRules.length > 0 && (
        <>
          <SectionHeader
            title="Top rules triggered"
            subtitle="Stable rule identifiers in scripts/_data_quality.py."
          />
          <Card>
            <table className="table">
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Rule</th>
                  <th style={{ textAlign: "right" }}>Count</th>
                </tr>
              </thead>
              <tbody>
                {topRules.map((r) => {
                  const badge = severityBadge(r.severity);
                  return (
                    <tr key={r.rule}>
                      <td>
                        <Badge variant={badge.variant as never}>{badge.label}</Badge>
                      </td>
                      <td className="mono">{r.rule}</td>
                      <td style={{ textAlign: "right" }}>{r.count.toLocaleString()}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        </>
      )}

      {samples.length > 0 && (
        <>
          <SectionHeader
            title="Quarantined row samples"
            subtitle="Grouped by rule and issue pattern."
          />
          <DqSampleTree
            samples={samples}
            ruleCounts={t.rule_counts}
            issueGroupCounts={t.issue_group_counts}
            severity="error"
            badgeVariant="red"
            badgeLabel={(s) => `${s.issues.length} issue(s)`}
            keyPrefix="quarantine"
            samplesOmitted={t.quarantined_samples_omitted ?? 0}
          />
        </>
      )}

      {infoSamples.length > 0 && (
        <>
          <SectionHeader title="Info samples" />
          <DqSampleTree
            samples={infoSamples}
            ruleCounts={t.rule_counts}
            issueGroupCounts={t.issue_group_counts}
            severity="info"
            badgeVariant="outline"
            badgeLabel={(s) => `${s.issues.length} info`}
            keyPrefix="info"
            samplesOmitted={t.info_samples_omitted ?? 0}
          />
        </>
      )}

      {warningSamples.length > 0 && (
        <>
          <SectionHeader title="Warning samples" />
          <DqSampleTree
            samples={warningSamples}
            ruleCounts={t.rule_counts}
            issueGroupCounts={t.issue_group_counts}
            severity="warning"
            badgeVariant="amber"
            badgeLabel={(s) => `${s.issues.length} warning(s)`}
            keyPrefix="warning"
            samplesOmitted={t.warning_samples_omitted ?? 0}
          />
        </>
      )}

      {(t.display_id_collisions?.length ?? 0) > 0 && (
        <>
          <SectionHeader
            title="Display id collisions"
            subtitle="Releases rewritten to composite ocid/id after compile (display_id_collision)."
          />
          <Card>
            <LazyJsonView
              value={t.display_id_collisions}
              maxHeight="16rem"
              filename="display-id-collisions.json"
            />
          </Card>
        </>
      )}

      {t.unmapped_columns.length > 0 && (
        <>
          <SectionHeader title="Unmapped columns" />
          <Card>
            <div className="pill-row">
              {t.unmapped_columns.map((c) => (
                <span key={c} className="pill">{c}</span>
              ))}
            </div>
          </Card>
        </>
      )}
    </>
  );
}

export function BeforeAfterPanel({ t }: { t: TransformBundle }) {
  const pairs = t.input_samples;
  const [idx, setIdx] = useState(0);

  if (pairs.length === 0) {
    return (
      <Card>
        <span className="muted">No before/after pairs available for this run.</span>
      </Card>
    );
  }

  const pair = pairs[idx];
  const rawEntries = Object.entries(pair.raw_row).filter(
    ([, v]) => v && String(v).trim().toUpperCase() !== "NULL",
  );

  return (
    <Card>
      <div className="browser-list-head" style={{ marginBottom: 8 }}>
        {pairs.length} paired samples ·{" "}
        <select value={idx} onChange={(e) => setIdx(Number(e.target.value))}>
          {pairs.map((p, i) => (
            <option key={i} value={i}>
              {p.award_reference_no} ({p.row_count} row{p.row_count === 1 ? "" : "s"})
            </option>
          ))}
        </select>
      </div>
      <div className="before-after">
        <div className="before-after-col">
          <h4 className="before-after-title">Raw CSV row</h4>
          <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
            Source values from <code className="mono">{t.input_file}</code>.
          </div>
          <Card>
            <dl className="kv-list">
              {rawEntries.map(([k, v]) => (
                <div key={k}>
                  <dt>{k}</dt>
                  <dd className="mono">{String(v)}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </div>
        <div className="before-after-arrow" aria-hidden>→</div>
        <div className="before-after-col">
          <h4 className="before-after-title">Compiled OCDS release</h4>
          <JsonView value={pair.release} filename={`${pair.award_reference_no}.json`} />
        </div>
      </div>
    </Card>
  );
}

export function OcidIdentityPanel() {
  return (
    <Card>
      <div className="release-section-title">OCID / release.id policy</div>
      <p className="muted" style={{ fontSize: 13, marginBottom: 12 }}>
        One OCDS release per contracting process. libcoveocds requires unique{" "}
        <code className="mono">(ocid, id)</code> pairs within each package.
      </p>
      <dl className="kv-list release-kv">
        <dt>Group rows by</dt>
        <dd>
          <code className="mono">bid_reference_no</code> →{" "}
          <code className="mono">solicitation_no</code> →{" "}
          <code className="mono">award_reference_no</code>
        </dd>
        <dt>release.id / ocid slug</dt>
        <dd>Same priority: bid first; solicitation when bid is missing or <code className="mono">0</code></dd>
        <dt>Human solicitation</dt>
        <dd>
          <code className="mono">philgeps.solicitationNo</code> — not the release <code className="mono">id</code>
        </dd>
        <dt>On collision</dt>
        <dd>Composite id (e.g. <code className="mono">bid-solicitation</code>) + DQ rule{" "}
          <code className="mono">display_id_collision</code>
        </dd>
        <dt>Reference</dt>
        <dd className="mono">docs/OCDS_ID_GENERATION.md</dd>
      </dl>
    </Card>
  );
}

export function EtlDocLinks() {
  return (
    <Card>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>Document</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {ETL_DOC_LINKS.map((doc) => (
              <tr key={doc.path}>
                <td className="mono">{doc.path}</td>
                <td>{doc.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export function EtlCommandsCard() {
  return (
    <Card>
      <pre className="mono etl-commands">
{`# Full dataset (54 files) — clean run after compiler policy changes
python scripts/run_full_dataset.py --no-quiet

# Post-ETL webapp bundle
python scripts/build_schema_field_map.py

# Single export
python scripts/transform_to_ocds.py raw/<export>.csv --out references/transformed/full/<name>

# Re-merge / refresh caches only
python scripts/merge_ocds_by_year.py
python scripts/build_year_dq_cache.py`}
      </pre>
    </Card>
  );
}

export function TransformMissingState({ title }: { title?: string }) {
  return (
    <Card>
      <div className="muted">
        {title ? <strong>{title}</strong> : null}
        {title ? " — " : ""}
        No transform output embedded. Run a transform, then refresh the bundle:
        <pre className="mono" style={{ marginTop: 8 }}>
          python scripts/run_full_dataset.py{"\n"}
          python scripts/build_schema_field_map.py
        </pre>
      </div>
    </Card>
  );
}

export function useTransformBundle() {
  return bundle.transform;
}

export function TransformPageShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <>
      <PageHeader title={title} subtitle={subtitle} />
      {children}
    </>
  );
}
