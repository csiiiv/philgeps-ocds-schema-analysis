import { classNames } from "./helpers";

export function SearchInput({
  value,
  onChange,
  placeholder = "Search…",
  autoFocus,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
}) {
  return (
    <input
      type="search"
      className="search-input"
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      autoFocus={autoFocus}
    />
  );
}

export function SelectInput<T extends string>({
  value,
  onChange,
  options,
  allLabel,
  ariaLabel,
}: {
  value: T | "all";
  onChange: (v: T | "all") => void;
  options: { value: T; label: string }[];
  allLabel?: string;
  ariaLabel?: string;
}) {
  return (
    <select
      className="select-input"
      value={value}
      onChange={(e) => onChange(e.target.value as T | "all")}
      aria-label={ariaLabel}
    >
      {allLabel && <option value="all">{allLabel}</option>}
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

export interface ChipOption<T extends string> {
  value: T;
  label: string;
  count?: number;
  dot?: string;
}

export function ChipFilter<T extends string>({
  options,
  value,
  onChange,
}: {
  options: ChipOption<T>[];
  value: T | "all";
  onChange: (v: T | "all") => void;
}) {
  return (
    <div className="chip-group" role="group">
      <button
        className={classNames("chip", value === "all" && "active")}
        onClick={() => onChange("all")}
      >
        All
      </button>
      {options.map((opt) => (
        <button
          key={opt.value}
          className={classNames("chip", value === opt.value && "active")}
          onClick={() => onChange(opt.value)}
        >
          {opt.dot && <span className={`dot ${opt.dot}`} />}
          {opt.label}
          {opt.count !== undefined && (
            <span style={{ opacity: 0.7, marginLeft: 2 }}>{opt.count}</span>
          )}
        </button>
      ))}
    </div>
  );
}

export function RowCount({ count, total }: { count: number; total: number }) {
  return (
    <span className="row-count">
      {count} / {total} rows
    </span>
  );
}
