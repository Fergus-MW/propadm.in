"use client";
import { FormInput, FormSelect, FormTextarea } from "./ui/Input";
import { object, type RecordData } from "@/lib/api";
export function RuleParameters({
  kind,
  value,
  onChange,
  types,
  source,
  target,
}: {
  kind: string;
  value: string;
  onChange: (value: string) => void;
  types: RecordData[];
  source: string;
  target: string;
}) {
  let params: Record<string, unknown>;
  try {
    params = object(JSON.parse(value));
  } catch {
    params = {};
  }
  const update = (key: string, next: string | number) =>
    onChange(JSON.stringify({ ...params, [key]: next }, null, 2));
  const fields = (type: string) => [
    { value: "", label: "Choose field" },
    ...[
      "name",
      "description",
      "email_domain",
      ...Object.keys(object(types.find((row) => row.id === type)?.fields)),
    ]
      .filter((field, i, list) => list.indexOf(field) === i)
      .map((field) => ({ value: field, label: field.replaceAll("_", " ") })),
  ];
  const numeric = (
    key: string,
    label: string,
    fallback: number,
    min: number,
    max: number,
    step = 1,
  ) => (
    <FormInput
      label={label}
      type="number"
      min={min}
      max={max}
      step={step}
      value={Number(params[key] ?? fallback)}
      onChange={(e) => update(key, Number(e.target.value))}
    />
  );
  return (
    <div className="form">
      {(kind === "field_match" || kind === "field_overlap") && (
        <div className="form-row">
          <FormSelect
            label="Source field"
            options={fields(source)}
            value={String(params.source_field ?? "")}
            onChange={(e) => update("source_field", e.target.value)}
          />
          <FormSelect
            label="Target field"
            options={fields(target)}
            value={String(params.target_field ?? "")}
            onChange={(e) => update("target_field", e.target.value)}
          />
        </div>
      )}
      {kind === "expression" && (
        <FormTextarea
          label="Expression"
          className="mono"
          placeholder="$a.fields.region = $b.fields.region"
          value={String(params.expression ?? "")}
          onChange={(e) => update("expression", e.target.value)}
        />
      )}
      {(kind === "co_occurrence" || kind === "llm_judge") && (
        <div className="form-row">
          {numeric(
            "min_documents",
            "Minimum shared documents",
            kind === "llm_judge" ? 1 : 3,
            1,
            1000,
          )}
          {numeric("window_days", "Lookback (days)", 90, 1, 3650)}
        </div>
      )}
      {(kind === "similarity" || kind === "llm_judge") && (
        <div className="form-row">
          {numeric("threshold", "Minimum score", 0.85, 0, 1, 0.01)}
          {kind === "similarity" &&
            numeric("top_k", "Neighbours per entity", 5, 1, 100)}
        </div>
      )}
      {kind === "similarity" && (
        <FormInput
          label="Embedding field"
          value={String(params.field ?? "description")}
          onChange={(e) => update("field", e.target.value)}
        />
      )}
      {kind === "llm_judge" && (
        <p className="caption">
          Adjudication uses shared source evidence and the saved rule
          instruction. Configure an LLM provider before recomputing.
        </p>
      )}
      <details>
        <summary className="draw-underline cursor-pointer caption">
          Advanced parameters
        </summary>
        <FormTextarea
          label="Parameters (JSON)"
          className="mono mt-4"
          rows={8}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </details>
    </div>
  );
}
