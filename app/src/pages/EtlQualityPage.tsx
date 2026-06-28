import { useEffect, useState } from "react";
import { SectionHeader } from "../components/Layout";
import { Card } from "../components/ui";
import {
  DataQualityPanel,
  RowAccountingPanel,
  RunSummaryStats,
  TransformPageShell,
  useTransformBundle,
} from "../components/etl/shared";
import { pickDefaultYear } from "../lib/yearBrowserCache";
import { DEFAULT_YEAR_DQ_BASE, fetchYearDqBundle } from "../lib/yearDqCache";
import type { TransformBundle } from "../data/types";

export function EtlQualityPage() {
  const overview = useTransformBundle();
  const years = overview?.years ?? [];
  const [year, setYear] = useState(() => pickDefaultYear(years));
  const [bundle, setBundle] = useState<TransformBundle | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (years.length && !years.some((y) => y.year === year)) {
      setYear(pickDefaultYear(years));
    }
  }, [years, year]);

  useEffect(() => {
    if (!year) {
      setBundle(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchYearDqBundle(DEFAULT_YEAR_DQ_BASE, year)
      .then((payload) => {
        if (!cancelled) setBundle(payload);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setBundle(null);
          setError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [year]);

  if (!overview && years.length === 0) {
    return (
      <TransformPageShell
        title="Year data quality"
        subtitle="Per-calendar-year DQ from source transform runs."
      >
        <Card>
          <p className="muted">
            No year index in the bundle. Transform a year, merge, then build caches:
          </p>
          <pre className="mono etl-commands">
{`python scripts/run_full_dataset.py --only "2004"
python scripts/merge_ocds_by_year.py --years 2004
python scripts/build_year_dq_cache.py --years 2004`}
          </pre>
        </Card>
      </TransformPageShell>
    );
  }

  return (
    <TransformPageShell
      title="Year data quality"
      subtitle="Inspect DQ for one calendar year from its source export(s). Samples include canonical fields and source row data for verification."
    >
      <Card>
        <div className="browser-list-head">
          <label>
            Calendar year{" "}
            <select value={year} onChange={(e) => setYear(e.target.value)}>
              {years.map((y) => (
                <option key={y.year} value={y.year}>
                  {y.year} ({y.compiled_release_count.toLocaleString()} releases)
                </option>
              ))}
            </select>
          </label>
          <span className="muted" style={{ fontSize: 12 }}>
            Loaded from{" "}
            <code className="mono">{DEFAULT_YEAR_DQ_BASE}/{year}.json</code>
          </span>
        </div>
      </Card>

      {loading && (
        <Card>
          <span className="muted">Loading year DQ cache…</span>
        </Card>
      )}

      {error && (
        <Card>
          <p className="release-browser-error">{error}</p>
          <pre className="mono etl-commands" style={{ marginTop: 8 }}>
{`python scripts/build_year_dq_cache.py --years ${year}`}
          </pre>
        </Card>
      )}

      {bundle && !loading && (
        <>
          <SectionHeader title="Run summary" subtitle={`Source file(s) for ${year}.`} />
          <RunSummaryStats t={bundle} />
          <RowAccountingPanel accounting={bundle.row_accounting} />
          <SectionHeader
            title="Findings"
            subtitle="Counts and samples from this year's transform sidecar(s), not the overall merge."
          />
          <DataQualityPanel t={bundle} />
        </>
      )}
    </TransformPageShell>
  );
}
