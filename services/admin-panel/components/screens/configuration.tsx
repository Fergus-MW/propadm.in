"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Plus } from "lucide-react";
import {
  Header,
  State,
  Section,
  Status,
  Records,
  Json,
  Confirm,
} from "../common";
import { Button } from "../ui/Button";
import { FormInput, FormSelect, FormTextarea } from "../ui/Input";
import { object, str, type RecordData } from "@/lib/api";
import { useAction, useData, useItems } from "@/lib/hooks";
import { RuleParameters } from "../rule-parameters";
const kinds = [
  "field_match",
  "field_overlap",
  "expression",
  "co_occurrence",
  "similarity",
  "llm_judge",
];
export function Rules({ id }: { id?: string }) {
  const list = useItems("edge-rules");
  const [draft, setDraft] = useState<RecordData | null>(null);
  const [prompt, setPrompt] = useState("");
  const compile = useAction();
  const existing = list.data?.items.find((rule) => rule.id === id);
  if (id === "new" || existing || draft)
    return (
      <RuleEditor
        key={draft ? JSON.stringify(draft) : id}
        rule={
          draft ??
          existing ?? {
            id: "",
            name: "",
            kind: "field_match",
            source_type: "person",
            target_type: "company",
            relation: "works_at",
            enabled: false,
            params: {},
            version: 0,
          }
        }
        onClose={() => setDraft(null)}
      />
    );
  return (
    <>
      <Header title="Edge rules">
        <Button asChild variant="ghost">
          <Link href="/rules/new">
            <Plus size={16} />
            Create rule
          </Link>
        </Button>
      </Header>
      <form
        className="form mb-8"
        onSubmit={(e) => {
          e.preventDefault();
          compile.mutate(
            { path: "edge-rules/compile", body: { prompt } },
            { onSuccess: (result) => setDraft({ ...result, id: "", prompt }) },
          );
        }}
      >
        <FormInput
          label="Describe a rule"
          placeholder="Link people to companies whose domain matches their email"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          required
        />
        <div className="actions">
          <Button loading={compile.isPending}>Compile rule</Button>
          <span className="caption">
            Review the specification before saving.
          </span>
        </div>
        <State error={compile.error} />
      </form>
      <State
        pending={list.isPending}
        error={list.error}
        retry={() => void list.refetch()}
      />
      {list.data && (
        <Records
          items={list.data.items}
          columns={[
            {
              key: "name",
              title: "Rule",
              render: (row) => (
                <Link
                  className="draw-underline font-medium"
                  href={`/rules/${encodeURIComponent(row.id)}`}
                >
                  {str(row.name)}
                </Link>
              ),
            },
            { key: "kind", title: "Kind" },
            { key: "relation", title: "Relation" },
            {
              key: "enabled",
              title: "Status",
              render: (row) => (
                <Status value={row.enabled ? "active" : "disabled"} />
              ),
            },
            { key: "version", title: "Version" },
          ]}
        />
      )}
    </>
  );
}
function RuleEditor({
  rule,
  onClose,
}: {
  rule: RecordData;
  onClose: () => void;
}) {
  const router = useRouter();
  const [name, setName] = useState(str(rule.name));
  const [kind, setKind] = useState(str(rule.kind));
  const [source, setSource] = useState(str(rule.source_type));
  const [target, setTarget] = useState(str(rule.target_type));
  const [relation, setRelation] = useState(str(rule.relation));
  const [enabled, setEnabled] = useState(Boolean(rule.enabled));
  const [params, setParams] = useState(
    JSON.stringify(rule.params ?? {}, null, 2),
  );
  const [error, setError] = useState<Error | null>(null);
  const [confirm, setConfirm] = useState(false);
  const types = useItems("entity-types");
  const action = useAction();
  const preview = useAction<{ count: number; samples: RecordData[] }>();
  const options = (types.data?.items ?? []).map((type) => ({
    value: type.id,
    label: str(type.name),
  }));
  return (
    <>
      <Header title={rule.id ? str(rule.name) : "New edge rule"}>
        <Link className="draw-underline" href="/rules" onClick={onClose}>
          All rules
        </Link>
      </Header>
      <div className="two-columns">
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            try {
              const parsed = JSON.parse(params);
              if (
                !parsed ||
                Array.isArray(parsed) ||
                typeof parsed !== "object"
              )
                throw new Error("Parameters must be a JSON object");
              action.mutate(
                {
                  path: rule.id
                    ? `edge-rules/${encodeURIComponent(rule.id)}`
                    : "edge-rules",
                  method: rule.id ? "PATCH" : "POST",
                  body: {
                    ...(rule.id ? { id: rule.id, version: rule.version } : {}),
                    name,
                    kind,
                    source_type: source,
                    target_type: target,
                    relation,
                    params: parsed,
                    enabled,
                    prompt: rule.prompt ?? "",
                  },
                },
                {
                  onSuccess: (result) =>
                    router.push(`/rules/${encodeURIComponent(result.id)}`),
                },
              );
            } catch (reason) {
              setError(
                reason instanceof Error
                  ? reason
                  : new Error("Invalid parameters"),
              );
            }
          }}
        >
          <FormInput
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          <FormSelect
            label="Criterion kind"
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            options={kinds.map((value) => ({
              value,
              label: value.replaceAll("_", " "),
            }))}
          />
          <div className="form-row">
            <FormSelect
              label="Source type"
              options={options}
              value={source}
              onChange={(e) => setSource(e.target.value)}
            />
            <FormSelect
              label="Target type"
              options={options}
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            />
          </div>
          <FormInput
            label="Relation"
            value={relation}
            onChange={(e) => setRelation(e.target.value)}
            required
            pattern="[a-z][a-z0-9_]*"
          />
          <RuleParameters
            kind={kind}
            value={params}
            onChange={setParams}
            types={types.data?.items ?? []}
            source={source}
            target={target}
          />
          <label className="flex items-center gap-2 caption">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
            />
            Enable rule
          </label>
          <State error={error ?? action.error} />
          <Button loading={action.isPending}>Save rule</Button>
        </form>
        <div>
          {rule.prompt ? (
            <Section title="Original instruction">
              <p>{str(rule.prompt)}</p>
            </Section>
          ) : null}
          <Section title="Compiled query">
            <Json value={rule.compiled_query ?? "Save to compile"} />
          </Section>
          <Section title="Preview">
            <div className="actions">
              <Button
                variant="ghost"
                disabled={!rule.id}
                loading={preview.isPending}
                onClick={() =>
                  preview.mutate({
                    path: `edge-rules/${encodeURIComponent(rule.id)}/preview`,
                    body: {},
                  })
                }
              >
                Preview saved rule
              </Button>
              <Button
                variant="ghost"
                disabled={!rule.id}
                onClick={() => setConfirm(true)}
              >
                Recompute edges
              </Button>
            </div>
            <State error={preview.error} />
            {preview.data && (
              <>
                <p className="caption my-4">
                  {preview.data.count} matching pairs
                </p>
                <Json value={preview.data.samples} />
              </>
            )}
          </Section>
        </div>
      </div>
      {confirm && (
        <Confirm
          title="Recompute this rule?"
          pending={action.isPending}
          onClose={() => setConfirm(false)}
          onConfirm={() =>
            action.mutate(
              {
                path: `edge-rules/${encodeURIComponent(rule.id)}/recompute`,
                body: {},
              },
              { onSuccess: () => setConfirm(false) },
            )
          }
        >
          Generated connections are replaced using the saved rule version.
          Manual connections are preserved.
          <State error={action.error} />
        </Confirm>
      )}
    </>
  );
}
export function Schema() {
  const list = useItems("entity-types");
  const [selected, setSelected] = useState<RecordData | null>(null);
  return (
    <>
      <Header title="Entity types">
        <Button
          variant={selected ? "ghost" : "default"}
          onClick={() =>
            setSelected({
              id: "",
              name: "",
              fields: {},
              version: 0,
              primary: true,
            })
          }
        >
          <Plus size={16} />
          Create type
        </Button>
      </Header>
      <State
        pending={list.isPending}
        error={list.error}
        retry={() => void list.refetch()}
      />
      {list.data && (
        <Records
          items={list.data.items}
          columns={[
            {
              key: "name",
              title: "Type",
              render: (row) => (
                <Button variant="ghost" onClick={() => setSelected(row)}>
                  {str(row.name)}
                </Button>
              ),
            },
            { key: "id", title: "Identifier" },
            {
              key: "primary",
              title: "Ingestion",
              render: (row) => (row.primary ? "Extracted" : "Not extracted"),
            },
            {
              key: "fields",
              title: "Fields",
              render: (row) => Object.keys(object(row.fields)).length,
            },
            { key: "version", title: "Version" },
          ]}
        />
      )}{" "}
      {selected && (
        <SchemaEditor
          key={`${selected.id}-${selected.version}`}
          selected={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}
function SchemaEditor({
  selected,
  onClose,
}: {
  selected: RecordData;
  onClose: () => void;
}) {
  const [id, setId] = useState(selected.id);
  const [name, setName] = useState(str(selected.name));
  const [fields, setFields] = useState(
    JSON.stringify(selected.fields, null, 2),
  );
  const [primary, setPrimary] = useState(Boolean(selected.primary));
  const [error, setError] = useState<Error | null>(null);
  const action = useAction();
  return (
    <Section title={selected.id ? `Edit ${name}` : "New entity type"}>
      <form
        className="form"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          try {
            const parsed = JSON.parse(fields);
            action.mutate(
              {
                path: "entity-types",
                method: selected.id ? "PATCH" : "POST",
                // Spread keeps composite keys and other registry settings intact.
                body: { ...selected, id, name, fields: parsed, primary },
              },
              { onSuccess: onClose },
            );
          } catch {
            setError(new Error("Fields must be valid JSON"));
          }
        }}
      >
        <div className="form-row">
          <FormInput
            label="Identifier"
            disabled={Boolean(selected.id)}
            required
            value={id}
            onChange={(e) => setId(e.target.value)}
            pattern="[a-z][a-z0-9_]*"
          />
          <FormInput
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <label className="flex items-center gap-2 caption">
          <input
            type="checkbox"
            checked={primary}
            onChange={(e) => setPrimary(e.target.checked)}
          />
          Primary entity: ingestion extracts this type from sources
        </label>
        <FormTextarea
          label="Field definitions (JSON)"
          rows={10}
          className="mono"
          value={fields}
          onChange={(e) => setFields(e.target.value)}
        />
        <p className="caption">
          Each field supports type, required, unique_key and embed. Types
          include string, number, boolean and array&lt;string&gt;.
        </p>
        <State error={error ?? action.error} />
        <div className="actions">
          <Button loading={action.isPending}>Save type</Button>
          <Button variant="ghost" type="button" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </form>
    </Section>
  );
}
export function Settings() {
  const data = useData<RecordData>("settings");
  return (
    <>
      <Header title="Settings" />
      <State
        pending={data.isPending}
        error={data.error}
        retry={() => void data.refetch()}
      />
      {data.data && (
        <>
          <Section title="Provider configuration">
            <Json value={data.data} />
          </Section>
          <Section title="Runtime boundaries">
            <p>
              This build runs the admin panel, API and ingestion services.
              Provider configuration and local extraction capabilities are
              reported above.
            </p>
          </Section>
        </>
      )}
    </>
  );
}
