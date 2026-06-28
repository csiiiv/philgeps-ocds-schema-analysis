import { useEffect } from "react";
import { useRoute, Layout, parseRoute, routePageId } from "./components/Layout";
import { OverviewPage } from "./pages/OverviewPage";
import { CanonicalPage } from "./pages/CanonicalPage";
import { CrosswalkPage } from "./pages/CrosswalkPage";
import { StagedPage } from "./pages/StagedPage";
import { ReleasePage } from "./pages/ReleasePage";
import { EtlOverviewPage } from "./pages/EtlOverviewPage";
import { EtlQualityPage } from "./pages/EtlQualityPage";
import { EtlReleasesPage } from "./pages/EtlReleasesPage";
import { EtlOverallQualityPage } from "./pages/EtlOverallQualityPage";
import { EtlSamplesPage } from "./pages/EtlSamplesPage";
import { PeriodsPage } from "./pages/PeriodsPage";
import { CodelistsPage } from "./pages/CodelistsPage";
import { LookupPage } from "./pages/LookupPage";
import { EvolutionPage } from "./pages/EvolutionPage";
import { SearchPage } from "./pages/SearchPage";
import { AboutPage } from "./pages/AboutPage";
import { NAV_ITEMS } from "./nav";

const ROUTES: Record<string, () => React.ReactNode> = {
  overview: OverviewPage,
  canonical: CanonicalPage,
  crosswalk: CrosswalkPage,
  staged: StagedPage,
  release: ReleasePage,
  transform: EtlOverviewPage,
  "etl-overview": EtlOverviewPage,
  "etl-quality": EtlQualityPage,
  "etl-overall-quality": EtlOverallQualityPage,
  "etl-releases": EtlReleasesPage,
  "etl-samples": EtlSamplesPage,
  periods: PeriodsPage,
  codelists: CodelistsPage,
  lookup: LookupPage,
  evolution: EvolutionPage,
  search: SearchPage,
  about: AboutPage,
};

const LEGACY_ROUTE_REDIRECTS: Record<string, string> = {
  transform: "etl-overview",
  "etl-corpus-quality": "etl-overall-quality",
};

export function App() {
  const route = useRoute();
  const pageId = routePageId(route);
  const Page = ROUTES[pageId] ?? OverviewPage;

  useEffect(() => {
    const redirect = LEGACY_ROUTE_REDIRECTS[pageId];
    if (redirect) {
      window.location.hash = `/${redirect}`;
      return;
    }

    const valid = NAV_ITEMS.map((i) => i.id);
    const titleBase = "PhilGEPS Schema Explorer";
    const item = NAV_ITEMS.find((i) => i.id === pageId);
    const { segments } = parseRoute(route);
    let pageTitle = item?.label;
    if (pageId === "etl-releases" && segments[0]) {
      pageTitle = `${item?.label ?? "Release browser"} · ${segments[0]}`;
    }
    document.title = pageTitle ? `${pageTitle} · ${titleBase}` : titleBase;
    if (pageId && !valid.includes(pageId) && !ROUTES[pageId]) {
      window.location.hash = "/overview";
    }
    window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
  }, [route, pageId]);

  return (
    <Layout route={route}>
      <Page />
    </Layout>
  );
}
