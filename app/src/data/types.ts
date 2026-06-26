// Types matching the bundled JSON produced by scripts/build_schema_field_map.py
// (see app_bundle schema in build_app_bundle).

export type SchemaKey = "schema_1" | "schema_2" | "schema_3" | "schema_4" | "schema_5";

export const SCHEMA_KEYS: SchemaKey[] = [
  "schema_1",
  "schema_2",
  "schema_3",
  "schema_4",
  "schema_5",
];

export type FieldTypeId =
  | "string"
  | "decimal"
  | "integer"
  | "date"
  | "datetime"
  | "string_array";

export type CrosswalkStatus =
  | "mapped"
  | "omit"
  | "derived"
  | "extension"
  | "constant"
  | "unmapped";

export interface SchemaPeriod {
  key: SchemaKey;
  short_key: string;
  label: string;
  period: string;
  format: string;
  columns: number;
  key_change: string;
  source_columns: Record<string, string>;
}

export interface CanonicalField {
  canonical_field: string;
  field_type: FieldTypeId | null;
  category: string | null;
  semantic_name: string | null;
  source_columns: Partial<Record<SchemaKey, string>>;
  present_in_schemas: SchemaKey[];
  ocds_paths: string[];
  evolution_notes: string | null;
  canonical_ai: string;
  excluded: boolean;
}

export interface SemanticFieldEntry {
  field_name: string;
  schema_1_2_2000_2020: string | null;
  schema_3_2021_2024: string | null;
  schema_4_5_2025_v2: string | null;
  evolution_notes: string | null;
}

export interface SemanticGroup {
  category: string;
  fields: SemanticFieldEntry[];
}

export interface CrosswalkRow {
  ocds_field: string;
  ocds_block: string;
  philgeps_1_5: string;
  philgeps_2_0: string;
  v2_csv: string;
  v1_csv: string;
  canonical: string;
  status: CrosswalkStatus;
}

export interface StagedPath {
  path: string;
  canonical: string;
  is_constant: boolean;
}

export interface StagedBlock {
  block: string;
  paths: StagedPath[];
}

export interface GeneratedFieldSpec {
  field: string;
  spec: unknown;
}

export interface OcdsStaged {
  version: string;
  ocid_prefix: string;
  extensions: string[];
  planning_triggers: string[];
  generated: GeneratedFieldSpec[];
  blocks: StagedBlock[];
  defaults: Record<string, string | string[]>;
}

export interface CodelistEntry {
  philgeps: string;
  ocds: string;
}

export interface CodelistSection {
  name: string;
  label: string;
  entries: CodelistEntry[];
}

export interface BundleMetadata {
  title: string;
  generated_at: string;
  schema_analysis_date: string;
  ocds_template: string;
  ocds_mapping_version: string;
  ocid_prefix: string;
  sources: Record<string, string>;
}

export interface BundleSummary {
  schema_count: number;
  canonical_field_count: number;
  crosswalk_row_count: number;
  crosswalk_with_ocds: number;
  crosswalk_mapped: number;
  crosswalk_omit: number;
  crosswalk_derived: number;
  crosswalk_extension: number;
  staged_block_count: number;
  codelist_count: number;
  semantic_group_count: number;
}

export interface SchemaBundle {
  metadata: BundleMetadata;
  schemas: Record<SchemaKey, SchemaPeriod>;
  semantic_grouping: SemanticGroup[];
  canonical_fields: CanonicalField[];
  field_types: Record<string, string[]>;
  excluded_source_columns: string[];
  ocds_crosswalk: CrosswalkRow[];
  ocds_staged: OcdsStaged;
  ocds_release: OcdsReleasePayload;
  codelists: CodelistSection[];
  ocds_reverse: Record<string, string[]>;
  summary: BundleSummary;
}

export interface OcdsReleaseSummary {
  ocid: string;
  release_id: string;
  release_date: string;
  version: string;
  initiation_type: string;
  tag: string[];
  language: string;
  publisher: string;
  extensions: string[];
  top_level_blocks: string[];
  tender_item_count: number;
  award_count: number;
  contract_count: number;
  party_count: number;
  bid_count: number;
  has_planning: boolean;
  has_extension: boolean;
  tender_keys: string[];
  award_keys: string[];
  contract_keys: string[];
}

export interface OcdsReleasePayload {
  package: Record<string, unknown>;
  release: Record<string, unknown>;
  summary: OcdsReleaseSummary;
}
