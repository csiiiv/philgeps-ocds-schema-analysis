import { useEffect } from "react";
import { useRoute, Layout } from "./components/Layout";
import { OverviewPage } from "./pages/OverviewPage";
import { CanonicalPage } from "./pages/CanonicalPage";
import { CrosswalkPage } from "./pages/CrosswalkPage";
import { StagedPage } from "./pages/StagedPage";
import { ReleasePage } from "./pages/ReleasePage";
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
  periods: PeriodsPage,
  codelists: CodelistsPage,
  lookup: LookupPage,
  evolution: EvolutionPage,
  search: SearchPage,
  about: AboutPage,
};

export function App() {
  const route = useRoute();
  const Page = ROUTES[route] ?? OverviewPage;

  useEffect(() => {
    const valid = NAV_ITEMS.map((i) => i.id);
    const titleBase = "PhilGEPS Schema Explorer";
    const item = NAV_ITEMS.find((i) => i.id === route);
    document.title = item ? `${item.label} · ${titleBase}` : titleBase;
    if (route && !valid.includes(route)) {
      window.location.hash = "/overview";
    }
    window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
  }, [route]);

  return (
    <Layout route={route}>
      <Page />
    </Layout>
  );
}
