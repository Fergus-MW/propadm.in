"use client";
import { useState } from "react";
import { useAction } from "@/lib/hooks";
import type { PortalData } from "@/lib/portal";
import { FormInput, FormSelect, FormTextarea } from "../ui/Input";
import { Button } from "../ui/Button";
import { State } from "../common";

export function AvailabilityEditor({ data }: { data: PortalData }) {
  const [kind, setKind] = useState("prospect");
  const [id, setId] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [evidence, setEvidence] = useState("");
  const [budget, setBudget] = useState(1800);
  const [occupied, setOccupied] = useState(true);
  const [consent, setConsent] = useState(false);
  const [compliant, setCompliant] = useState(false);
  const action = useAction();
  const records = kind === "prospect" ? (data.people ?? []) : data.properties;
  return (
    <form
      className="form"
      onSubmit={(e) => {
        e.preventDefault();
        const window = {
          start: new Date(start).toISOString(),
          end: new Date(end).toISOString(),
          evidence,
        };
        action.mutate({
          path:
            kind === "prospect"
              ? "portal/prospects/availability"
              : `portal/properties/${encodeURIComponent(id)}/viewing-rules`,
          method: "PUT",
          body:
            kind === "prospect"
              ? { person_id: id, budget, ...window }
              : { occupied, consent, compliant, notice_hours: 24, ...window },
        });
      }}
    >
      <FormSelect
        label="Record availability for"
        value={kind}
        onChange={(e) => {
          setKind(e.target.value);
          setId("");
        }}
        options={[
          { value: "prospect", label: "Prospect" },
          { value: "property", label: "Property viewing rules" },
        ]}
      />
      <FormSelect
        label={
          kind === "prospect" ? "Person in the graph" : "Property in the graph"
        }
        required
        value={id}
        onChange={(e) => setId(e.target.value)}
        options={[
          { value: "", label: "Choose a record…" },
          ...records.map((r) => ({ value: r.id, label: r.name })),
        ]}
      />
      <div className="form-row">
        <FormInput
          label="Available from (your timezone)"
          type="datetime-local"
          required
          value={start}
          onChange={(e) => setStart(e.target.value)}
        />
        <FormInput
          label="Available until (your timezone)"
          type="datetime-local"
          required
          min={start}
          value={end}
          onChange={(e) => setEnd(e.target.value)}
        />
      </div>
      {kind === "prospect" ? (
        <FormInput
          label="Monthly budget (£)"
          type="number"
          min={1}
          required
          value={budget}
          onChange={(e) => setBudget(Number(e.target.value))}
        />
      ) : (
        <>
          <label>
            <input
              type="checkbox"
              checked={occupied}
              onChange={(e) => setOccupied(e.target.checked)}
            />{" "}
            Property is occupied
          </label>
          <label>
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />{" "}
            Current tenant consent is recorded
          </label>
          <label>
            <input
              type="checkbox"
              checked={compliant}
              onChange={(e) => setCompliant(e.target.checked)}
            />{" "}
            Required compliance documents have been checked and are valid
          </label>
          <p className="caption">
            Minimum notice: 24 hours. Recording a window replaces the previous
            window.
          </p>
        </>
      )}
      <FormTextarea
        label="Evidence / source of confirmation"
        required
        minLength={3}
        value={evidence}
        onChange={(e) => setEvidence(e.target.value)}
      />
      <Button loading={action.isPending} type="submit">
        Save verified availability
      </Button>
      <State error={action.error} />
      {action.isSuccess && <p role="status">Availability saved.</p>}
    </form>
  );
}
