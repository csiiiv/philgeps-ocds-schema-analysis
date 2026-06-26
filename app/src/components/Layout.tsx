import { useEffect, useState, type ReactNode } from "react";
import { groupedNav } from "../nav";
import { bundle, formatTimestamp } from "../data/bundle";
import { classNames } from "./helpers";

export function getRouteFromHash(): string {
  const h = window.location.hash.replace(/^#\/?/, "");
  return h || "overview";
}

export function navigate(route: string) {
  window.location.hash = `/${route}`;
}

export function useRoute(): string {
  const [route, setRoute] = useState<string>(getRouteFromHash());
  useEffect(() => {
    const onHashChange = () => setRoute(getRouteFromHash());
    window.addEventListener("hashchange", onHashChange);
    if (!window.location.hash) {
      window.location.hash = "/overview";
    }
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  return route;
}

export function Layout({ route, children }: { route: string; children: ReactNode }) {
  const groups = groupedNav();
  const counts: Record<string, number> = {
    canonical: bundle.summary.canonical_field_count,
    crosswalk: bundle.summary.crosswalk_row_count,
    staged: bundle.summary.staged_block_count,
    codelists: bundle.summary.codelist_count,
    periods: bundle.summary.schema_count,
    evolution: bundle.summary.semantic_group_count,
  };
  return (
    <div className="app-shell">
      <header className="app-header">
        <a className="brand" href="#/overview">
          <span className="brand-mark">PG</span>
          <span>
            PhilGEPS Schema Explorer
            <span className="brand-sub"> · v{bundle.metadata.ocds_mapping_version}</span>
          </span>
        </a>
        <span style={{ flex: 1 }} />
        <a
          className="brand-sub"
          href="https://github.com/BetterGovPH/philgeps_data_analysis"
          target="_blank"
          rel="noreferrer"
          style={{ fontSize: 12.5 }}
        >
          Repo ↗
        </a>
      </header>
      <div className="app-body">
        <aside className="sidebar">
          {groups.map((g) => (
            <div key={g.label} className="nav-group">
              <div className="nav-group-label">{g.label}</div>
              {g.items.map((item) => {
                const count = counts[item.id];
                return (
                  <a
                    key={item.id}
                    href={`#/${item.id}`}
                    className={classNames("nav-item", route === item.id && "active")}
                  >
                    {item.icon}
                    <span>{item.label}</span>
                    {count !== undefined && (
                      <span className="nav-count">{count}</span>
                    )}
                  </a>
                );
              })}
            </div>
          ))}
        </aside>
        <main className="content">{children}</main>
      </div>
      <footer className="app-footer">
        <span>
          Generated {formatTimestamp(bundle.metadata.generated_at)} · Schema analysis{" "}
          {bundle.metadata.schema_analysis_date}
        </span>
        <span>
          Data from{" "}
          <code>
            scripts/build_schema_field_map.py → app/src/data/schema_bundle.json
          </code>
        </span>
      </footer>
    </div>
  );
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="page-header">
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
    </div>
  );
}

export function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="section-header">
      <h2>{title}</h2>
      {subtitle && <p>{subtitle}</p>}
    </div>
  );
}
