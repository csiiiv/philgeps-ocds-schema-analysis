import type { ReleaseSummary } from "./releaseSummary";
import type { TransformYearSummary } from "../data/types";

export type { ReleaseSummary };

export interface YearBrowserCache {
  year: string;
  compiled_release_count: number;
  index_count: number;
  index_truncated: boolean;
  detail_count: number;
  index: ReleaseSummary[];
  releases: Record<string, Record<string, unknown>>;
}

export const DEFAULT_RELEASE_BROWSER_BASE = "/data/releases";

export function releaseBrowserUrl(base: string, year: string): string {
  const trimmed = base.replace(/\/$/, "");
  return `${trimmed}/${year}.json`;
}

export function pickDefaultYear(years: TransformYearSummary[]): string {
  if (years.length === 0) return "";
  const withData = years.filter((y) => y.compiled_release_count > 0);
  const list = withData.length > 0 ? withData : years;
  return list[list.length - 1]?.year ?? years[0].year;
}

export async function fetchYearBrowserCache(
  baseUrl: string,
  year: string,
): Promise<YearBrowserCache> {
  const response = await fetch(releaseBrowserUrl(baseUrl, year));
  if (!response.ok) {
    throw new Error(
      response.status === 404
        ? `No browser cache for ${year}. Run merge + build_year_browser_cache.py.`
        : `Failed to load ${year} (${response.status})`,
    );
  }
  return response.json() as Promise<YearBrowserCache>;
}

export function releaseDetailUrl(_baseUrl: string, year: string, ocid: string): string {
  // Use fixed base path for release details (not the browser cache base)
  const base = "/data/release";
  const trimmed = base.replace(/\/$/, "");
  return `${trimmed}/${year}/${encodeURIComponent(ocid)}.json`;
}

export async function fetchReleaseDetail(
  baseUrl: string,
  year: string,
  ocid: string,
): Promise<Record<string, unknown>> {
  const response = await fetch(releaseDetailUrl(baseUrl, year, ocid));
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { error?: string } | null;
    throw new Error(payload?.error ?? `Failed to load release (${response.status})`);
  }
  return response.json() as Promise<Record<string, unknown>>;
}
