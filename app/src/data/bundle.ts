import bundleJson from "./schema_bundle.json";
import type { SchemaBundle, SchemaKey, CanonicalField } from "./types";

export const bundle = bundleJson as unknown as SchemaBundle;

export const SCHEMA_KEY_LIST: SchemaKey[] = [
  "schema_1",
  "schema_2",
  "schema_3",
  "schema_4",
  "schema_5",
];

export const SCHEMA_SHORT_KEYS: Record<SchemaKey, string> = {
  schema_1: "S1",
  schema_2: "S2",
  schema_3: "S3",
  schema_4: "S4",
  schema_5: "S5",
};

export const SCHEMA_PERIOD_LABELS: Record<SchemaKey, string> = {
  schema_1: "2000–2015",
  schema_2: "2016–2020",
  schema_3: "2021–2024",
  schema_4: "2025",
  schema_5: "2021–2024-V2",
};

/** Build a lookup: canonical field name -> field object. */
const canonicalFieldIndex: Map<string, CanonicalField> = new Map(
  bundle.canonical_fields.map((f) => [f.canonical_field, f]),
);

export function getCanonicalField(name: string): CanonicalField | undefined {
  return canonicalFieldIndex.get(name);
}

export function formatTimestamp(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}
