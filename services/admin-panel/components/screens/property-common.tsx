"use client";
import Link from "next/link";
import { object, rows, str, type RecordData } from "@/lib/api";
import { entityHref, fields, money, recordName } from "@/lib/property";
import { Section, Records } from "../common";
import { StatGrid } from "../library/StatGrid";

export function Balances({ value }: { value: unknown }) {
  const data = object(value);
  return (
    <StatGrid
      stats={[
        {
          label: "Tenant balance",
          value: money(data.tenant_balance_minor),
          title: "Positive means rent arrears",
        },
        {
          label: "Landlord balance",
          value: money(data.landlord_balance_minor),
          title: "Money held for the landlord",
        },
        { label: "Deposit held", value: money(data.deposit_held_minor) },
      ]}
    />
  );
}
export function EntityLink({
  row,
  landlord = false,
}: {
  row: RecordData;
  landlord?: boolean;
}) {
  const target = object(row.entity);
  const entity = target.id ? (target as RecordData) : row;
  return (
    <Link
      className="draw-underline"
      href={
        landlord
          ? `/landlords/${encodeURIComponent(entity.id)}`
          : entityHref(entity)
      }
    >
      {recordName(entity)}
    </Link>
  );
}
export function Related({
  title,
  value,
  landlord = false,
}: {
  title: string;
  value: unknown;
  landlord?: boolean;
}) {
  return (
    <Section title={title}>
      <Records
        items={rows(value)}
        columns={[
          {
            key: "name",
            title: "Name",
            render: (row) => <EntityLink row={row} landlord={landlord} />,
          },
          {
            key: "detail",
            title: "Details",
            render: (row) =>
              str(
                (row.share_pct ?? object(row.relationship).share_pct)
                  ? `${row.share_pct ?? object(row.relationship).share_pct}% ownership`
                  : (fields(row).status ??
                      fields(row).subject ??
                      fields(row).ref ??
                      ""),
              ),
          },
        ]}
      />
    </Section>
  );
}
export function Facts({ value }: { value: unknown }) {
  return (
    <dl className="fact-grid">
      {Object.entries(object(value)).map(([key, value]) => (
        <div key={key} className="fact">
          <dt>
            {key
              .replace(/_minor$/, "")
              .replace(/_pct$/, " (%)")
              .replaceAll("_", " ")}
          </dt>
          <dd>
            {key.endsWith("_minor")
              ? money(value)
              : Array.isArray(value)
                ? value
                    .map((item) =>
                      typeof item === "object"
                        ? Object.values(object(item))
                            .filter(Boolean)
                            .join(" · ")
                        : str(item),
                    )
                    .join(", ")
                : typeof value === "boolean"
                  ? value
                    ? "Yes"
                    : "No"
                  : str(value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}
