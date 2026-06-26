import type { CrosswalkStatus } from "../data/types";

export type BadgeVariant =
  | ""
  | "green"
  | "amber"
  | "red"
  | "purple"
  | "teal"
  | "blue"
  | "outline";

export type DotVariant = "" | "green" | "amber" | "red" | "purple" | "blue" | "gray";

export function classNames(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

export function highlight(text: string, query: string): string {
  if (!query.trim()) return text;
  const safe = query.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return text.replace(new RegExp(`(${safe})`, "gi"), "<mark>$1</mark>");
}

export function safeHtml(html: string): { __html: string } {
  return { __html: html };
}

const STATUS_META: Record<
  CrosswalkStatus,
  { label: string; dot: DotVariant; badge: BadgeVariant }
> = {
  mapped: { label: "Mapped", dot: "green", badge: "green" },
  omit: { label: "Omit", dot: "gray", badge: "" },
  derived: { label: "Derived", dot: "purple", badge: "purple" },
  extension: { label: "Extension", dot: "blue", badge: "teal" },
  constant: { label: "Constant", dot: "blue", badge: "blue" },
  unmapped: { label: "Unmapped", dot: "amber", badge: "amber" },
};

export function statusMeta(status: CrosswalkStatus) {
  return STATUS_META[status] ?? STATUS_META.mapped;
}

const TYPE_BADGE: Record<string, BadgeVariant> = {
  string: "",
  decimal: "blue",
  integer: "blue",
  date: "purple",
  datetime: "purple",
  string_array: "teal",
};

export function typeBadgeClass(typeId: string | null | undefined): BadgeVariant {
  if (!typeId) return "outline";
  return TYPE_BADGE[typeId] ?? "outline";
}

export function isPresent(value: string | null | undefined): boolean {
  return !!value && value !== "—" && !value.includes("REMOVED");
}

export function emDashIfEmpty(value: string | null | undefined): string {
  if (!value || value === "—") return "—";
  return value;
}
