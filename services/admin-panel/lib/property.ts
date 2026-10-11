import { object, str, type RecordData } from "./api";

export const categories = [
  "rent_due",
  "rent_received",
  "tenant_recharge",
  "deposit_received",
  "deposit_deduction",
  "deposit_returned",
  "management_fee",
  "expense",
  "service_charge",
  "ground_rent",
  "utility",
  "council_tax",
  "insurance",
  "compliance",
  "landlord_contribution",
  "landlord_payout",
  "refund",
  "adjustment",
];
export const trades = [
  "plumbing",
  "heating/gas",
  "electrical",
  "roofing",
  "guttering",
  "drainage",
  "carpentry",
  "locksmith",
  "glazing",
  "damp/mould",
  "pest control",
  "appliance repair",
  "decorating",
  "plastering",
  "flooring",
  "cleaning",
  "gardening",
  "handyman",
  "general building",
];
export const providerStatuses = [
  "preferred",
  "approved",
  "trial",
  "suspended",
  "do_not_use",
];
export const label = (value: string) => value.replaceAll("_", " ");
export const options = (values: string[]) =>
  values.map((value) => ({ value, label: label(value) }));
export function money(value: unknown): string {
  if (value === null || value === undefined || !Number.isFinite(Number(value)))
    return "—";
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: "GBP",
  }).format(Number(value) / 100);
}
/** Decimal input is converted without floating-point rounding of money. */
export function minorUnits(value: string): number {
  if (!/^\d+(\.\d{1,2})?$/.test(value.trim()))
    throw new Error(
      "Enter a positive GBP amount with up to two decimal places",
    );
  const [whole, fraction = ""] = value.trim().split(".");
  const amount = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
  if (!Number.isSafeInteger(amount) || amount <= 0)
    throw new Error("Amount must be positive and within the supported range");
  return amount;
}
export function queryPath(
  path: string,
  filters: Record<string, string>,
): string {
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, value]) => value !== ""),
  );
  return params.size ? `${path}?${params}` : path;
}
export function fields(row: RecordData): Record<string, unknown> {
  return object(row.fields);
}
export function entityHref(row: RecordData): string {
  const section =
    row.type === "property"
      ? "properties"
      : row.type === "service_provider"
        ? "providers"
        : "entities";
  return `/${section}/${encodeURIComponent(row.id)}`;
}
export function expiry(
  value: unknown,
  now = new Date(),
): "expired" | "expiring" | "valid" | "unknown" {
  if (!value) return "unknown";
  const date = new Date(String(value));
  if (!Number.isFinite(date.getTime())) return "unknown";
  const days =
    Math.floor(date.getTime() / 86400000) -
    Math.floor(now.getTime() / 86400000);
  return days < 0 ? "expired" : days <= 30 ? "expiring" : "valid";
}
export function stalePrice(value: unknown, now = new Date()): boolean {
  const cutoff = new Date(now);
  cutoff.setMonth(cutoff.getMonth() - 6);
  return (
    !value ||
    new Date(String(value)).getTime() < cutoff.getTime() ||
    Number.isNaN(new Date(String(value)).getTime())
  );
}
export function recordName(row: RecordData): string {
  return str(row.name ?? fields(row).ref ?? row.id);
}
export function editableFields(
  values: Record<string, unknown>,
  schema: Record<string, unknown>,
): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(values).filter(([key]) => {
      const spec = object(schema[key]);
      const derived = [
        "tenant_balance_minor",
        "landlord_balance_minor",
        "deposit_held_minor",
        "jobs_completed",
        "avg_response_hours",
        "first_time_fix_rate",
        "avg_job_cost_minor",
        "rating",
      ];
      return (
        !derived.includes(key) &&
        !spec.read_only &&
        !spec.readonly &&
        !spec.derived
      );
    }),
  );
}

/** Version change since an edit began; edits save against `from` so the API rejects stale writes. */
export function editConflict(base: { version: number }, current: { version: number }) {
  return current.version === base.version ? null : { from: base.version, to: current.version };
}
