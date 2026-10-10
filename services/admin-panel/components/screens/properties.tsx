"use client";
import Link from "next/link";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  endpoint,
  object,
  rows,
  str,
  type Entity,
  type RecordData,
} from "@/lib/api";
import { useAction, useData, useItems, useLive } from "@/lib/hooks";
import { fields, money, queryPath } from "@/lib/property";
import { Header, Records, Section, State, Status } from "../common";
import { Button } from "../ui/Button";
import { FormInput, FormSelect } from "../ui/Input";
import { Balances, EntityLink, Facts, Related } from "./property-common";
import { PropertyLedger } from "./property-ledger";
import { PropertyEditor } from "./property-editor";

export function Properties({ id }: { id?: string }) {
  return id ? <PropertyDetail id={id} /> : <PropertyList />;
}
function PropertyList() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [create, setCreate] = useState(false);
  const data = useItems(queryPath("properties", { q, status }));
  return (
    <>
      <Header title="Properties">
        <Button
          variant={create ? "ghost" : "default"}
          onClick={() => setCreate(!create)}
        >
          {create ? "Close form" : "Add property"}
        </Button>
      </Header>
      {create && <NewProperty onClose={() => setCreate(false)} />}
      <div className="filter-row">
        <FormInput
          label="Find property"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Reference or address"
        />
        <FormSelect
          label="Status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          options={[
            { value: "", label: "All statuses" },
            ...["let", "vacant", "void_works", "off_market"].map((value) => ({
              value,
              label: value.replaceAll("_", " "),
            })),
          ]}
        />
      </div>
      <State
        pending={data.isPending}
        error={data.error}
        retry={() => void data.refetch()}
      />
      {data.data && (
        <Records
          items={data.data.items}
          columns={[
            {
              key: "name",
              title: "Property",
              render: (row) => <EntityLink row={row} />,
            },
            {
              key: "ref",
              title: "Reference",
              render: (row) => str(fields(row).ref),
            },
            {
              key: "status",
              title: "Status",
              render: (row) => <Status value={fields(row).status} />,
            },
            {
              key: "rent",
              title: "Rent",
              render: (row) => (
                <span className="tabular-nums">
                  {money(fields(row).rent_amount_minor)} /{" "}
                  {str(fields(row).rent_frequency)}
                </span>
              ),
            },
            {
              key: "balance",
              title: "Tenant balance",
              render: (row) => money(fields(row).tenant_balance_minor),
            },
          ]}
        />
      )}
    </>
  );
}
function NewProperty({ onClose }: { onClose: () => void }) {
  const action = useAction();
  const [values, setValues] = useState({
    ref: "",
    address_line1: "",
    postcode: "",
    rent: "",
    status: "vacant",
    frequency: "monthly",
    day: "1",
  });
  const input = (key: keyof typeof values) => ({
    value: values[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setValues({ ...values, [key]: e.target.value }),
  });
  return (
    <Section title="Add property">
      <form
        className="form"
        onSubmit={(e) => {
          e.preventDefault();
          action.mutate(
            {
              path: "entities",
              body: {
                type: "property",
                name: `${values.address_line1}, ${values.postcode}`,
                description: "",
                fields: {
                  ref: values.ref,
                  address_line1: values.address_line1,
                  postcode: values.postcode,
                  address_text: `${values.address_line1}, ${values.postcode}`,
                  status: values.status,
                  rent_amount_minor: values.rent
                    ? Math.round(Number(values.rent) * 100)
                    : 0,
                  rent_frequency: values.frequency,
                  rent_due_day: Number(values.day),
                  property_type: "flat",
                  bedrooms: 0,
                  bathrooms: 0,
                },
              },
            },
            { onSuccess: onClose },
          );
        }}
      >
        <div className="form-row">
          <FormInput label="Reference" required {...input("ref")} />
          <FormInput label="Address" required {...input("address_line1")} />
        </div>
        <div className="form-row">
          <FormInput label="Postcode" required {...input("postcode")} />
          <FormSelect
            label="Status"
            options={["let", "vacant", "void_works", "off_market"].map(
              (value) => ({ value, label: value.replaceAll("_", " ") }),
            )}
            {...input("status")}
          />
        </div>
        <div className="form-row">
          <FormInput
            label="Rent (GBP)"
            type="number"
            min="0"
            step="0.01"
            {...input("rent")}
          />
          <FormSelect
            label="Frequency"
            options={["weekly", "monthly", "quarterly"].map((value) => ({
              value,
              label: value,
            }))}
            {...input("frequency")}
          />
        </div>
        <FormInput
          label={
            values.frequency === "weekly"
              ? "Due weekday (1–7)"
              : "Due day (1–31)"
          }
          type="number"
          min="1"
          max={values.frequency === "weekly" ? "7" : "31"}
          {...input("day")}
        />
        <State error={action.error} />
        <div className="actions">
          <Button loading={action.isPending}>Add property</Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </form>
    </Section>
  );
}
function PropertyDetail({ id }: { id: string }) {
  const [edit, setEdit] = useState(false);
  const data = useData<Entity>(`properties/${encodeURIComponent(id)}`);
  useLive("entities/graph/stream");
  if (!data.data)
    return (
      <State
        pending={data.isPending}
        error={data.error}
        retry={() => void data.refetch()}
      />
    );
  const entity = data.data;
  return (
    <>
      <Header title={entity.name}>
        <Button
          onClick={() => setEdit(!edit)}
          variant={edit ? "ghost" : "default"}
        >
          {edit ? "Close editor" : "Edit property"}
        </Button>
        <Link
          className="draw-underline"
          href={`/graph?property=${encodeURIComponent(id)}&transactions=true`}
        >
          Explore ledger graph ↗
        </Link>
      </Header>
      <Balances value={entity.balances ?? entity.fields} />
      {edit && (
        <PropertyEditor
          key={entity.version}
          entity={entity}
          onClose={() => setEdit(false)}
        />
      )}
      <PropertyLedger id={id} />
      <div className="two-columns">
        <div>
          <Section title="Property details">
            <Facts value={entity.fields} />
          </Section>
          <Related title="Owners" value={entity.owners} landlord />
          <Related title="Tenants" value={entity.tenants} />
          <Related
            title="Managing company"
            value={
              entity.managing_companies ??
              (entity.managing_company
                ? [entity.managing_company]
                : entity.managers)
            }
          />
        </div>
        <div>
          <Related title="Open tickets" value={entity.open_tickets} />
          <Related title="Emails" value={entity.emails} />
          <Related title="Calls" value={entity.calls} />
        </div>
      </div>
    </>
  );
}
export function Landlords({ id }: { id?: string }) {
  return id ? <LandlordDetail id={id} /> : <LandlordList />;
}
function LandlordList() {
  const data = useItems("landlords");
  return (
    <>
      <Header title="Landlords" />
      <State
        pending={data.isPending}
        error={data.error}
        retry={() => void data.refetch()}
      />
      {data.data && (
        <Records
          items={data.data.items}
          columns={[
            {
              key: "name",
              title: "Landlord",
              render: (row) => <EntityLink row={row} landlord />,
            },
            {
              key: "properties",
              title: "Properties",
              render: (row) =>
                str(row.property_count ?? rows(row.properties).length),
            },
            {
              key: "balance",
              title: "Landlord balance",
              render: (row) =>
                money(object(row.balances).landlord_balance_minor),
            },
          ]}
        />
      )}
    </>
  );
}
function LandlordDetail({ id }: { id: string }) {
  const params = useSearchParams();
  const [period, setPeriod] = useState(
    params.get("period") ?? new Date().toISOString().slice(0, 7),
  );
  const data = useData<RecordData>(
    queryPath(`landlords/${encodeURIComponent(id)}/statement`, { period }),
  );
  const statement = data.data;
  return (
    <>
      <Header
        title={
          statement
            ? str(
                object(statement.landlord).name ??
                  object(statement.subject).name ??
                  statement.name ??
                  "Landlord statement",
              )
            : "Landlord statement"
        }
      >
        <a
          className="draw-underline"
          href={endpoint(
            queryPath(`statements/${encodeURIComponent(id)}`, {
              period,
              format: "pdf",
            }),
          )}
          download
        >
          Download statement ↗
        </a>
      </Header>
      <div className="filter-row">
        <FormInput
          label="Statement month"
          type="month"
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
        />
      </div>
      <State
        pending={data.isPending}
        error={data.error}
        retry={() => void data.refetch()}
      />
      {statement && (
        <>
          <Balances value={statement.balances} />
          <Section title="Owned properties">
            <Records
              items={rows(statement.properties).map((row) => ({
                ...object(row.property),
                id: str(object(row.property).id ?? row.id),
                share_pct: row.share_pct,
                balances: row.closing_balances ?? row.balances,
              }))}
              columns={[
                {
                  key: "name",
                  title: "Property",
                  render: (row) => <EntityLink row={row} />,
                },
                {
                  key: "share_pct",
                  title: "Ownership",
                  render: (row) => `${str(row.share_pct ?? 100)}%`,
                },
                {
                  key: "balance",
                  title: "Landlord balance",
                  render: (row) =>
                    money(
                      object(row.balances).landlord_balance_minor ??
                        fields(row).landlord_balance_minor,
                    ),
                },
              ]}
            />
          </Section>
          <p className="caption mt-6">
            Combined balances reflect ownership shares. Statement records money
            held and owed.
          </p>
        </>
      )}
    </>
  );
}
export function Unallocated() {
  const data = useItems("ledger/unallocated");
  return (
    <>
      <Header title="Unallocated ledger entries" />
      <p className="caption mb-6">
        The agent assigns these entries to properties after checking their
        references and evidence.
      </p>
      <State
        pending={data.isPending}
        error={data.error}
        retry={() => void data.refetch()}
      />
      {data.data && (
        <Records
          items={data.data.items.map((row) => ({
            ...row,
            fields: object(object(row.payload).fields ?? row.fields),
          }))}
          columns={[
            {
              key: "date",
              title: "Date",
              render: (row) =>
                str(fields(row).effective_date ?? row.effective_date),
            },
            {
              key: "counterparty",
              title: "Counterparty",
              render: (row) =>
                str(fields(row).counterparty_name ?? row.counterparty_name),
            },
            {
              key: "amount",
              title: "Amount",
              render: (row) =>
                money(fields(row).amount_minor ?? row.amount_minor),
            },
            {
              key: "description",
              title: "Description",
              render: (row) => str(fields(row).description ?? row.description),
            },
            {
              key: "external_ref",
              title: "Reference",
              render: (row) =>
                str(fields(row).external_ref ?? row.external_ref),
            },
          ]}
        />
      )}
    </>
  );
}
