import { SectionHeader } from "../components/Layout";
import { Card } from "../components/ui";
import {
  DataQualityPanel,
  RowAccountingPanel,
  TransformPageShell,
  useTransformBundle,
} from "../components/etl/shared";

export function EtlOverallQualityPage() {
  const t = useTransformBundle();

  if (!t || t.scope !== "full_dataset") {
    return (
      <TransformPageShell
        title="Overall data quality"
        subtitle="Dataset-wide DQ roll-up after a full ETL re-run."
      >
        <Card>
          <p className="muted">
            Overall data quality requires{" "}
            <code className="mono">references/transformed/combined.report.json</code> from a full
            transform of all source exports. For quick iteration on one year, use{" "}
            <strong>Year data quality</strong> instead.
          </p>
          <pre className="mono etl-commands" style={{ marginTop: 8 }}>
{`python scripts/run_full_dataset.py --no-quiet
python scripts/merge_ocds_by_year.py
python scripts/aggregate_dataset_report.py
python scripts/build_schema_field_map.py`}
          </pre>
        </Card>
      </TransformPageShell>
    );
  }

  return (
    <TransformPageShell
      title="Overall data quality"
      subtitle="Merged severity counts and diverse samples across all source exports. Meaningful only after a full ETL re-run — stale years pollute merged samples."
    >
      <Card>
        <p className="muted" style={{ fontSize: 13 }}>
          Aggregated from{" "}
          <code className="mono">{t.combined_report_path ?? "combined.report.json"}</code>. Per-year
          samples with full row context live under Year data quality.
        </p>
      </Card>

      <RowAccountingPanel accounting={t.row_accounting} />

      <SectionHeader
        title="Findings"
        subtitle="Overall roll-up across all sources. Warning samples prefer rule diversity; re-transform all files for consistent row context."
      />
      <DataQualityPanel t={t} />
    </TransformPageShell>
  );
}
