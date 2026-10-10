"use client";
import Link from "next/link";
import { useState } from "react";
import { object, rows, str, type Entity } from "@/lib/api";
import { useAction, useData, useItems, useLive } from "@/lib/hooks";
import {
  expiry,
  fields,
  label,
  money,
  options,
  providerStatuses,
  queryPath,
  stalePrice,
  trades,
} from "@/lib/property";
import { Header, Records, Section, State, Status } from "../common";
import { Button } from "../ui/Button";
import { FormInput, FormSelect, FormTextarea } from "../ui/Input";
import { StatGrid } from "../library/StatGrid";
import { EntityLink, Facts, Related } from "./property-common";
import { OfferingForm, ProviderForm, QuoteForm } from "./provider-forms";
import { Evidence } from "./entities";

export function Providers({ id }: { id?: string }) {
  return id ? <ProviderDetail id={id} /> : <ProviderDirectory />;
}
function ProviderDirectory() {
  const [filter, setFilter] = useState({
    q: "",
    trade: "",
    postcode: "",
    status: "",
    min_rating: "",
    urgency: "",
  });
  const [create, setCreate] = useState(false);
  const data = useItems(queryPath("providers", filter));
  const registry = useItems("entity-types");
  const schema = registry.data?.items.find(
    (row) => row.id === "service_provider",
  );
  const tradeOptions = Array.isArray(object(object(schema?.fields).trades).enum)
    ? (object(object(schema?.fields).trades).enum as string[])
    : trades;
  const input = (key: keyof typeof filter) => ({
    value: filter[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setFilter({ ...filter, [key]: e.target.value }),
  });
  return (
    <>
      <Header title="Service providers">
        <Button
          variant={create ? "ghost" : "default"}
          onClick={() => setCreate(!create)}
        >
          {create ? "Close form" : "Add provider"}
        </Button>
      </Header>
      {create && <ProviderForm onClose={() => setCreate(false)} />}
      <div className="filter-row">
        <FormInput
          label="Find providers"
          placeholder="Name or service"
          {...input("q")}
        />
        <FormSelect
          label="Trade"
          options={[
            { value: "", label: "All trades" },
            ...options(tradeOptions),
          ]}
          {...input("trade")}
        />
        <FormInput
          label="Postcode or district"
          placeholder="E1"
          {...input("postcode")}
        />
      </div>
      <div className="filter-row">
        <FormSelect
          label="Status"
          options={[
            { value: "", label: "Available providers" },
            ...options(providerStatuses),
          ]}
          {...input("status")}
        />
        <FormSelect
          label="Urgency"
          options={[
            { value: "", label: "Any availability" },
            ...options(["routine", "urgent", "emergency"]),
          ]}
          {...input("urgency")}
        />
        <FormInput
          label="Minimum rating"
          type="number"
          min="1"
          max="5"
          step="0.5"
          {...input("min_rating")}
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
              title: "Provider",
              render: (row) => <EntityLink row={row} />,
            },
            {
              key: "trades",
              title: "Trades",
              render: (row) =>
                Array.isArray(fields(row).trades)
                  ? (fields(row).trades as string[]).map(label).join(", ")
                  : "—",
            },
            {
              key: "status",
              title: "Status",
              render: (row) => <Status value={fields(row).status} />,
            },
            {
              key: "area",
              title: "Coverage",
              render: (row) =>
                Array.isArray(fields(row).postcode_districts)
                  ? (fields(row).postcode_districts as string[]).join(", ")
                  : "—",
            },
            {
              key: "response",
              title: "Response",
              render: (row) => (
                <div>
                  {fields(row).emergency_callout
                    ? "Emergency call-out"
                    : "Routine"}
                  <p className="caption">
                    {fields(row).typical_response_hours != null
                      ? `${str(fields(row).typical_response_hours)} hours`
                      : ""}
                  </p>
                </div>
              ),
            },
            {
              key: "rating",
              title: "Rating",
              render: (row) => str(fields(row).rating),
            },
            {
              key: "offering",
              title: "Matching price",
              render: (row) => {
                const offer = rows(row.offerings)[0];
                return offer
                  ? money(
                      fields(offer).price_minor ??
                        fields(offer).hourly_rate_minor,
                    )
                  : "—";
              },
            },
          ]}
        />
      )}
    </>
  );
}
function ProviderDetail({ id }: { id: string }) {
  const data = useData<Entity>(`providers/${encodeURIComponent(id)}`);
  const action = useAction();
  const [edit, setEdit] = useState(false);
  const [offering, setOffering] = useState(false);
  const [quote, setQuote] = useState(false);
  const [changeStatus, setChangeStatus] = useState(false);
  const [status, setStatus] = useState("approved");
  const [reason, setReason] = useState("");
  useLive("entities/graph/stream");
  if (!data.data)
    return (
      <State
        pending={data.isPending}
        error={data.error}
        retry={() => void data.refetch()}
      />
    );
  const provider = data.data;
  const info = fields(provider);
  return (
    <>
      <Header title={provider.name}>
        <Status value={info.status} />
        <Button
          variant="ghost"
          onClick={() => {
            setChangeStatus(!changeStatus);
            setStatus(str(info.status));
          }}
        >
          Change status
        </Button>
        <Button
          variant={edit ? "ghost" : "default"}
          onClick={() => setEdit(!edit)}
        >
          {edit ? "Close editor" : "Edit provider"}
        </Button>
      </Header>
      <p className="lead">{provider.description}</p>
      <StatGrid
        stats={[
          { label: "Jobs completed", value: str(info.jobs_completed ?? 0) },
          { label: "Rating", value: info.rating ? `${info.rating} / 5` : "—" },
          {
            label: "First-time fixes",
            value:
              info.first_time_fix_rate != null
                ? `${Math.round(Number(info.first_time_fix_rate) * 100)}%`
                : "—",
          },
          {
            label: "Total spend",
            value: money(
              provider.total_spend_minor ?? provider.spend_minor ?? 0,
            ),
          },
        ]}
      />
      {edit && (
        <Section title="Edit provider">
          <ProviderForm entity={provider} onClose={() => setEdit(false)} />
        </Section>
      )}
      {changeStatus && (
        <Section title="Provider status">
          <form
            className="form"
            onSubmit={(e) => {
              e.preventDefault();
              action.mutate(
                {
                  path: `providers/${encodeURIComponent(id)}/status`,
                  body: { status, reason },
                },
                { onSuccess: () => setChangeStatus(false) },
              );
            }}
          >
            <FormSelect
              label="Status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              options={options(providerStatuses)}
            />
            <FormTextarea
              label="Reason"
              required
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <State error={action.error} />
            <Button loading={action.isPending}>Set status</Button>
          </form>
        </Section>
      )}
      <Section title="Services and prices">
        <div className="actions mb-6">
          <Button variant="ghost" onClick={() => setOffering(!offering)}>
            {offering ? "Close form" : "Add offering"}
          </Button>
        </div>
        {offering && (
          <OfferingForm provider={id} onClose={() => setOffering(false)} />
        )}
        <Records
          items={rows(provider.offerings)}
          columns={[
            {
              key: "name",
              title: "Service",
              render: (row) => (
                <div>
                  {str(row.name)}
                  <p className="caption whitespace-normal">
                    {str(fields(row).description)}
                  </p>
                </div>
              ),
            },
            {
              key: "model",
              title: "Pricing",
              render: (row) => label(str(fields(row).pricing_model)),
            },
            {
              key: "price",
              title: "Rate",
              render: (row) => (
                <div>
                  {money(
                    fields(row).price_minor ??
                      fields(row).hourly_rate_minor ??
                      fields(row).day_rate_minor,
                  )}
                  <p className="caption">
                    {fields(row).vat_included ? "VAT included" : "VAT excluded"}
                    {fields(row).callout_fee_minor != null
                      ? ` · Call-out ${money(fields(row).callout_fee_minor)}`
                      : ""}
                  </p>
                </div>
              ),
            },
            {
              key: "confirmed",
              title: "Confirmed",
              render: (row) => (
                <div>
                  {str(fields(row).last_confirmed_at)}
                  {stalePrice(fields(row).last_confirmed_at) && (
                    <p>
                      <Status value="price needs rechecking" />
                    </p>
                  )}
                </div>
              ),
            },
            {
              key: "source",
              title: "Source",
              render: (row) => (
                <div>
                  {str(fields(row).price_source)}
                  <details>
                    <summary className="draw-underline cursor-pointer">
                      Open evidence
                    </summary>
                    <Evidence evidence={rows(row.evidence)} />
                  </details>
                </div>
              ),
            },
          ]}
        />
      </Section>
      <div className="two-columns">
        <div>
          <Section title="Accreditations">
            <Records
              items={rows(info.accreditations).map((row, i) => ({
                ...row,
                id: row.id ?? String(i),
              }))}
              columns={[
                { key: "scheme", title: "Scheme" },
                { key: "number", title: "Registration" },
                {
                  key: "expires_on",
                  title: "Expiry",
                  render: (row) => (
                    <div>
                      {str(row.expires_on)}
                      <p>
                        <Status value={expiry(row.expires_on)} />
                      </p>
                    </div>
                  ),
                },
              ]}
            />
          </Section>
          <Section title="Public liability insurance">
            <p>{money(info.insurance_public_liability_minor)} cover</p>
            <p className="caption mt-2">
              Expires {str(info.insurance_expires_on)} ·{" "}
              <Status value={expiry(info.insurance_expires_on)} />
            </p>
          </Section>
          <Related title="Contacts" value={provider.contacts} />
          <Related
            title="Registered company"
            value={
              provider.registered_companies ??
              (provider.registered_as
                ? [provider.registered_as]
                : provider.companies)
            }
          />
        </div>
        <div>
          <Related
            title="Assigned tickets"
            value={provider.tickets ?? provider.recent_jobs}
          />
          <Section title="Quotes">
            <div className="actions mb-6">
              <Button variant="ghost" onClick={() => setQuote(!quote)}>
                {quote ? "Close form" : "Record quote"}
              </Button>
            </div>
            {quote && (
              <QuoteForm provider={id} onClose={() => setQuote(false)} />
            )}
            <Records
              items={rows(provider.quotes)}
              columns={[
                {
                  key: "ref",
                  title: "Quote",
                  render: (row) => str(fields(row).ref ?? row.name),
                },
                {
                  key: "amount",
                  title: "Amount",
                  render: (row) => money(fields(row).amount_minor),
                },
                {
                  key: "status",
                  title: "Status",
                  render: (row) => <Status value={fields(row).status} />,
                },
                {
                  key: "valid",
                  title: "Valid until",
                  render: (row) => str(fields(row).valid_until),
                },
                {
                  key: "accept",
                  title: "",
                  render: (row) =>
                    fields(row).status === "received" ? (
                      <Button
                        variant="ghost"
                        loading={action.isPending}
                        onClick={() =>
                          action.mutate({
                            path: `quotes/${encodeURIComponent(row.id)}/accept`,
                            body: {},
                          })
                        }
                      >
                        Accept quote
                      </Button>
                    ) : null,
                },
              ]}
            />
            <State error={action.error} />
            <p className="caption mt-4">
              Accepting assigns the ticket and records an expected expense.
            </p>
          </Section>
        </div>
      </div>
      <Section title="Provider details">
        <Facts value={info} />
      </Section>
      <Link
        className="draw-underline"
        href={`/graph?entity=${encodeURIComponent(id)}`}
      >
        Explore connections ↗
      </Link>
    </>
  );
}
