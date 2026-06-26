import { classNames, typeBadgeClass, type BadgeVariant, type DotVariant } from "./helpers";
import type { SchemaKey } from "../data/types";
import { SCHEMA_SHORT_KEYS } from "../data/bundle";

export function Badge({
  children,
  variant = "",
  title,
}: {
  children: React.ReactNode;
  variant?: BadgeVariant;
  title?: string;
}) {
  return (
    <span className={classNames("badge", variant)} title={title}>
      {children}
    </span>
  );
}

export function Dot({ variant = "" }: { variant?: DotVariant }) {
  return <span className={classNames("dot", variant)} />;
}

export function TypeBadge({ type }: { type: string | null | undefined }) {
  if (!type) return null;
  return <Badge variant={typeBadgeClass(type)}>{type}</Badge>;
}

/**
 * Renders the S1–S5 presence pills for a canonical field.
 * `presentIn` is the list of schema keys where the field has a non-null column.
 */
export function SchemaPills({
  presentIn,
  titleFor,
}: {
  presentIn: SchemaKey[] | Partial<Record<SchemaKey, string | null>>;
  titleFor?: Partial<Record<SchemaKey, string | null>>;
}) {
  const keys: SchemaKey[] = ["schema_1", "schema_2", "schema_3", "schema_4", "schema_5"];
  const presentSet = Array.isArray(presentIn)
    ? new Set(presentIn)
    : new Set(keys.filter((k) => presentIn[k]));
  return (
    <span className="schema-pills">
      {keys.map((k) => {
        const on = presentSet.has(k);
        const title = titleFor?.[k] ?? (on ? "Present" : "Not in this schema");
        return (
          <span
            key={k}
            className={classNames("schema-pill", on && "on")}
            title={title as string}
          >
            {SCHEMA_SHORT_KEYS[k]}
          </span>
        );
      })}
    </span>
  );
}

export function PathCode({ path }: { path: string }) {
  const segments = path.split("/");
  return (
    <span className="path-code">
      {segments.map((seg, i) => (
        <span key={i}>
          {i > 0 && <span className="path-sep">/</span>}
          {seg}
        </span>
      ))}
    </span>
  );
}

export function EmDash() {
  return <span className="em-dash">—</span>;
}

export function Card({
  children,
  className,
  interactive,
  onClick,
}: {
  children: React.ReactNode;
  className?: string;
  interactive?: boolean;
  onClick?: () => void;
}) {
  return (
    <div
      className={classNames("card", interactive && "interactive", className)}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {children}
    </div>
  );
}
