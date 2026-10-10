"use client";
import Link from "next/link";
import { useState } from "react";
import { Undo2 } from "lucide-react";
import {
  Header,
  State,
  Section,
  Status,
  Records,
  Confirm,
  Json,
} from "../common";
import { Button } from "../ui/Button";
import { object, str, time, type RecordData } from "@/lib/api";
import { useAction, useData, useItems } from "@/lib/hooks";
export function Actions() {
  const data = useItems("actions");
  const [undo, setUndo] = useState<RecordData | null>(null);
  const action = useAction();
  return (
    <>
      <Header title="Change log" />
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
              key: "reason",
              title: "Change",
              render: (row) => (
                <div className="max-w-lg whitespace-normal">
                  <p>{str(row.reason ?? row.tool ?? row.kind)}</p>
                  <span className="caption">{str(row.actor)}</span>
                </div>
              ),
            },
            {
              key: "status",
              title: "Status",
              render: (row) => <Status value={row.status ?? "recorded"} />,
            },
            {
              key: "created_at",
              title: "When",
              render: (row) => time(row.created_at),
            },
            {
              key: "undo",
              title: "",
              render: (row) =>
                row.reversible && Boolean(row.before) && !row.undone ? (
                  <Button variant="ghost" onClick={() => setUndo(row)}>
                    <Undo2 size={14} />
                    Undo
                  </Button>
                ) : null,
            },
          ]}
        />
      )}{" "}
      {undo && (
        <Confirm
          title="Undo this change?"
          pending={action.isPending}
          onClose={() => setUndo(null)}
          onConfirm={() =>
            action.mutate(
              { path: `actions/${encodeURIComponent(undo.id)}/undo`, body: {} },
              { onSuccess: () => setUndo(null) },
            )
          }
        >
          The previous value is restored if the record has not changed since
          this action.
          <State error={action.error} />
        </Confirm>
      )}
    </>
  );
}
export function Communications({
  email = false,
  id,
}: {
  email?: boolean;
  id?: string;
}) {
  const list = useItems(email ? "emails" : "calls");
  const detail = useData<RecordData>(
    `calls/${encodeURIComponent(id ?? "")}`,
    Boolean(id && !email),
  );
  if (id && !email) {
    if (!detail.data)
      return (
        <State
          pending={detail.isPending}
          error={detail.error}
          retry={() => void detail.refetch()}
        />
      );
    const call = { ...detail.data, ...object(detail.data.fields) };
    return (
      <>
        <Header title="Call">
          <Link className="draw-underline" href="/calls">
            All calls
          </Link>
          <Link
            className="draw-underline"
            href={`/entities/${encodeURIComponent(id)}`}
          >
            Open entity
          </Link>
        </Header>
        <div className="actions caption">
          <Status value={call.status} />
          <span>{time(call.created_at)}</span>
          <span>{str(call.direction)}</span>
        </div>
        <Section title="Objective">
          <p>{str(call.objective)}</p>
        </Section>
        <Section title="Transcript">
          {typeof call.transcript_text === "string" ? (
            <article className="source-text">{call.transcript_text}</article>
          ) : (
            <Json value={call.transcript ?? []} />
          )}
        </Section>
        <Section title="Outcome">
          <p>{str(call.outcome ?? call.summary)}</p>
        </Section>
        {call.document_id ? (
          <Link
            className="draw-underline"
            href={`/documents/${encodeURIComponent(str(call.document_id))}`}
          >
            Open source evidence
          </Link>
        ) : null}
      </>
    );
  }
  return (
    <>
      <Header title={email ? "Emails" : "Calls"} />
      <State
        pending={list.isPending}
        error={list.error}
        retry={() => void list.refetch()}
      />
      {list.data && (
        <Records
          items={list.data.items.map((row) => ({
            ...row,
            ...object(row.fields),
          }))}
          columns={[
            {
              key: "subject",
              title: email ? "Subject" : "Objective",
              render: (row) =>
                email ? (
                  <details>
                    <summary className="draw-underline cursor-pointer">
                      {str(row.subject ?? row.name)}
                    </summary>
                    <article className="source-text max-w-lg">
                      {str(row.body ?? row.body_text ?? row.description)}
                    </article>
                    <Link
                      className="draw-underline"
                      href={`/entities/${encodeURIComponent(row.id)}`}
                    >
                      Open entity and evidence
                    </Link>
                  </details>
                ) : (
                  <Link
                    className="draw-underline"
                    href={`/calls/${encodeURIComponent(row.id)}`}
                  >
                    {str(row.objective ?? row.summary ?? row.name)}
                  </Link>
                ),
            },
            {
              key: "to",
              title: "Contact",
              render: (row) => str(row.to ?? row.to_number),
            },
            {
              key: "status",
              title: "Status",
              render: (row) => <Status value={row.status ?? "imported"} />,
            },
            {
              key: "created_at",
              title: "When",
              render: (row) =>
                time(row.started_at ?? row.received_at ?? row.created_at),
            },
          ]}
        />
      )}
    </>
  );
}
