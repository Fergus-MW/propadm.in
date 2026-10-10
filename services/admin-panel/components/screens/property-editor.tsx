"use client";
import { useState } from "react";
import { object, type Entity } from "@/lib/api";
import { useAction, useItems } from "@/lib/hooks";
import { editableFields } from "@/lib/property";
import { Section, State } from "../common";
import { Button } from "../ui/Button";
import { FormInput, FormTextarea } from "../ui/Input";
import { RegisteredFields } from "./registered-fields";

export function PropertyEditor({
  entity,
  onClose,
}: {
  entity: Entity;
  onClose: () => void;
}) {
  const registry = useItems("entity-types");
  const schema = object(
    registry.data?.items.find((row) => row.id === "property")?.fields,
  );
  const [values, setValues] = useState(editableFields(entity.fields, {}));
  const [name, setName] = useState(entity.name);
  const [description, setDescription] = useState(entity.description);
  const [reason, setReason] = useState("");
  const action = useAction();
  return (
    <Section title="Edit property">
      <form
        className="form"
        onSubmit={(e) => {
          e.preventDefault();
          action.mutate(
            {
              path: `entities/${encodeURIComponent(entity.id)}`,
              method: "PATCH",
              body: {
                name,
                description,
                fields: editableFields(values, schema),
                version: entity.version,
                reason,
              },
            },
            { onSuccess: onClose },
          );
        }}
      >
        <FormInput
          label="Property name"
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
        <FormInput
          label="Reason for change"
          required
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
        <p className="caption">
          Balances are calculated from recorded transactions. Saving checks
          version {entity.version}.
        </p>
        <State error={action.error} />
        <div className="actions">
          <Button disabled={!registry.data} loading={action.isPending}>
            Save property
          </Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </form>
    </Section>
  );
}
