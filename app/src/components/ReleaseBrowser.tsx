import { useEffect, useMemo, useRef, useState } from "react";
import { Card, Badge } from "./ui";
import { LazyJsonView } from "./JsonView";
import {
  collectAwards,
  collectContracts,
  formatMoney,
  type ReleaseSummary,
} from "../lib/releaseSummary";
import {
  buildReleaseFilterFacets,
  DEFAULT_RELEASE_FILTERS,
  hasActiveReleaseFilters,
  releaseMatchesFilters,
  type ReleaseFilterState,
  type ReleaseSearchField,
} from "../lib/releaseFilters";
import type { TransformYearSummary } from "../data/types";
import {
  DEFAULT_RELEASE_BROWSER_BASE,
  fetchReleaseDetail,
  fetchYearBrowserCache,
  pickDefaultYear,
  type YearBrowserCache,
} from "../lib/yearBrowserCache";

const OCDS_BLOCKS: { key: string; label: string }[] = [
  { key: "buyer", label: "Buyer" },
  { key: "tender", label: "Tender" },
  { key: "awards", label: "Awards" },
  { key: "contracts", label: "Contracts" },
  { key: "parties", label: "Parties" },
  { key: "bids", label: "Bids" },
  { key: "philgeps", label: "PhilGEPS" },
];

type DetailTab = "summary" | "json";

const SEARCH_DEBOUNCE_MS = 300;

function resolveYear(years: TransformYearSummary[], preferred?: string): string {
  if (preferred && years.some((y) => y.year === preferred)) return preferred;
  return pickDefaultYear(years);
}

export function ReleaseBrowser({
  years,
  totalCount,
  baseUrl = DEFAULT_RELEASE_BROWSER_BASE,
  routeYear,
  routeOcid,
  onNavigate,
}: {
  years: TransformYearSummary[];
  totalCount: number;
  baseUrl?: string;
  routeYear?: string;
  routeOcid?: string;
  onNavigate?: (year: string, ocid?: string | null) => void;
}) {
  const [year, setYear] = useState(() => resolveYear(years, routeYear));
  const [cache, setCache] = useState<YearBrowserCache | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedOcid, setSelectedOcid] = useState<string | null>(null);
  const [queryInput, setQueryInput] = useState("");
  const [filters, setFilters] = useState<ReleaseFilterState>(DEFAULT_RELEASE_FILTERS);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [tab, setTab] = useState<DetailTab>("summary");
  const activeItemRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(
      () => setFilters((prev) => ({ ...prev, query: queryInput })),
      SEARCH_DEBOUNCE_MS,
    );
    return () => window.clearTimeout(timer);
  }, [queryInput]);

  const applyFilters = (patch: Partial<ReleaseFilterState>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    if (patch.query !== undefined) setQueryInput(patch.query);
  };

  const clearFilters = () => {
    setQueryInput("");
    setFilters(DEFAULT_RELEASE_FILTERS);
  };

  useEffect(() => {
    if (!years.length) return;
    const next = resolveYear(years, routeYear);
    if (next !== year) setYear(next);
  }, [routeYear, years, year]);

  const selectYear = (nextYear: string) => {
    setYear(nextYear);
    onNavigate?.(nextYear, null);
  };

  const selectOcid = (ocid: string) => {
    setSelectedOcid(ocid);
    setTab("summary");
    onNavigate?.(year, ocid);
  };

  useEffect(() => {
    if (!year) {
      setCache(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    setCache(null);
    setSelectedOcid(null);
    setQueryInput("");
    setFilters(DEFAULT_RELEASE_FILTERS);
    setFiltersOpen(false);
    fetchYearBrowserCache(baseUrl, year)
      .then((payload) => {
        if (cancelled) return;
        setCache(payload);
        const preferred =
          routeOcid && payload.index.some((s) => s.ocid === routeOcid)
            ? routeOcid
            : (payload.index[0]?.ocid ?? null);
        setSelectedOcid(preferred);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [baseUrl, year]);

  useEffect(() => {
    if (!cache || !routeOcid) return;
    if (cache.index.some((s) => s.ocid === routeOcid)) {
      setSelectedOcid(routeOcid);
    }
  }, [cache, routeOcid]);

  const summaries = cache?.index ?? [];

  const facets = useMemo(() => buildReleaseFilterFacets(summaries), [summaries]);

  const detailOcids = useMemo(
    () => new Set(Object.keys(cache?.releases ?? {})),
    [cache?.releases],
  );

  const filtered = useMemo(() => {
    return summaries.filter((summary) =>
      releaseMatchesFilters(summary, filters, { detailOcids }),
    );
  }, [summaries, filters, detailOcids]);

  const filtersActive = hasActiveReleaseFilters(filters);

  useEffect(() => {
    activeItemRef.current?.scrollIntoView({ block: "nearest" });
  }, [selectedOcid, filtered.length]);

  const activeSummary = useMemo(() => {
    if (!filtered.length) return null;
    if (selectedOcid) {
      const match = filtered.find((s) => s.ocid === selectedOcid);
      if (match) return match;
    }
    return filtered[0] ?? null;
  }, [filtered, selectedOcid]);

  const cachedRelease = activeSummary
    ? (cache?.releases[activeSummary.ocid] as Record<string, unknown> | undefined)
    : undefined;

  const [fetchedRelease, setFetchedRelease] = useState<Record<string, unknown> | null>(null);
  const [releaseLoading, setReleaseLoading] = useState(false);
  const [releaseError, setReleaseError] = useState<string | null>(null);

  useEffect(() => {
    setFetchedRelease(null);
    setReleaseError(null);
    setReleaseLoading(false);
  }, [activeSummary?.ocid, year]);

  useEffect(() => {
    if (tab !== "json" || !activeSummary || cachedRelease) return;

    let cancelled = false;
    setReleaseLoading(true);
    setReleaseError(null);
    fetchReleaseDetail(baseUrl, year, activeSummary.ocid)
      .then((release) => {
        if (!cancelled) setFetchedRelease(release);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setReleaseError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) setReleaseLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [tab, activeSummary, cachedRelease, baseUrl, year]);

  const activeRelease = cachedRelease ?? fetchedRelease ?? undefined;

  const yearMeta = years.find((y) => y.year === year);

  if (years.length === 0) {
    return (
      <Card>
        <span className="muted">No calendar-year packages available yet. Run the ETL merge step.</span>
      </Card>
    );
  }

  return (
    <Card className="release-browser">
      <div className="release-browser-toolbar">
        <label className="release-browser-year-label">
          Calendar year
          <select
            className="release-browser-year-select"
            value={year}
            onChange={(e) => selectYear(e.target.value)}
            aria-label="Calendar year"
          >
            {years.map((y) => (
              <option key={y.year} value={y.year}>
                {y.year} ({y.compiled_release_count.toLocaleString()} releases)
              </option>
            ))}
          </select>
        </label>
        {yearMeta && (
          <span className="muted release-browser-year-meta">
            {yearMeta.package_mb.toLocaleString()} MB merged package
            {yearMeta.source_file_count > 1
              ? ` · ${yearMeta.source_file_count} source files`
              : ""}
          </span>
        )}
      </div>

      {loading && (
        <p className="muted release-browser-status">Loading {year} releases…</p>
      )}
      {error && (
        <p className="release-browser-status release-browser-error">{error}</p>
      )}

      {!loading && !error && cache && (
        <div className="release-browser-layout">
          <aside className="release-browser-sidebar">
            <div className="release-browser-sidebar-head">
              <div className="release-browser-count">
                {filtersActive ? (
                  <>
                    {filtered.length.toLocaleString()} of {cache.index_count.toLocaleString()} match
                  </>
                ) : (
                  <>{cache.index_count.toLocaleString()} listed</>
                )}
                {cache.index_truncated && (
                  <span className="muted"> (first {cache.index_count.toLocaleString()} of {cache.compiled_release_count.toLocaleString()})</span>
                )}
                <span className="muted">
                  {" "}
                  · {cache.detail_count.toLocaleString()} with full JSON
                </span>
              </div>
              <ReleaseBrowserFilters
                queryInput={queryInput}
                filters={filters}
                facets={facets}
                open={filtersOpen}
                active={filtersActive}
                onOpenChange={setFiltersOpen}
                onQueryInputChange={setQueryInput}
                onApplyQueryNow={() => applyFilters({ query: queryInput })}
                onChange={applyFilters}
                onClear={clearFilters}
              />
            </div>
            <ul className="release-browser-list" role="listbox" aria-label="Releases for selected year">
              {filtered.length === 0 ? (
                <li className="release-browser-empty muted">No releases match your search.</li>
              ) : (
                filtered.map((summary) => (
                  <li key={summary.ocid}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={summary.ocid === activeSummary?.ocid}
                      ref={summary.ocid === activeSummary?.ocid ? activeItemRef : undefined}
                      className={`release-browser-item${summary.ocid === activeSummary?.ocid ? " active" : ""}`}
                      onClick={() => selectOcid(summary.ocid)}
                    >
                      <div className="release-browser-item-title">{summary.title}</div>
                      <div className="release-browser-item-meta">
                        <span>{summary.buyer}</span>
                        <span className="release-browser-item-dot" aria-hidden>
                          ·
                        </span>
                        <span>{formatMoney(summary.award)}</span>
                        {summary.awardCount > 1 && (
                          <>
                            <span className="release-browser-item-dot" aria-hidden>
                              ·
                            </span>
                            <span>{summary.awardCount} awards</span>
                          </>
                        )}
                      </div>
                      <div className="release-browser-item-foot">
                        <span className="mono">{summary.ocid}</span>
                        {String(summary.philgeps.solicitationNo ?? "").trim() && (
                          <span className="muted mono" style={{ fontSize: 11 }}>
                            {String(summary.philgeps.solicitationNo)}
                          </span>
                        )}
                        <span>{summary.dateLabel}</span>
                      </div>
                    </button>
                  </li>
                ))
              )}
            </ul>
          </aside>

          <div className="release-browser-main">
            {activeSummary ? (
              <ReleaseDetail
                year={year}
                release={activeRelease}
                summary={activeSummary}
                detailCount={cache.detail_count}
                tab={tab}
                releaseLoading={releaseLoading}
                releaseError={releaseError}
                onTabChange={setTab}
              />
            ) : (
              <span className="muted">Select a release from the list.</span>
            )}
          </div>
        </div>
      )}

      <div className="muted release-browser-foot">
        Dataset total: {totalCount.toLocaleString()} releases across all years · caches served from{" "}
        <code className="mono">{baseUrl}/&#123;year&#125;.json</code>
      </div>
    </Card>
  );
}

const SEARCH_FIELD_OPTIONS: { value: ReleaseSearchField; label: string }[] = [
  { value: "all", label: "All fields" },
  { value: "title", label: "Title" },
  { value: "buyer", label: "Buyer" },
  { value: "supplier", label: "Supplier" },
  { value: "identifier", label: "OCID / id / solicitation" },
  { value: "award", label: "Award no. / title" },
];

function ReleaseBrowserFilters({
  queryInput,
  filters,
  facets,
  open,
  active,
  onOpenChange,
  onQueryInputChange,
  onApplyQueryNow,
  onChange,
  onClear,
}: {
  queryInput: string;
  filters: ReleaseFilterState;
  facets: ReturnType<typeof buildReleaseFilterFacets>;
  open: boolean;
  active: boolean;
  onOpenChange: (open: boolean) => void;
  onQueryInputChange: (value: string) => void;
  onApplyQueryNow: () => void;
  onChange: (patch: Partial<ReleaseFilterState>) => void;
  onClear: () => void;
}) {
  return (
    <div className="release-browser-filters">
      <div className="release-browser-search-row">
        <input
          type="search"
          className="search-input release-browser-search"
          placeholder="Search…"
          value={queryInput}
          onChange={(e) => onQueryInputChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") onApplyQueryNow();
          }}
          aria-label="Search releases"
        />
        <button
          type="button"
          className={`release-browser-filters-toggle${open ? " active" : ""}${active ? " has-active" : ""}`}
          onClick={() => onOpenChange(!open)}
          aria-expanded={open}
        >
          Filters{active ? " ·" : ""}
        </button>
      </div>

      {open && (
        <div className="release-browser-filters-panel">
          <label className="release-browser-filter-field">
            <span>Search in</span>
            <select
              value={filters.field}
              onChange={(e) => onChange({ field: e.target.value as ReleaseSearchField })}
            >
              {SEARCH_FIELD_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="release-browser-filter-field">
            <span>Category</span>
            <select
              value={filters.category}
              onChange={(e) => onChange({ category: e.target.value })}
            >
              <option value="">Any</option>
              {facets.categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>

          <label className="release-browser-filter-field">
            <span>Procurement method</span>
            <select
              value={filters.procurementMethod}
              onChange={(e) => onChange({ procurementMethod: e.target.value })}
            >
              <option value="">Any</option>
              {facets.procurementMethods.map((method) => (
                <option key={method} value={method}>
                  {method}
                </option>
              ))}
            </select>
          </label>

          <label className="release-browser-filter-field">
            <span>Min award total (PHP)</span>
            <input
              type="text"
              inputMode="decimal"
              placeholder="e.g. 100000"
              value={filters.minAwardValue}
              onChange={(e) => onChange({ minAwardValue: e.target.value })}
            />
          </label>

          <div className="release-browser-filter-checks">
            <label className="release-browser-check">
              <input
                type="checkbox"
                checked={filters.multiAwardOnly}
                onChange={(e) => onChange({ multiAwardOnly: e.target.checked })}
              />
              Multi-award only
            </label>
            <label className="release-browser-check">
              <input
                type="checkbox"
                checked={filters.fullJsonOnly}
                onChange={(e) => onChange({ fullJsonOnly: e.target.checked })}
              />
              Full JSON cached
            </label>
          </div>

          {active && (
            <button type="button" className="release-browser-clear-filters" onClick={onClear}>
              Clear filters
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function ReleaseDetail({
  year,
  release,
  summary,
  detailCount,
  tab,
  releaseLoading,
  releaseError,
  onTabChange,
}: {
  year: string;
  release: Record<string, unknown> | undefined;
  summary: ReleaseSummary;
  detailCount: number;
  tab: DetailTab;
  releaseLoading: boolean;
  releaseError: string | null;
  onTabChange: (tab: DetailTab) => void;
}) {
  const philgepsEntries = Object.entries(summary.philgeps).filter(
    ([, v]) => v != null && String(v).trim() !== "" && String(v).toUpperCase() !== "NULL",
  );
  const hasFullRelease = release !== undefined;
  const awardRows = useMemo(
    () => (release ? collectAwards(release) : summary.awards ?? []),
    [release, summary.awards],
  );
  const contractRows = useMemo(
    () => (release ? collectContracts(release) : summary.contracts ?? []),
    [release, summary.contracts],
  );
  const tenderId = release
    ? String((release.tender as Record<string, unknown> | undefined)?.id ?? summary.id)
    : summary.id;

  return (
    <div className="release-detail">
      <div className="release-detail-header">
        <div className="release-detail-heading">
          <h3 className="release-detail-title">{summary.title}</h3>
          <div className="release-detail-badges">
            {summary.tags.map((tag) => (
              <Badge key={tag} variant="outline">
                {tag}
              </Badge>
            ))}
            <Badge variant="blue">{summary.initiationType}</Badge>
            {!hasFullRelease && (
              <Badge variant="amber">Summary only</Badge>
            )}
          </div>
          <div className="release-detail-identifiers mono">
            <span>{summary.ocid}</span>
            <span className="muted">·</span>
            <span>id {summary.id}</span>
            <span className="muted">·</span>
            <span>{summary.dateLabel}</span>
          </div>
        </div>
        <div className="release-detail-tabs" role="tablist" aria-label="Release view">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "summary"}
            className={`release-detail-tab${tab === "summary" ? " active" : ""}`}
            onClick={() => onTabChange("summary")}
          >
            Summary
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "json"}
            className={`release-detail-tab${tab === "json" ? " active" : ""}`}
            onClick={() => onTabChange("json")}
          >
            Raw JSON
          </button>
        </div>
      </div>

      <div className="release-detail-body">
      {tab === "summary" ? (
        <div className="release-detail-summary">
          <div className="card-grid cols-4 release-detail-stats">
            <MetricCard label="Award value" value={formatMoney(summary.award)} />
            <MetricCard label="Tender estimate" value={formatMoney(summary.tender)} />
            <MetricCard label="Buyer" value={summary.buyer} />
            <MetricCard label="Supplier" value={summary.supplier} />
          </div>

          <div className="card-grid cols-2">
            <Card>
              <div className="release-section-title">Procurement</div>
              <dl className="kv-list release-kv">
                <dt>Release id</dt>
                <dd className="mono">{summary.id}</dd>
                <dt>Tender id (bid ref)</dt>
                <dd className="mono">{tenderId}</dd>
                {String(summary.philgeps.solicitationNo ?? "").trim() && (
                  <>
                    <dt>Solicitation no.</dt>
                    <dd className="mono">{String(summary.philgeps.solicitationNo)}</dd>
                  </>
                )}
                <dt>Method</dt>
                <dd>{summary.procurementMethod}</dd>
                <dt>Category</dt>
                <dd>{summary.category}</dd>
                <dt>Tender status</dt>
                <dd>{summary.tenderStatus}</dd>
                <dt>Award status</dt>
                <dd>{summary.awardStatus}</dd>
                <dt>Awards</dt>
                <dd>{summary.awardCount}</dd>
                <dt>Parties</dt>
                <dd>{summary.partyCount}</dd>
              </dl>
            </Card>

            <Card>
              <div className="release-section-title">Timeline</div>
              <dl className="kv-list release-kv">
                <dt>Tender opens</dt>
                <dd>{summary.tenderStart}</dd>
                <dt>Tender closes</dt>
                <dd>{summary.tenderEnd}</dd>
                <dt>Award date</dt>
                <dd>{summary.awardDate}</dd>
                <dt>Contract start</dt>
                <dd>{summary.contractStart}</dd>
                <dt>Contract end</dt>
                <dd>{summary.contractEnd}</dd>
              </dl>
            </Card>
          </div>

          {summary.parties.length > 0 && (
            <Card>
              <div className="release-section-title">Parties</div>
              <div className="release-party-list">
                {summary.parties.map((party) => (
                  <div key={party.name + party.roles.join(",")} className="release-party-row">
                    <div className="release-party-name">{party.name}</div>
                    <div className="pill-row">
                      {party.roles.map((role) => (
                        <span key={role} className="pill">
                          {role}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {awardRows.length > 0 && (
            <Card>
              <div className="release-section-title">
                Awards
                <span className="muted release-section-count">{awardRows.length}</span>
              </div>
              <div className="table-wrap">
                <table className="data-table release-items-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Title</th>
                      <th>Supplier</th>
                      <th>Date</th>
                      <th>Status</th>
                      <th>Value</th>
                      <th>Items</th>
                    </tr>
                  </thead>
                  <tbody>
                    {awardRows.map((award) => (
                      <tr key={award.id + award.title}>
                        <td className="mono">{award.id}</td>
                        <td>{award.title}</td>
                        <td>{award.supplier}</td>
                        <td>{award.date}</td>
                        <td>{award.status}</td>
                        <td>{award.value}</td>
                        <td>{award.itemCount > 0 ? award.itemCount : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {contractRows.length > 0 && (
            <Card>
              <div className="release-section-title">
                Contracts
                <span className="muted release-section-count">{contractRows.length}</span>
              </div>
              <div className="table-wrap">
                <table className="data-table release-items-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Award</th>
                      <th>Status</th>
                      <th>Value</th>
                      <th>Start</th>
                      <th>End</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contractRows.map((contract) => (
                      <tr key={contract.id + contract.awardId}>
                        <td className="mono">{contract.id}</td>
                        <td className="mono">{contract.awardId}</td>
                        <td>{contract.status}</td>
                        <td>{contract.value}</td>
                        <td>{contract.startDate}</td>
                        <td>{contract.endDate}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {summary.items.length > 0 && (
            <Card>
              <div className="release-section-title">
                Line items
                <span className="muted release-section-count">{summary.items.length}</span>
              </div>
              <div className="table-wrap">
                <table className="data-table release-items-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Description</th>
                      <th>Qty</th>
                      <th>Unit</th>
                      <th>Unit price</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.items.map((item) => (
                      <tr key={item.id + item.description}>
                        <td className="mono">{item.id}</td>
                        <td>{item.description}</td>
                        <td>{item.quantity}</td>
                        <td>{item.unit}</td>
                        <td>{item.unitPrice}</td>
                        <td>{item.total}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {philgepsEntries.length > 0 && (
            <Card>
              <div className="release-section-title">PhilGEPS extension</div>
              <dl className="kv-list release-kv">
                {philgepsEntries.map(([key, value]) => (
                  <div key={key}>
                    <dt>{humanizeKey(key)}</dt>
                    <dd>{String(value)}</dd>
                  </div>
                ))}
              </dl>
            </Card>
          )}

          <Card>
            <div className="release-section-title">OCDS blocks present</div>
            <div className="block-jumps">
              {OCDS_BLOCKS.map((block) => {
                const present =
                  release !== undefined
                    ? release[block.key] !== undefined
                    : blockPresenceFromSummary(block.key, summary);
                return (
                  <span
                    key={block.key}
                    className={`block-jump${present ? "" : " muted"}`}
                    title={present ? `${block.label} block included` : "Not in this release"}
                  >
                    {block.label}
                    {!present && " ·"}
                  </span>
                );
              })}
            </div>
          </Card>
        </div>
      ) : releaseLoading ? (
        <Card>
          <p className="muted">Loading release JSON…</p>
        </Card>
      ) : releaseError ? (
        <Card>
          <p className="release-browser-error">{releaseError}</p>
          <p className="muted">
            Cached full JSON is available for {detailCount.toLocaleString()} releases in this year.
            Larger year packages load on demand when under the dev-server size cap.
          </p>
        </Card>
      ) : hasFullRelease ? (
        <LazyJsonView
          value={release}
          filename={`${summary.ocid}.json`}
          maxHeight="100%"
        />
      ) : (
        <Card>
          <p className="muted">
            Full release JSON could not be loaded. The complete package is in{" "}
            <code className="mono">references/transformed/by_year/{year}.json</code>.
          </p>
        </Card>
      )}
      </div>
    </div>
  );
}

function blockPresenceFromSummary(blockKey: string, summary: ReleaseSummary): boolean {
  switch (blockKey) {
    case "buyer":
      return summary.buyer !== "—";
    case "tender":
      return summary.title !== "—" || summary.tender.amount != null;
    case "awards":
      return summary.awardCount > 0;
    case "contracts":
      return summary.contractStart !== "—" || summary.contractEnd !== "—";
    case "parties":
      return summary.partyCount > 0;
    case "bids":
      return false;
    case "philgeps":
      return Object.keys(summary.philgeps).length > 0;
    default:
      return false;
  }
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <div className="card-title">{label}</div>
      <div className="card-value release-metric-value">{value}</div>
    </Card>
  );
}

function humanizeKey(key: string): string {
  return key
    .replace(/([A-Z])/g, " $1")
    .replace(/^./, (c) => c.toUpperCase())
    .trim();
}
