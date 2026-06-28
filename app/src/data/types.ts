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
  transform_available?: boolean;
  transform_scope?: "single_file" | "full_dataset";
  transform_release_count?: number;
  transform_release_sample_count?: number;
  transform_source_file_count?: number;
  transform_calendar_year_count?: number;
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
  transform: TransformBundle | null;
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

// ---------------------------------------------------------------------------
// ETL Pipeline section (transform stats + corpus embed)
// ---------------------------------------------------------------------------

export interface TransformSeverityCounts {
  error: number;
  warning: number;
  info: number;
}

export interface TransformRuleCount {
  rule: string;
  severity: "error" | "warning" | "info";
  count: number;
}

export interface TransformIssueGroupCount {
  rule: string;
  severity: "error" | "warning" | "info";
  field: string;
  pattern: string;
  count: number;
}

export interface RowAccountingBreakdownStep {
  id: string;
  label: string;
  count: number;
  detail: string;
}

export interface RowAccounting {
  rows_seen: number;
  rows_committed: number;
  rows_quarantined: number;
  compile_accounting: {
    rows_excluded_no_award: number;
    rows_excluded_no_process_key: number;
    rows_grouped: number;
    process_group_count: number;
    rows_merged_into_groups: number;
    releases_compiled: number;
  };
  merge_accounting?: {
    releases_before_dedup: number;
    releases_after_dedup: number;
    duplicate_ocids_overwritten: number;
    scope?: "year" | "overall";
  } | null;
  breakdown: RowAccountingBreakdownStep[];
  estimated?: boolean;
}

export interface TransformQuarantinedIssue {
  rule: string;
  severity: "error" | "warning" | "info";
  field: string;
  value: unknown;
  message: string;
}

export interface TransformQuarantinedSample {
  row_index?: number;
  row_entry?: Record<string, unknown>;
  raw_row?: Record<string, string>;
  award_reference_no?: string;
  group_key?: string;
  row_indices?: number[];
  row_indices_omitted?: number;
  issues: TransformQuarantinedIssue[];
}

export interface TransformInputSample {
  award_reference_no: string;
  raw_row: Record<string, string>;
  release: Record<string, unknown>;
  row_count: number;
}

export interface TransformYearSummary {
  year: string;
  compiled_release_count: number;
  package_mb: number;
  source_file_count: number;
  all_passed: boolean;
  severity_counts: TransformSeverityCounts;
}

export interface TransformBundle {
  scope?: "single_file" | "full_dataset" | "calendar_year";
  calendar_year?: string;
  input_file: string;
  input_bytes: number;
  schema_detected: string;
  mapped_column_count: number;
  unmapped_columns: string[];
  header: string[];
  rows_seen: number;
  rows_committed: number;
  rows_quarantined: number;
  severity_counts: TransformSeverityCounts;
  rule_counts: TransformRuleCount[];
  issue_group_counts?: TransformIssueGroupCount[];
  quarantined_samples: TransformQuarantinedSample[];
  quarantined_samples_omitted?: number;
  warning_samples: TransformQuarantinedSample[];
  warning_samples_omitted?: number;
  info_samples: TransformQuarantinedSample[];
  info_samples_omitted?: number;
  compiled_release_count: number;
  source_file_count?: number;
  source_files?: { path: string; dq_path?: string; input_file?: string; compiled_release_count?: number }[];
  calendar_year_count?: number;
  duplicate_ocids_overwritten?: number;
  package_mb_total?: number;
  years?: TransformYearSummary[];
  releases_sample?: Record<string, unknown>[];
  /** Base URL for per-year browser caches (dev: /data/releases/{year}.json). */
  release_browser_base_url?: string;
  input_samples?: TransformInputSample[];
  package_path?: string;
  combined_report_path?: string;
  display_id_collisions?: Record<string, unknown>[];
  row_accounting?: RowAccounting;
}
