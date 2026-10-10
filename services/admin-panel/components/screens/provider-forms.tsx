"use client";
import { useState } from "react";
import { object, type Entity } from "@/lib/api";
import { useAction, useItems } from "@/lib/hooks";
import {
  editableFields,
  fields,
  minorUnits,
  options,
  trades,
} from "@/lib/property";
import { State } from "../common";
import { RegisteredFields } from "./registered-fields";
import { Button } from "../ui/Button";
import { FormInput, FormSelect, FormTextarea } from "../ui/Input";

export function ProviderForm({
  entity,
  onClose,
}: {
  entity?: Entity;
  onClose: () => void;
}) {
  const registry = useItems("entity-types");
  const schema = object(
    registry.data?.items.find((row) => row.id === "service_provider")?.fields,
  );
  const original = entity
    ? fields(entity)
    : {
        ref: "",
        trading_name: "",
        legal_name: "",
        business_type: "sole trader",
        trades: [],
        emails: [],
        phone_main: null,
        phone_emergency: null,
        postcode_districts: [],
        emergency_callout: false,
        booking_method: "email",
        status: "trial",
        accreditations: [],
      };
  const [name, setName] = useState(entity?.name ?? "");
  const [description, setDescription] = useState(entity?.description ?? "");
  const [values, setValues] = useState<Record<string, unknown>>(
    editableFields(original, schema),
  );
  const [reason, setReason] = useState("");
  const [error, setError] = useState<Error | null>(null);
  const action = useAction();
  return (
    <form
      className="form mb-8"
      onSubmit={(e) => {
        e.preventDefault();
        setError(null);
        try {
          const clean = editableFields(values, schema);
          action.mutate(
            {
              path: entity
                ? `providers/${encodeURIComponent(entity.id)}`
                : "providers",
              method: entity ? "PATCH" : "POST",
              body: {
                ...(!entity ? { type: "service_provider" } : {}),
                name,
                description,
                fields: clean,
                ...(entity ? { version: entity.version, reason } : {}),
              },
            },
            { onSuccess: onClose },
          );
        } catch (reason) {
          setError(
            reason instanceof Error
              ? reason
              : new Error("Invalid provider fields"),
          );
        }
      }}
    >
      <FormInput
        label="Provider name"
        required
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <FormTextarea
        label="Description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <State
        pending={registry.isPending}
        error={registry.error}
        retry={() => void registry.refetch()}
      />
      <RegisteredFields schema={schema} value={values} onChange={setValues} />
      {entity && (
        <FormInput
          label="Reason for change"
          required
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
      )}
      <p className="caption">
        Outcome metrics are calculated from tickets and expenses. Bank details
        are kept outside this graph.
      </p>
      <State error={error ?? action.error} />
      <div className="actions">
        <Button loading={action.isPending} disabled={!registry.data}>
          {entity ? "Save provider" : "Add provider"}
        </Button>
        <Button type="button" variant="ghost" onClick={onClose}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
export function OfferingForm({
  provider,
  onClose,
}: {
  provider: string;
  onClose: () => void;
}) {
  const registry = useItems("entity-types");
  const schema = object(
    registry.data?.items.find((row) => row.id === "service_offering")?.fields,
  );
  const tradeValues = Array.isArray(object(schema.trade).enum)
    ? (object(schema.trade).enum as string[])
    : trades;
  const models = Array.isArray(object(schema.pricing_model).enum)
    ? (object(schema.pricing_model).enum as string[])
    : [
        "fixed",
        "hourly",
        "day rate",
        "call-out + hourly",
        "per unit",
        "quote only",
      ];
  const [values, setValues] = useState({
    name: "",
    description: "",
    trade: "plumbing",
    pricing_model: "fixed",
    price: "",
    callout: "",
    source: "admin",
    confirmed: new Date().toISOString().slice(0, 10),
    vat: "true",
    evidence: "",
    unit: "",
  });
  const action = useAction();
  const [error, setError] = useState<Error | null>(null);
  const input = (key: keyof typeof values) => ({
    value: values[key],
    onChange: (
      e: React.ChangeEvent<
        HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
      >,
    ) => setValues({ ...values, [key]: e.target.value }),
  });
  return (
    <form
      className="form mb-8"
      onSubmit={(e) => {
        e.preventDefault();
        setError(null);
        try {
          const priceKey =
            values.pricing_model === "hourly" ||
            values.pricing_model === "call-out + hourly"
              ? "hourly_rate_minor"
              : values.pricing_model === "day rate"
                ? "day_rate_minor"
                : "price_minor";
          action.mutate(
            {
              path: `providers/${encodeURIComponent(provider)}/offerings`,
              body: {
                name: values.name,
                description: values.description,
                fields: {
                  name: values.name,
                  trade: values.trade,
                  description: values.description,
                  pricing_model: values.pricing_model,
                  ...(values.price
                    ? { [priceKey]: minorUnits(values.price) }
                    : {}),
                  ...(values.callout
                    ? { callout_fee_minor: minorUnits(values.callout) }
                    : {}),
                  ...(values.unit ? { unit: values.unit } : {}),
                  vat_included: values.vat === "true",
                  price_source: values.source,
                  valid_from: values.confirmed,
                  last_confirmed_at: values.confirmed,
                },
                ...(values.evidence
                  ? { evidence: [{ chunk_id: values.evidence }] }
                  : {}),
              },
            },
            { onSuccess: onClose },
          );
        } catch (reason) {
          setError(
            reason instanceof Error ? reason : new Error("Invalid price"),
          );
        }
      }}
    >
      <FormInput label="Service name" required {...input("name")} />
      <FormTextarea
        label="Scope and exclusions"
        required
        {...input("description")}
      />
      <div className="form-row">
        <FormSelect
          label="Trade"
          options={options(tradeValues)}
          {...input("trade")}
        />
        <FormSelect
          label="Pricing model"
          options={options(models)}
          {...input("pricing_model")}
        />
      </div>
      <div className="form-row">
        <FormInput
          label="Price or rate (GBP)"
          inputMode="decimal"
          {...input("price")}
        />
        <FormInput
          label="Call-out fee (GBP)"
          inputMode="decimal"
          {...input("callout")}
        />
      </div>
      <div className="form-row">
        <FormInput
          label="Unit (optional)"
          placeholder="per metre"
          {...input("unit")}
        />
        <FormSelect
          label="VAT"
          options={[
            { value: "true", label: "Included" },
            { value: "false", label: "Excluded" },
          ]}
          {...input("vat")}
        />
      </div>
      <div className="form-row">
        <FormSelect
          label="Price source"
          options={options([
            "website",
            "quote",
            "invoice",
            "call",
            "email",
            "admin",
          ])}
          {...input("source")}
        />
        <FormInput
          label="Last confirmed"
          type="date"
          required
          {...input("confirmed")}
        />
      </div>
      <FormInput label="Source chunk ID (optional)" {...input("evidence")} />
      <State error={error ?? action.error} />
      <div className="actions">
        <Button loading={action.isPending}>Add offering</Button>
        <Button type="button" variant="ghost" onClick={onClose}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
export function QuoteForm({
  provider,
  onClose,
}: {
  provider: string;
  onClose: () => void;
}) {
  const [values, setValues] = useState({
    ticket: "",
    ref: "",
    amount: "",
    scope: "",
    exclusions: "",
    valid: "",
    start: "",
    vat: "true",
    status: "received",
  });
  const action = useAction();
  const [error, setError] = useState<Error | null>(null);
  const input = (key: keyof typeof values) => ({
    value: values[key],
    onChange: (
      e: React.ChangeEvent<
        HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
      >,
    ) => setValues({ ...values, [key]: e.target.value }),
  });
  return (
    <form
      className="form mb-8"
      onSubmit={(e) => {
        e.preventDefault();
        setError(null);
        try {
          action.mutate(
            {
              path: "quotes",
              body: {
                provider_id: provider,
                ticket_id: values.ticket,
                fields: {
                  amount_minor: minorUnits(values.amount),
                  scope: values.scope,
                  exclusions: values.exclusions,
                  vat_included: values.vat === "true",
                  status: values.status,
                  ...(values.ref ? { ref: values.ref } : {}),
                  ...(values.valid ? { valid_until: values.valid } : {}),
                  ...(values.start ? { earliest_start: values.start } : {}),
                },
              },
            },
            { onSuccess: onClose },
          );
        } catch (reason) {
          setError(
            reason instanceof Error ? reason : new Error("Invalid quote"),
          );
        }
      }}
    >
      <div className="form-row">
        <FormInput label="Ticket ID" required {...input("ticket")} />
        <FormInput label="Provider quote reference" {...input("ref")} />
      </div>
      <div className="form-row">
        <FormInput
          label="Total (GBP)"
          inputMode="decimal"
          required
          {...input("amount")}
        />
        <FormSelect
          label="VAT"
          options={[
            { value: "true", label: "Included" },
            { value: "false", label: "Excluded" },
          ]}
          {...input("vat")}
        />
      </div>
      <FormTextarea label="Scope" required {...input("scope")} />
      <FormTextarea label="Exclusions" {...input("exclusions")} />
      <div className="form-row">
        <FormInput label="Earliest start" type="date" {...input("start")} />
        <FormInput label="Valid until" type="date" {...input("valid")} />
      </div>
      <FormSelect
        label="Status"
        options={options(["requested", "received", "declined"])}
        {...input("status")}
      />
      <State error={error ?? action.error} />
      <div className="actions">
        <Button loading={action.isPending}>Record quote</Button>
        <Button type="button" variant="ghost" onClick={onClose}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
