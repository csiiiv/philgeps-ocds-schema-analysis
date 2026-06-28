import { Card } from "../components/ui";
import { SectionHeader } from "../components/Layout";
import {
  BeforeAfterPanel,
  TransformMissingState,
  TransformPageShell,
  useTransformBundle,
} from "../components/etl/shared";

export function EtlSamplesPage() {
  const t = useTransformBundle();

  if (!t) {
    return (
      <TransformPageShell
        title="Transform samples"
        subtitle="Raw source rows alongside compiled OCDS releases."
      >
        <TransformMissingState />
      </TransformPageShell>
    );
  }

  if (t.scope === "full_dataset") {
    return (
      <TransformPageShell
        title="Transform samples"
        subtitle="Before/after pairs are embedded for single-file transform runs only."
      >
        <Card>
          <p className="muted">
            The full-dataset run does not embed per-row before/after pairs in{" "}
            <code className="mono">schema_bundle.json</code> (too large). Use the{" "}
            <strong>Release browser</strong> to inspect compiled releases, or run a single-file
            transform and rebuild the bundle:
          </p>
          <pre className="mono" style={{ marginTop: 12 }}>
            python scripts/transform_to_ocds.py raw/&lt;export&gt;.csv{"\n"}
            python scripts/build_schema_field_map.py
          </pre>
        </Card>
      </TransformPageShell>
    );
  }

  return (
    <TransformPageShell
      title="Transform samples"
      subtitle="For each sample release, the raw CSV row alongside the compiled OCDS JSON."
    >
      <SectionHeader title="Before / after" />
      <BeforeAfterPanel t={t} />
    </TransformPageShell>
  );
}
