import { SectionHeader } from "../components/Layout";
import { Card } from "../components/ui";
import {
  EtlCommandsCard,
  EtlDocLinks,
  OcidIdentityPanel,
  PipelineDiagram,
  RunSummaryStats,
  TransformMissingState,
  TransformPageShell,
  useTransformBundle,
  YearsTable,
} from "../components/etl/shared";

export function EtlOverviewPage() {
  const t = useTransformBundle();

  if (!t) {
    return (
      <TransformPageShell
        title="Pipeline overview"
        subtitle="How PhilGEPS exports become OCDS release packages."
      >
        <TransformMissingState />
        <SectionHeader title="Documentation" subtitle="Repo docs under philgeps_schema_analysis/docs/." />
        <EtlDocLinks />
        <SectionHeader title="Commands" />
        <EtlCommandsCard />
      </TransformPageShell>
    );
  }

  const isFullDataset = t.scope === "full_dataset";

  return (
    <TransformPageShell
      title="Pipeline overview"
      subtitle={
        isFullDataset
          ? "Full PhilGEPS dataset (2000–2025): detect schema → canonical → DQ → process-level OCDS → merge by year."
          : "End-to-end path from one PhilGEPS export to validated OCDS releases."
      }
    >
      <SectionHeader
        title="Stages"
        subtitle="Each stage maps to scripts in philgeps_schema_analysis/scripts/."
      />
      <PipelineDiagram />

      <SectionHeader title="Run summary" />
      <RunSummaryStats t={t} />

      <SectionHeader
        title="OCID / release.id"
        subtitle="How process identity becomes ocid and release.id (ADR-011)."
      />
      <OcidIdentityPanel />

      {(isFullDataset || (t.years && t.years.length > 0)) && t.years && t.years.length > 0 && (
        <>
          <SectionHeader
            title="By calendar year"
            subtitle="Merged packages under references/transformed/by_year/."
          />
          <YearsTable years={t.years} />
        </>
      )}

      <SectionHeader
        title="Webapp pages"
        subtitle="ETL Pipeline section after a full transform + build_schema_field_map.py."
      />
      <Card>
        <ul className="muted" style={{ margin: 0, paddingLeft: 20, fontSize: 13, lineHeight: 1.7 }}>
          <li>
            <strong>Year data quality</strong> — <code>by_year/dq/&#123;year&#125;.json</code>
          </li>
          <li>
            <strong>Overall data quality</strong> — roll-up from embedded <code>combined.report.json</code>
          </li>
          <li>
            <strong>Release browser</strong> — <code>#/etl-releases/&#123;year&#125;</code> optional{" "}
            <code>/&#123;ocid&#125;</code>
          </li>
        </ul>
      </Card>

      <SectionHeader
        title="Documentation"
        subtitle="Design intent, operator guides, and validation references."
      />
      <EtlDocLinks />

      <SectionHeader title="Commands" subtitle="Typical operator workflow after mapping changes." />
      <EtlCommandsCard />

      {isFullDataset && (
        <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>
          Combined report:{" "}
          <code className="mono">{t.combined_report_path ?? "references/transformed/combined.report.json"}</code>
        </p>
      )}
    </TransformPageShell>
  );
}
