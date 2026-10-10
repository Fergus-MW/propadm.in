"use client";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { endpoint, object, rows, str, type RecordData } from "@/lib/api";
import { useAction, useData } from "@/lib/hooks";
import {
  categories,
  fields,
  label,
  minorUnits,
  money,
  options,
  queryPath,
} from "@/lib/property";
import { Confirm, Records, Section, State, Status } from "../common";
import { Button } from "../ui/Button";
import { FormInput, FormSelect, FormTextarea } from "../ui/Input";
import { RowMenu } from "../library/RowMenu";
import { Evidence } from "./entities";

export function PropertyLedger({ id }: { id: string }) {
  const params = useSearchParams();
  const [from, setFrom] = useState(params.get("from") ?? "");
  const [to, setTo] = useState(params.get("to") ?? "");
  const [category, setCategory] = useState(params.get("category") ?? "");
  const [create, setCreate] = useState(false);
  const [reverse, setReverse] = useState<RecordData | null>(null);
  const [reason, setReason] = useState("");
  const data = useData<RecordData>(
    queryPath(`properties/${encodeURIComponent(id)}/ledger`, {
      from,
      to,
      category,
    }),
  );
  const action = useAction();
  const transactions = rows(data.data?.transactions);
  const [period, setPeriod] = useState(new Date().toISOString().slice(0, 7));
  return (
    <Section title="Ledger">
      <div className="filter-row">
        <FormInput
          label="From"
          type="date"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
        />
        <FormInput
          label="To"
          type="date"
          value={to}
          min={from || undefined}
          onChange={(e) => setTo(e.target.value)}
        />
        <FormSelect
          label="Category"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          options={[
            { value: "", label: "All categories" },
            ...options(categories),
          ]}
        />
        <div className="actions">
          <Button
            variant={create ? "ghost" : "default"}
            onClick={() => setCreate(!create)}
          >
            {create ? "Close form" : "Record transaction"}
          </Button>
        </div>
      </div>
      {create && (
        <RecordTransaction property={id} onClose={() => setCreate(false)} />
      )}
      <State
        pending={data.isPending}
        error={data.error}
        retry={() => void data.refetch()}
      />
      {data.data && (
        <Records
          items={transactions}
          columns={[
            {
              key: "date",
              title: "Date",
              render: (row) => str(fields(row).effective_date),
            },
            {
              key: "description",
              title: "Transaction",
              render: (row) => (
                <div>
                  <strong>{label(str(fields(row).category))}</strong>
                  <p className="caption whitespace-normal">
                    {str(fields(row).description)}
                  </p>
                  <span className="mono">{str(fields(row).ref)}</span>
                </div>
              ),
            },
            {
              key: "counterparty",
              title: "Counterparty",
              render: (row) => str(fields(row).counterparty_name),
            },
            {
              key: "amount",
              title: "Amount",
              render: (row) => (
                <span className="tabular-nums">
                  {money(fields(row).amount_minor)}
                </span>
              ),
            },
            {
              key: "status",
              title: "Status",
              render: (row) => <Status value={fields(row).status} />,
            },
            {
              key: "running",
              title: "Running balances",
              render: (row) => {
                const balance = object(row.running_balances);
                return (
                  <div className="caption tabular-nums">
                    <p>Tenant {money(balance.tenant_balance_minor)}</p>
                    <p>Landlord {money(balance.landlord_balance_minor)}</p>
                    <p>Deposit {money(balance.deposit_held_minor)}</p>
                  </div>
                );
              },
            },
            {
              key: "evidence",
              title: "Evidence",
              render: (row) => (
                <details>
                  <summary className="draw-underline cursor-pointer">
                    Open sources
                  </summary>
                  <Evidence evidence={rows(row.evidence)} />
                </details>
              ),
            },
            {
              key: "actions",
              title: "",
              render: (row) => (
                <RowMenu
                  label={str(fields(row).ref)}
                  items={
                    row.is_reversal ||
                    row.reversed_by ||
                    fields(row).status === "void"
                      ? []
                      : [
                          {
                            label: "Reverse entry",
                            onSelect: () => {
                              setReverse(row);
                              setReason("");
                              action.reset();
                            },
                          },
                        ]
                  }
                />
              ),
            },
          ]}
        />
      )}
      <div className="filter-row mt-6">
        <FormInput
          label="Statement month"
          type="month"
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
        />
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
      </div>
      {reverse && (
        <Confirm
          title={`Reverse ${str(fields(reverse).ref)}?`}
          disabled={!reason.trim()}
          pending={action.isPending}
          onClose={() => setReverse(null)}
          onConfirm={() =>
            action.mutate(
              {
                path: `transactions/${encodeURIComponent(reverse.id)}/reverse`,
                body: { reason },
              },
              { onSuccess: () => setReverse(null) },
            )
          }
        >
          <span className="block mb-4">
            A reversing entry cancels {money(fields(reverse).amount_minor)}.
            Both entries remain in the ledger.
          </span>
          <FormTextarea
            label="Reason"
            required
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <State error={action.error} />
        </Confirm>
      )}
    </Section>
  );
}
const kinds: Record<string, string> = {
  rent_due: "charge",
  tenant_recharge: "charge",
  management_fee: "charge",
  deposit_deduction: "transfer",
  adjustment: "adjustment",
};
function RecordTransaction({
  property,
  onClose,
}: {
  property: string;
  onClose: () => void;
}) {
  const [values, setValues] = useState({
    category: "rent_received",
    amount: "",
    date: new Date().toISOString().slice(0, 10),
    counterparty: "",
    description: "",
    external_ref: "",
    status: "cleared",
    paid_by: "",
    paid_to: "",
    ticket: "",
    notes: "",
    evidence: "",
    adjustment_balance: "tenant",
    adjustment_direction: "increase",
  });
  const [error, setError] = useState<Error | null>(null);
  const action = useAction();
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
          const amount_minor = minorUnits(values.amount);
          action.mutate(
            {
              path: "transactions",
              body: {
                property_id: property,
                fields: {
                  kind: kinds[values.category] ?? "payment",
                  category: values.category,
                  amount_minor,
                  currency: "GBP",
                  effective_date: values.date,
                  status: values.status,
                  counterparty_name: values.counterparty,
                  description: values.description,
                  notes: values.notes ? [values.notes] : [],
                  ...(values.external_ref
                    ? { external_ref: values.external_ref }
                    : {}),
                },
                ...(values.category === "adjustment"
                  ? {
                      adjustment_deltas: {
                        [values.adjustment_balance === "deposit"
                          ? "deposit_held_minor"
                          : `${values.adjustment_balance}_balance_minor`]:
                          amount_minor *
                          (values.adjustment_direction === "increase" ? 1 : -1),
                      },
                    }
                  : {}),
                ...(values.paid_by ? { paid_by: values.paid_by } : {}),
                ...(values.paid_to ? { paid_to: values.paid_to } : {}),
                ...(values.ticket ? { ticket_id: values.ticket } : {}),
                ...(values.evidence
                  ? {
                      evidence: values.evidence
                        .split(",")
                        .map((id) => ({ chunk_id: id.trim() })),
                    }
                  : {}),
              },
            },
            { onSuccess: onClose },
          );
        } catch (reason) {
          setError(
            reason instanceof Error ? reason : new Error("Invalid transaction"),
          );
        }
      }}
    >
      <div className="form-row">
        <FormSelect
          label="Category"
          options={options(categories)}
          {...input("category")}
        />
        <FormInput
          label="Amount (GBP)"
          inputMode="decimal"
          required
          placeholder="950.00"
          {...input("amount")}
        />
      </div>
      <div className="form-row">
        <FormInput
          label="Effective date"
          type="date"
          required
          {...input("date")}
        />
        <FormSelect
          label="Status"
          options={options(["expected", "pending", "cleared", "reconciled"])}
          {...input("status")}
        />
      </div>
      <FormInput label="Counterparty" required {...input("counterparty")} />
      <FormTextarea label="Description" required {...input("description")} />
      <div className="form-row">
        <FormInput label="External reference" {...input("external_ref")} />
        <FormInput label="Ticket ID (optional)" {...input("ticket")} />
      </div>
      <div className="form-row">
        <FormInput label="Paid by entity ID (optional)" {...input("paid_by")} />
        <FormInput label="Paid to entity ID (optional)" {...input("paid_to")} />
      </div>
      <FormInput
        label="Evidence chunk IDs (comma separated)"
        {...input("evidence")}
      />
      {values.category === "adjustment" && (
        <div className="form-row">
          <FormSelect
            label="Balance to adjust"
            options={options(["tenant", "landlord", "deposit"])}
            {...input("adjustment_balance")}
          />
          <FormSelect
            label="Direction"
            options={options(["increase", "decrease"])}
            {...input("adjustment_direction")}
          />
        </div>
      )}
      <FormTextarea
        label={
          values.category === "adjustment" ? "Reason for adjustment" : "Notes"
        }
        required={values.category === "adjustment"}
        {...input("notes")}
      />
      <p className="caption">
        This records a ledger entry. No money is sent. Entries are corrected by
        reversal.
      </p>
      <State error={error ?? action.error} />
      <div className="actions">
        <Button loading={action.isPending}>Record transaction</Button>
        <Button type="button" variant="ghost" onClick={onClose}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
