import type { ReactNode } from "react";

export function DataTable({
  head,
  children,
  minWidth,
}: {
  head: ReactNode[];
  children: ReactNode;
  minWidth?: number;
}) {
  return (
    <div className="table-wrap">
      <div className="table-scroll">
        <table className="data-table" style={minWidth ? { minWidth } : undefined}>
          <thead>
            <tr>{head.map((h, i) => (
              <th key={i}>{h}</th>
            ))}</tr>
          </thead>
          <tbody>{children}</tbody>
        </table>
      </div>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="empty-state">{children}</div>;
}
