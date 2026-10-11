"use client";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowUpRight, GitMerge, Plus } from "lucide-react";
import {
  Header,
  Section,
  State,
  Status,
  Records,
  Confirm,
  Json,
} from "../common";
import { Button } from "../ui/Button";
import { FormInput, FormSelect, FormTextarea } from "../ui/Input";
import { RowMenu } from "../library/RowMenu";
import {
  object,
  rows,
  str,
  time,
  type Entity,
  type RecordData,
} from "@/lib/api";
import { useAction, useData, useItems } from "@/lib/hooks";
import { editConflict, editableFields, entityHref } from "@/lib/property";
import { TicketCompletion, TicketCompletionEditor } from "./ticket-completion";
export function Entities({ tickets = false }: { tickets?: boolean }) {
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [create, setCreate] = useState(false);
  const data = useItems(
    `entities?${new URLSearchParams({ ...(tickets ? { type: "ticket" } : type ? { type } : {}), ...(q ? { q } : {}) })}`,
  );
  const types = useItems("entity-types");
  return (
    <>
      <Header title={tickets ? "Tickets" : "Entities"}>
        <Button
          variant={create ? "ghost" : "default"}
          disabled={type === "transaction"}
          onClick={() => setCreate(!create)}
        >
          <Plus size={16} />
          Create {tickets ? "ticket" : "entity"}
        </Button>
      </Header>
      {create && (
        <EntityCreate
          type={tickets ? "ticket" : type || "person"}
          types={types.data?.items ?? []}
          onClose={() => setCreate(false)}
        />
      )}
      <div className="filter-row">
        <FormInput
          label="Find records"
          placeholder="Name, address or identifier"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        {!tickets && (
          <FormSelect
            label="Entity type"
            value={type}
            onChange={(e) => setType(e.target.value)}
            options={[
              { value: "", label: "All types" },
              ...(types.data?.items ?? []).map((t) => ({
                value: t.id,
                label: str(t.name),
              })),
            ]}
          />
        )}
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
              title: "Name",
              key: "name",
              render: (row) => (
                <Link
                  className="link draw-underline font-medium"
                  href={entityHref(row)}
                >
                  {str(row.name)}
                </Link>
              ),
            },
            {
              title: tickets ? "Status" : "Type",
              key: "type",
              render: (row) =>
                tickets ? (
                  <Status value={object(row.fields).status} />
                ) : (
                  str(row.type)
                ),
            },
            {
              title: tickets ? "Priority" : "Updated",
              key: "updated_at",
              render: (row) =>
                tickets
                  ? str(object(row.fields).priority)
                  : time(row.updated_at),
            },
            {
              title: "",
              key: "actions",
              render: (row) => (
                <RowMenu
                  label={str(row.name)}
                  items={[
                    {
                      label: "Explore connections",
                      href: `/graph?entity=${encodeURIComponent(row.id)}`,
                    },
                  ]}
                />
              ),
            },
          ]}
        />
      )}
    </>
  );
}
function EntityCreate({
  type,
  types,
  onClose,
}: {
  type: string;
  types: RecordData[];
  onClose: () => void;
}) {
  const [name, setName] = useState("");
  const [kind, setKind] = useState(type);
  const [description, setDescription] = useState("");
  const action = useAction();
  return (
    <Section title="New entity">
      <form
        className="form mb-8"
        onSubmit={(e) => {
          e.preventDefault();
          action.mutate(
            {
              path: "entities",
              body: { name, type: kind, description, fields: {} },
            },
            { onSuccess: onClose },
          );
        }}
      >
        <div className="form-row">
          <FormInput
            label="Name"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <FormSelect
            label="Type"
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            options={types
              .filter((t) => t.id !== "transaction")
              .map((t) => ({ value: t.id, label: str(t.name) }))}
          />
        </div>
        <FormTextarea
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <State error={action.error} />
        <div className="actions">
          <Button type="submit" loading={action.isPending}>
            Create entity
          </Button>
          <Button variant="ghost" type="button" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </form>
    </Section>
  );
}
export function EntityDetail({ id }: { id: string }) {
  const data = useData<Entity>(`entities/${encodeURIComponent(id)}`);
  const router = useRouter();
  const action = useAction<Entity>();
  const [edit, setEdit] = useState(false);
  const [draft, setDraft] = useState(0);
  const [merge, setMerge] = useState(false);
  const [target, setTarget] = useState("");
  const [reason, setReason] = useState("");
  const all = useItems("entities");
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
        <Link
          className="draw-underline"
          href={`/graph?entity=${encodeURIComponent(id)}`}
        >
          Explore connections <ArrowUpRight className="inline" size={14} />
        </Link>
        {entity.type !== "transaction" && (
          <Button variant="ghost" onClick={() => setMerge(true)}>
            <GitMerge size={16} />
            Merge
          </Button>
        )}
        {entity.type !== "transaction" && (
          <Button
            variant={edit ? "ghost" : "default"}
            onClick={() => setEdit(!edit)}
          >
            {edit ? "Close editor" : "Edit entity"}
          </Button>
        )}
      </Header>
      <div className="actions caption">
        <span className="mono">{entity.id}</span>
        <span>{entity.type}</span>
        <span>Version {entity.version}</span>
      </div>
      <p className="lead">{entity.description || "No description yet."}</p>
      {edit && (
        <EntityEditor
          key={draft}
          entity={entity}
          onReload={() => setDraft((n) => n + 1)}
          onClose={() => setEdit(false)}
        />
      )}
      <State error={action.error} />
      {entity.type === "ticket" && <TicketCompletion entity={entity} />}
      <div className="two-columns">
        <div>
          <Section title="Details">
            <dl className="fact-grid">
              {Object.entries(entity.fields ?? {}).filter(([key]) =>
                entity.type !== "ticket" || !["final_answer", "reasoning"].includes(key),
              ).map(([key, value]) => (
                <div className="fact" key={key}>
                  <dt>{key.replaceAll("_", " ")}</dt>
                  <dd>{str(value)}</dd>
                </div>
              ))}
            </dl>
          </Section>
          <Section title="Connections">
            <Records
              items={rows(entity.edges)}
              columns={[
                { key: "relation", title: "Relation" },
                {
                  key: "target",
                  title: "Entity",
                  render: (edge) => {
                    const other =
                      edge.source === id ? edge.target : edge.source;
                    return (
                      <Link
                        className="draw-underline"
                        href={`/entities/${encodeURIComponent(str(other))}`}
                      >
                        {str(other)}
                      </Link>
                    );
                  },
                },
                {
                  key: "rule",
                  title: "Origin",
                  render: (row) => (row.rule ? str(row.rule) : "Manual"),
                },
              ]}
            />
          </Section>
        </div>
        <div>
          <Section title="Evidence">
            <Evidence evidence={rows(entity.evidence)} />
          </Section>
          <Section title="Activity">
            <Records
              items={rows(entity.timeline)}
              columns={[
                {
                  key: "reason",
                  title: "Change",
                  render: (row) => (
                    <span className="whitespace-normal">
                      {str(row.reason ?? row.kind)}
                    </span>
                  ),
                },
                { key: "actor", title: "Actor" },
                {
                  key: "created_at",
                  title: "When",
                  render: (row) => time(row.created_at),
                },
              ]}
            />
          </Section>
        </div>
      </div>
      {merge && (
        <Confirm
          title={`Merge ${entity.name}?`}
          disabled={!target || !reason.trim()}
          pending={action.isPending}
          onClose={() => setMerge(false)}
          onConfirm={() =>
            action.mutate(
              {
                path: `entities/${encodeURIComponent(id)}/merge`,
                body: { target_id: target, version: entity.version, reason },
              },
              {
                onSuccess: () => {
                  setMerge(false);
                  router.push(`/entities/${encodeURIComponent(target)}`);
                },
              },
            )
          }
        >
          <span className="block mb-4">
            Evidence and connections move to the target entity. Choose the
            record to keep.
          </span>
          <FormSelect
            label="Target"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            options={[
              { value: "", label: "Select entity" },
              ...(all.data?.items ?? [])
                .filter((row) => row.id !== id && row.type === entity.type)
                .map((row) => ({ value: row.id, label: str(row.name) })),
            ]}
          />
          <div className="mt-4">
            <FormInput
              label="Reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
          <State error={action.error} />
        </Confirm>
      )}
    </>
  );
}
function EntityEditor({
  entity,
  onReload,
  onClose,
}: {
  entity: Entity;
  onReload: () => void;
  onClose: () => void;
}) {
  // Edits stay pinned to the version they started from, so a concurrent save
  // never silently replaces the draft; the API rejects the stale write instead.
  const [base] = useState(entity);
  const conflict = editConflict(base, entity);
  const [name, setName] = useState(entity.name);
  const [description, setDescription] = useState(entity.description);
  const [fields, setFields] = useState(
    JSON.stringify(editableFields(Object.fromEntries(
      Object.entries(entity.fields).filter(([key]) =>
        entity.type !== "ticket" || !["status", "final_answer", "reasoning"].includes(key),
      ),
    ), {}), null, 2),
  );
  const [status, setStatus] = useState(String(entity.fields.status ?? ""));
  const [finalAnswer, setFinalAnswer] = useState(String(entity.fields.final_answer ?? ""));
  const [reasoning, setReasoning] = useState(String(entity.fields.reasoning ?? ""));
  const [reason, setReason] = useState("");
  const [error, setError] = useState<Error | null>(null);
  const action = useAction();
  const types = useItems("entity-types");
  const schema = types.data?.items.find((t) => t.id === entity.type);
  return (
    <Section title="Edit record">
      <form
        className="form"
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          try {
            const parsed = JSON.parse(fields);
            if (!parsed || Array.isArray(parsed) || typeof parsed !== "object")
              throw new Error("Fields must be a JSON object");
            action.mutate(
              {
                path: `entities/${encodeURIComponent(entity.id)}`,
                method: "PATCH",
                body: {
                  name,
                  description,
                  fields: editableFields({ ...parsed, ...(entity.type === "ticket" ? {
                    ...(status ? { status } : {}), final_answer: finalAnswer, reasoning,
                  } : {}) }, object(schema?.fields)),
                  version: base.version,
                  reason,
                },
              },
              { onSuccess: onClose },
            );
          } catch (reason) {
            setError(
              reason instanceof Error ? reason : new Error("Invalid fields"),
            );
          }
        }}
      >
        <FormInput
          label="Name"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <FormTextarea
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        {entity.type === "ticket" && (
          <TicketCompletionEditor
            status={status} finalAnswer={finalAnswer} reasoning={reasoning}
            onStatus={setStatus} onAnswer={setFinalAnswer} onReasoning={setReasoning}
          />
        )}
        <FormTextarea
          label="Typed fields (JSON)"
          rows={8}
          className="mono"
          value={fields}
          onChange={(e) => setFields(e.target.value)}
        />
        {schema && (
          <details>
            <summary className="draw-underline cursor-pointer">
              View field schema
            </summary>
            <Json value={schema.fields} />
          </details>
        )}
        <FormInput
          label="Reason for change"
          required
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
        <State error={error ?? action.error} />
        <div className="actions">
          <Button loading={action.isPending}>Save changes</Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </div>
        {conflict ? (
          <p className="caption" role="alert">
            This record changed to version {conflict.to} while you were
            editing version {conflict.from}. Copy anything you need, then{" "}
            <button type="button" className="draw-underline" onClick={onReload}>
              load the latest version
            </button>
            .
          </p>
        ) : (
          <p className="caption">
            Saving uses version {base.version}. A conflicting edit must be
            reloaded.
          </p>
        )}
      </form>
    </Section>
  );
}
export function Evidence({ evidence }: { evidence: RecordData[] }) {
  if (!evidence.length)
    return <p className="caption">No source evidence attached.</p>;
  return (
    <div>
      {evidence.map((item, index) => {
        const span = item.span
          ? object(item.span)
          : {
              start: item.char_start ?? 0,
              end: item.char_end ?? 0,
              text: item.text,
            };
        const document = str(item.document_id ?? item.document);
        return (
          <div className="result" key={item.id ?? index}>
            <Link
              className="draw-underline"
              href={`/documents/${encodeURIComponent(document)}?start=${Number(span.start ?? 0)}&end=${Number(span.end ?? 0)}#source-highlight`}
            >
              {str(item.filename ?? document)}
            </Link>
            {Boolean(span.text) && <p>“{str(span.text)}”</p>}
            <div className="caption">
              {item.confidence !== undefined &&
                `Confidence ${Math.round(Number(item.confidence) * 100)}% · `}
              {str(item.extractor_version ?? "Source record")}
            </div>
          </div>
        );
      })}
    </div>
  );
}
