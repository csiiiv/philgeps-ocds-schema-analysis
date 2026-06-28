import type { TransformBundle } from "../data/types";

export const DEFAULT_YEAR_DQ_BASE = "/data/dq";

export function yearDqUrl(base: string, year: string): string {
  const trimmed = base.replace(/\/$/, "");
  return `${trimmed}/${year}.json`;
}

export async function fetchYearDqBundle(
  baseUrl: string,
  year: string,
): Promise<TransformBundle> {
  const response = await fetch(yearDqUrl(baseUrl, year));
  if (!response.ok) {
    throw new Error(
      response.status === 404
        ? `No DQ cache for ${year}. Run merge + build_year_dq_cache.py --years ${year}.`
        : `Failed to load DQ for ${year} (${response.status})`,
    );
  }
  return response.json() as Promise<TransformBundle>;
}
