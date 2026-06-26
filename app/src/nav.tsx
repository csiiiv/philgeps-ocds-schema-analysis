import type { ReactNode } from "react";

export interface NavItem {
  id: string;
  label: string;
  icon: ReactNode;
  group: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

// Simple inline SVG icons (no dependency).
function Icon({ d }: { d: string }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {d.split("|").map((seg, i) => (
        <path key={i} d={seg} />
      ))}
    </svg>
  );
}

export const NAV_ITEMS: NavItem[] = [
  {
    id: "overview",
    label: "Overview",
    group: "Start",
    icon: <Icon d="M3 12l9-9 9 9M5 10v10h14V10" />,
  },
  {
    id: "search",
    label: "Global search",
    group: "Start",
    icon: <Icon d="M11 4a7 7 0 100 14 7 7 0 000-14zM21 21l-4.3-4.3" />,
  },
  {
    id: "canonical",
    label: "Canonical fields",
    group: "Schemas",
    icon: <Icon d="M4 6h16M4 12h16M4 18h10" />,
  },
  {
    id: "periods",
    label: "Schema periods (S1–S5)",
    group: "Schemas",
    icon: <Icon d="M3 5h18M3 12h18M3 19h18" />,
  },
  {
    id: "evolution",
    label: "Schema evolution",
    group: "Schemas",
    icon: <Icon d="M3 17l6-6 4 4 8-8M14 7h7v7" />,
  },
  {
    id: "lookup",
    label: "Source column lookup",
    group: "Schemas",
    icon: <Icon d="M11 4a7 7 0 100 14 7 7 0 000-14zM21 21l-4.3-4.3" />,
  },
  {
    id: "crosswalk",
    label: "OCDS crosswalk",
    group: "OCDS mapping",
    icon: <Icon d="M8 7h-3v10h3M16 7h3v10h-3M3 12h18" />,
  },
  {
    id: "staged",
    label: "OCDS staged output",
    group: "OCDS mapping",
    icon: <Icon d="M4 4h16v6H4zM4 14h16v6H4zM8 7h.01M8 17h.01" />,
  },
  {
    id: "release",
    label: "OCDS release package",
    group: "OCDS mapping",
    icon: <Icon d="M21 8l-5-5H7a2 2 0 00-2 2v14a2 2 0 002 2h12a2 2 0 002-2V8zM14 3v5h5M9 13h6M9 17h4" />,
  },
  {
    id: "codelists",
    label: "Codelist mappings",
    group: "OCDS mapping",
    icon: <Icon d="M9 7H5a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6v6h-6zM10 14l4-4" />,
  },
  {
    id: "about",
    label: "About & sources",
    group: "Start",
    icon: <Icon d="M12 9v4M12 17h.01M10.3 3.86l-8 14A2 2 0 004 21h16a2 2 0 001.7-3.14l-8-14a2 2 0 00-3.4 0z" />,
  },
];

export function groupedNav(): NavGroup[] {
  const groups: NavGroup[] = [];
  const order = ["Start", "Schemas", "OCDS mapping"];
  for (const label of order) {
    const items = NAV_ITEMS.filter((i) => i.group === label);
    if (items.length) groups.push({ label, items });
  }
  return groups;
}
