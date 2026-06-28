import type { ReleaseSummary } from "./releaseSummary";

export type ReleaseSearchField =
  | "all"
  | "title"
  | "buyer"
  | "supplier"
  | "identifier"
  | "award";

export interface ReleaseFilterState {
  query: string;
  field: ReleaseSearchField;
  category: string;
  procurementMethod: string;
  multiAwardOnly: boolean;
  fullJsonOnly: boolean;
  minAwardValue: string;
}

export const DEFAULT_RELEASE_FILTERS: ReleaseFilterState = {
  query: "",
  field: "all",
  category: "",
  procurementMethod: "",
  multiAwardOnly: false,
  fullJsonOnly: false,
  minAwardValue: "",
};

export interface ReleaseFilterFacets {
  categories: string[];
  procurementMethods: string[];
}

export function buildReleaseFilterFacets(summaries: ReleaseSummary[]): ReleaseFilterFacets {
  const categories = new Set<string>();
  const procurementMethods = new Set<string>();

  for (const summary of summaries) {
    if (summary.category && summary.category !== "—") categories.add(summary.category);
    if (summary.procurementMethod && summary.procurementMethod !== "—") {
      procurementMethods.add(summary.procurementMethod);
    }
  }

  return {
    categories: [...categories].sort((a, b) => a.localeCompare(b)),
    procurementMethods: [...procurementMethods].sort((a, b) => a.localeCompare(b)),
  };
}

export function hasActiveReleaseFilters(filters: ReleaseFilterState): boolean {
  return (
    filters.query.trim() !== "" ||
    filters.field !== "all" ||
    filters.category !== "" ||
    filters.procurementMethod !== "" ||
    filters.multiAwardOnly ||
    filters.fullJsonOnly ||
    filters.minAwardValue.trim() !== ""
  );
}

function searchableText(summary: ReleaseSummary, field: ReleaseSearchField): string {
  switch (field) {
    case "title":
      return summary.title;
    case "buyer":
      return summary.buyer;
    case "supplier":
      return [summary.supplier, ...summary.awards.map((a) => a.supplier)].join(" ");
    case "identifier":
      return [
        summary.ocid,
        summary.id,
        String(summary.philgeps.solicitationNo ?? ""),
        String(summary.philgeps.bidReferenceNo ?? ""),
      ].join(" ");
    case "award":
      return summary.awards
        .map((award) => [award.id, award.title, award.supplier].join(" "))
        .join(" ");
    case "all":
    default:
      return [
        summary.ocid,
        summary.id,
        summary.title,
        summary.buyer,
        summary.supplier,
        summary.procurementMethod,
        summary.category,
        String(summary.philgeps.solicitationNo ?? ""),
        String(summary.philgeps.bidReferenceNo ?? ""),
        summary.awards.map((award) => [award.id, award.title, award.supplier].join(" ")).join(" "),
      ].join(" ");
  }
}

function awardAmountForFilter(summary: ReleaseSummary): number | null {
  if (summary.awardTotal?.amount != null) return summary.awardTotal.amount;
  return summary.award.amount;
}

export function releaseMatchesFilters(
  summary: ReleaseSummary,
  filters: ReleaseFilterState,
  options?: { detailOcids?: ReadonlySet<string> },
): boolean {
  const q = filters.query.trim().toLowerCase();
  if (q && !searchableText(summary, filters.field).toLowerCase().includes(q)) {
    return false;
  }

  if (filters.category && summary.category !== filters.category) return false;

  if (filters.procurementMethod && summary.procurementMethod !== filters.procurementMethod) {
    return false;
  }

  if (filters.multiAwardOnly && summary.awardCount <= 1) return false;

  if (filters.fullJsonOnly && !options?.detailOcids?.has(summary.ocid)) return false;

  const minRaw = filters.minAwardValue.trim().replace(/,/g, "");
  if (minRaw) {
    const min = Number(minRaw);
    if (!Number.isFinite(min)) return true;
    const amount = awardAmountForFilter(summary);
    if (amount == null || amount < min) return false;
  }

  return true;
}
