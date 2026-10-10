"use client";
import { object, str } from "@/lib/api";
import { editableFields, options } from "@/lib/property";
import { Button } from "../ui/Button";
import { FormInput, FormSelect, FormTextarea } from "../ui/Input";

/** Controls follow the fixed registry while keeping calculated fields out of edits. */
export function RegisteredFields({
  schema,
  value,
  onChange,
}: {
  schema: Record<string, unknown>;
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
}) {
  const entries = Object.entries(schema).filter(
    ([key, spec]) =>
      !object(spec).read_only &&
      key in editableFields({ [key]: value[key] }, schema),
  );
  const set = (key: string, next: unknown) =>
    onChange({ ...value, [key]: next });
  return (
    <div className="form-row">
      {entries.map(([key, raw]) => {
        const spec = object(raw);
        const type = str(spec.type);
        const title = key.endsWith("_minor")
          ? `${key.slice(0, -6).replaceAll("_", " ")} (pence)`
          : key.replaceAll("_", " ");
        const current = value[key];
        const required = Boolean(spec.required);
        const enums = Array.isArray(spec.enum) ? (spec.enum as string[]) : [];
        if (type === "array<object>" && key === "accreditations") {
          const records = Array.isArray(current) ? current.map(object) : [];
          return (
            <div key={key} className="form col-span-full">
              <h3>Accreditations</h3>
              {records.map((record, index) => (
                <div key={index} className="form-row">
                  <FormSelect
                    label="Scheme"
                    options={options([
                      "Gas Safe",
                      "NICEIC",
                      "NAPIT",
                      "TrustMark",
                      "CSCS",
                      "other",
                    ])}
                    value={String(record.scheme ?? "Gas Safe")}
                    onChange={(e) =>
                      set(
                        key,
                        records.map((item, i) =>
                          i === index
                            ? { ...item, scheme: e.target.value }
                            : item,
                        ),
                      )
                    }
                  />
                  <FormInput
                    label="Registration number"
                    required
                    value={String(record.number ?? "")}
                    onChange={(e) =>
                      set(
                        key,
                        records.map((item, i) =>
                          i === index
                            ? { ...item, number: e.target.value }
                            : item,
                        ),
                      )
                    }
                  />
                  <FormInput
                    label="Expires on"
                    type="date"
                    value={String(record.expires_on ?? "")}
                    onChange={(e) =>
                      set(
                        key,
                        records.map((item, i) =>
                          i === index
                            ? { ...item, expires_on: e.target.value || null }
                            : item,
                        ),
                      )
                    }
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() =>
                      set(
                        key,
                        records.filter((_, i) => i !== index),
                      )
                    }
                  >
                    Remove accreditation
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="ghost"
                onClick={() =>
                  set(key, [
                    ...records,
                    { scheme: "Gas Safe", number: "", expires_on: null },
                  ])
                }
              >
                Add accreditation
              </Button>
            </div>
          );
        }
        if (type.includes("array") && enums.length)
          return (
            <FormSelect
              key={key}
              label={`${title} (select all that apply)`}
              multiple
              className="h-40"
              required={required}
              options={options(enums)}
              value={Array.isArray(current) ? (current as string[]) : []}
              onChange={(e) =>
                set(
                  key,
                  Array.from(
                    e.target.selectedOptions,
                    (option) => option.value,
                  ),
                )
              }
            />
          );
        if (type.includes("array"))
          return (
            <FormTextarea
              key={key}
              label={`${title} (one per line)`}
              value={Array.isArray(current) ? current.join("\n") : ""}
              required={required}
              onChange={(e) =>
                set(
                  key,
                  e.target.value
                    .split("\n")
                    .map((value) => value.trim())
                    .filter(Boolean),
                )
              }
            />
          );
        if (enums.length)
          return (
            <FormSelect
              key={key}
              label={title}
              value={String(current ?? "")}
              required={required}
              options={[
                ...(!required ? [{ value: "", label: "Not specified" }] : []),
                ...options(enums),
              ]}
              onChange={(e) =>
                set(
                  key,
                  e.target.value || (type.startsWith("option") ? null : ""),
                )
              }
            />
          );
        if (type.includes("bool"))
          return (
            <FormSelect
              key={key}
              label={title}
              value={String(current ?? false)}
              options={[
                { value: "false", label: "No" },
                { value: "true", label: "Yes" },
              ]}
              onChange={(e) => set(key, e.target.value === "true")}
            />
          );
        if (type.includes("text"))
          return (
            <FormTextarea
              key={key}
              label={title}
              required={required}
              value={String(current ?? "")}
              onChange={(e) => set(key, e.target.value)}
            />
          );
        const numeric = /int|decimal|float/.test(type);
        return (
          <FormInput
            key={key}
            label={title}
            required={required}
            type={numeric ? "number" : type.includes("date") ? "date" : "text"}
            min={
              numeric && typeof spec.minimum === "number"
                ? spec.minimum
                : undefined
            }
            max={
              numeric && typeof spec.maximum === "number"
                ? spec.maximum
                : undefined
            }
            step={type.includes("int") ? "1" : numeric ? "any" : undefined}
            value={String(current ?? "")}
            onChange={(e) =>
              set(
                key,
                numeric
                  ? e.target.value === ""
                    ? null
                    : Number(e.target.value)
                  : e.target.value || (type.startsWith("option") ? null : ""),
              )
            }
          />
        );
      })}
    </div>
  );
}
