import { useEffect } from "react";
import { ReleaseBrowser } from "../components/ReleaseBrowser";
import {
  TransformMissingState,
  TransformPageShell,
  useTransformBundle,
} from "../components/etl/shared";
import { navigate, parseRoute, useRoute } from "../components/Layout";
import { pickDefaultYear } from "../lib/yearBrowserCache";

export function EtlReleasesPage() {
  const route = useRoute();
  const { segments } = parseRoute(route);
  const routeYear = segments[0];
  const routeOcid = segments[1] ? decodeURIComponent(segments[1]) : undefined;
  const t = useTransformBundle();
  const years = t?.years ?? [];

  useEffect(() => {
    if (!years.length) return;
    if (!routeYear || !years.some((y) => y.year === routeYear)) {
      navigate(`etl-releases/${pickDefaultYear(years)}`);
    }
  }, [routeYear, years]);

  if (!t) {
    return (
      <TransformPageShell
        title="Release browser"
        subtitle="Browse merged OCDS releases by calendar year."
      >
        <TransformMissingState />
      </TransformPageShell>
    );
  }

  const isFullDataset = t.scope === "full_dataset";

  return (
    <TransformPageShell
      title="Release browser"
      subtitle="Pick a calendar year to browse merged releases. Summaries load from references/transformed/by_year/browser/; Raw JSON loads on demand."
    >
      <ReleaseBrowser
        years={years}
        totalCount={t.compiled_release_count}
        baseUrl={t.release_browser_base_url}
        routeYear={routeYear}
        routeOcid={routeOcid}
        onNavigate={(year, ocid) => {
          const path = ocid
            ? `etl-releases/${year}/${encodeURIComponent(ocid)}`
            : `etl-releases/${year}`;
          navigate(path);
        }}
      />
      <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>
        {isFullDataset ? (
          <>
            Per-year caches:{" "}
            <code className="mono">{t.release_browser_base_url ?? "/data/releases"}/&#123;year&#125;.json</code>
            {" · "}
            On-demand release: <code className="mono">/data/release/&#123;year&#125;/&#123;ocid&#125;.json</code>
            {" · "}
            Deep link: <code className="mono">#/etl-releases/2004/ocds-philgeps-39785</code>
          </>
        ) : (
          <>Full package: <code className="mono">{t.package_path}</code></>
        )}
      </p>
    </TransformPageShell>
  );
}
