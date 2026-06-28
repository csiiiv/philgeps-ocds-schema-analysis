/** Parse OCDS release JSON into display-friendly fields for the release browser. */

export interface MoneyValue {
  amount: number | null;
  currency: string;
}

export interface ReleaseItemRow {
  id: string;
  description: string;
  quantity: string;
  unit: string;
  unitPrice: string;
  total: string;
}

export interface ReleasePartyRow {
  name: string;
  roles: string[];
}

export interface ReleaseAwardRow {
  id: string;
  title: string;
  status: string;
  date: string;
  value: string;
  supplier: string;
  itemCount: number;
}

export interface ReleaseContractRow {
  id: string;
  awardId: string;
  status: string;
  value: string;
  startDate: string;
  endDate: string;
}

export interface ReleaseSummary {
  ocid: string;
  id: string;
  date: string;
  dateLabel: string;
  title: string;
  buyer: string;
  supplier: string;
  award: MoneyValue;
  awardTotal: MoneyValue;
  tender: MoneyValue;
  tenderStatus: string;
  awardStatus: string;
  procurementMethod: string;
  category: string;
  tenderStart: string;
  tenderEnd: string;
  awardDate: string;
  contractStart: string;
  contractEnd: string;
  itemCount: number;
  awardCount: number;
  partyCount: number;
  tags: string[];
  initiationType: string;
  philgeps: Record<string, unknown>;
  items: ReleaseItemRow[];
  parties: ReleasePartyRow[];
  awards: ReleaseAwardRow[];
  contracts: ReleaseContractRow[];
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}

function asArray<T = unknown>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function str(value: unknown, fallback = "—"): string {
  if (value == null || value === "") return fallback;
  return String(value);
}

export function formatMoney(value: MoneyValue | null | undefined): string {
  if (!value || value.amount == null || Number.isNaN(value.amount)) return "—";
  const formatted = value.amount.toLocaleString(undefined, {
    minimumFractionDigits: value.amount % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  });
  return value.currency ? `${formatted} ${value.currency}` : formatted;
}

export function formatDateLabel(iso: unknown): string {
  const text = str(iso, "");
  if (!text || text === "—") return "—";
  const d = new Date(text);
  if (Number.isNaN(d.getTime())) return text.slice(0, 10);
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

function readMoney(obj: Record<string, unknown> | undefined): MoneyValue {
  const value = asRecord(obj?.value);
  const amount = typeof value?.amount === "number" ? value.amount : null;
  return { amount, currency: str(value?.currency, "PHP") };
}

function partyName(release: Record<string, unknown>, role: string): string {
  const parties = asArray<Record<string, unknown>>(release.parties);
  const match = parties.find((p) => asArray<string>(p.roles).includes(role));
  if (match?.name) return str(match.name);

  const buyer = asRecord(release.buyer);
  if (role === "buyer" && buyer?.name) return str(buyer.name);

  const awards = asArray<Record<string, unknown>>(release.awards);
  for (const award of awards) {
    const suppliers = asArray<Record<string, unknown>>(award.suppliers);
    if (suppliers[0]?.name) return str(suppliers[0].name);
  }
  return "—";
}

function collectItems(release: Record<string, unknown>): ReleaseItemRow[] {
  const tender = asRecord(release.tender);
  const tenderItems = asArray<Record<string, unknown>>(tender?.items);
  const awardItems = asArray<Record<string, unknown>>(release.awards).flatMap((a) =>
    asArray<Record<string, unknown>>(a.items),
  );
  const raw = tenderItems.length > 0 ? tenderItems : awardItems;

  return raw.map((item, index) => {
    const unit = asRecord(item.unit);
    const unitValue = asRecord(unit?.value);
    const qty = item.quantity ?? unit?.quantity;
    return {
      id: str(item.id, String(index + 1)),
      description: str(item.description ?? asRecord(item.classification)?.description, "—"),
      quantity: qty != null ? String(qty) : "—",
      unit: str(unit?.name, "—"),
      unitPrice: formatMoney({
        amount: typeof unitValue?.amount === "number" ? unitValue.amount : null,
        currency: str(unitValue?.currency, "PHP"),
      }),
      total: formatMoney(readMoney(item)),
    };
  });
}

function collectParties(release: Record<string, unknown>): ReleasePartyRow[] {
  return asArray<Record<string, unknown>>(release.parties).map((p) => ({
    name: str(p.name),
    roles: asArray<string>(p.roles),
  }));
}

function resolveSupplierName(
  suppliers: unknown,
  parties: Record<string, unknown>[],
): string {
  const refs = asArray<Record<string, unknown>>(suppliers);
  const first = refs[0];
  if (!first) return "—";
  if (first.name) return str(first.name);
  const supplierId = first.id;
  if (supplierId) {
    const party = parties.find((p) => p.id === supplierId);
    if (party?.name) return str(party.name);
  }
  return "—";
}

function totalAwardMoney(awards: Record<string, unknown>[]): MoneyValue {
  let total = 0;
  let hasAmount = false;
  let currency = "PHP";
  for (const award of awards) {
    const money = readMoney(award);
    if (money.amount != null) {
      total += money.amount;
      hasAmount = true;
      currency = money.currency;
    }
  }
  return { amount: hasAmount ? total : null, currency };
}

export function collectAwards(release: Record<string, unknown>): ReleaseAwardRow[] {
  const parties = asArray<Record<string, unknown>>(release.parties);
  return asArray<Record<string, unknown>>(release.awards).map((award, index) => ({
    id: str(award.id, String(index + 1)),
    title: str(award.title),
    status: str(award.status),
    date: formatDateLabel(award.date),
    value: formatMoney(readMoney(award)),
    supplier: resolveSupplierName(award.suppliers, parties),
    itemCount: asArray(award.items).length,
  }));
}

export function collectContracts(release: Record<string, unknown>): ReleaseContractRow[] {
  return asArray<Record<string, unknown>>(release.contracts).map((contract, index) => {
    const period = asRecord(contract.period);
    return {
      id: str(contract.id, String(index + 1)),
      awardId: str(contract.awardID ?? contract.awardId),
      status: str(contract.status),
      value: formatMoney(readMoney(contract)),
      startDate: formatDateLabel(period?.startDate),
      endDate: formatDateLabel(period?.endDate),
    };
  });
}

export function summarizeRelease(release: Record<string, unknown>): ReleaseSummary {
  const tender = asRecord(release.tender);
  const awards = asArray<Record<string, unknown>>(release.awards);
  const contracts = asArray<Record<string, unknown>>(release.contracts);
  const firstAward = awards[0];
  const firstContract = contracts[0];
  const contractPeriod = asRecord(firstContract?.period);
  const tenderPeriod = asRecord(tender?.tenderPeriod);
  const philgeps = asRecord(release.philgeps) ?? {};

  const title =
    str(tender?.title, "") !== "—"
      ? str(tender?.title)
      : str(firstAward?.title, str(release.ocid, "Untitled release"));

  return {
    ocid: str(release.ocid, "?"),
    id: str(release.id, "?"),
    date: str(release.date),
    dateLabel: formatDateLabel(release.date),
    title,
    buyer: partyName(release, "buyer"),
    supplier: partyName(release, "supplier"),
    award: readMoney(firstAward),
    awardTotal: totalAwardMoney(awards),
    tender: readMoney(tender),
    tenderStatus: str(tender?.status),
    awardStatus: str(firstAward?.status),
    procurementMethod: str(tender?.procurementMethodDetails ?? tender?.procurementMethod),
    category: str(tender?.mainProcurementCategory),
    tenderStart: formatDateLabel(tenderPeriod?.startDate),
    tenderEnd: formatDateLabel(tenderPeriod?.endDate),
    awardDate: formatDateLabel(firstAward?.date),
    contractStart: formatDateLabel(contractPeriod?.startDate),
    contractEnd: formatDateLabel(contractPeriod?.endDate),
    itemCount: collectItems(release).length,
    awardCount: awards.length,
    partyCount: asArray(release.parties).length,
    tags: asArray<string>(release.tag),
    initiationType: str(release.initiationType),
    philgeps,
    items: collectItems(release),
    parties: collectParties(release),
    awards: collectAwards(release),
    contracts: collectContracts(release),
  };
}

export function releaseMatchesQuery(summary: ReleaseSummary, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return [
    summary.ocid,
    summary.id,
    summary.title,
    summary.buyer,
    summary.supplier,
    summary.procurementMethod,
    summary.category,
    String(summary.philgeps["solicitationNo"] ?? ""),
    String(summary.philgeps["bidReferenceNo"] ?? ""),
    summary.awards.map((award) => [award.id, award.title, award.supplier].join(" ")).join(" "),
  ]
    .join(" ")
    .toLowerCase()
    .includes(q);
}
