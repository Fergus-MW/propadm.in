"use client";
import Link from "next/link";
import { useState } from "react";
import { ArrowUpRight, Mail } from "lucide-react";
import { useAction } from "@/lib/hooks";
import {
  type PortalData,
  type PortalItem,
  needsHuman,
  portalHref,
  when,
  money,
} from "@/lib/portal";
import { Header, State } from "../common";
import { FormInput, FormTextarea } from "../ui/Input";
import { Button } from "../ui/Button";
import { EmptyState } from "../library/EmptyState";
import { Flags, Takeover } from "./shared";

export function Inbox({ data, id }: { data: PortalData; id?: string }) {
  const [filter, setFilter] = useState("Needs you");
  const [search, setSearch] = useState("");
  const selected = data.items.find((i) => i.id === id);
  const items = data.items.filter(
    (i) =>
      (filter === "All" ||
        (filter === "Needs you" && needsHuman(i)) ||
        filter === i.role ||
        (filter === "AI handling" && i.autonomy === 3)) &&
      `${i.title} ${i.property} ${i.person}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const active = selected ?? items[0];
  return (
    <>
      <Header title="Inbox" />
      <div className="portal-inbox-filters">
        <FormInput
          id="portal-search"
          label="Search conversations · ⌘K"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="portal-tabs">
          {[
            "Needs you",
            "All",
            "Tenant",
            "Landlord",
            "Contractor",
            "AI handling",
          ].map((tab) => (
            <button
              key={tab}
              aria-pressed={filter === tab}
              onClick={() => setFilter(tab)}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>
      <div className="portal-inbox">
        <aside aria-label="Conversations">
          {items.length ? (
            items.map((item) => (
              <Link
                className={`portal-thread-row ${item.id === active?.id ? "selected" : ""}`}
                key={item.id}
                href={portalHref("inbox", data.demo, item.id)}
              >
                <div className="actions">
                  <strong>{item.person}</strong>
                  <span className="caption">{item.role}</span>
                </div>
                <h3>{item.title}</h3>
                <p className="caption">{item.property}</p>
                <Flags flags={item.flags} />
              </Link>
            ))
          ) : (
            <EmptyState message="No conversations match." />
          )}
        </aside>
        {active ? (
          <>
            <Thread key={active.id} item={active} demo={data.demo} />
            <aside className="portal-context">
              <h3>From the knowledge graph</h3>
              <dl>
                <dt>Property</dt>
                <dd>{active.property}</dd>
                <dt>Contact</dt>
                <dd>
                  {active.person} · {active.role}
                </dd>
                <dt>Repair estimate</dt>
                <dd>{money(active.estimate)}</dd>
                <dt>Spend limit</dt>
                <dd>{money(active.spend_limit)}</dd>
              </dl>
              <h3>Why this needs attention</h3>
              <Flags flags={active.flags} />
              <p>
                {active.handover ||
                  "Open the source record to review the available evidence."}
              </p>
              {active.related_items?.map(related => (
                <p key={related.id}><Link className="draw-underline" href={portalHref("inbox", data.demo, related.id)}>
                  Related: {related.title} ↗
                </Link></p>
              ))}
              <h3>Facts used</h3>
              {active.facts.length ? (
                active.facts.map((f) => (
                  <Link
                    key={f.id}
                    href={`/entities/${encodeURIComponent(f.id)}`}
                    className="draw-underline"
                  >
                    {f.label} ↗
                  </Link>
                ))
              ) : (
                <p className="caption">
                  No linked source records.
                </p>
              )}
              <Link
                className="draw-underline"
                href={portalHref("maintenance", data.demo, active.id)}
              >
                Open repair progress <ArrowUpRight size={14} />
              </Link>
            </aside>
          </>
        ) : (
          <EmptyState message="Select a conversation to begin." />
        )}
      </div>
    </>
  );
}
function Highlight({ text }: { text: string }) {
  return (
    <>
      {text
        .split(
          /(eggy smell|gas smell|burning smell|change the locks|water near electrics)/gi,
        )
        .map((part, i) => (i % 2 ? <mark key={i}>{part}</mark> : part))}
    </>
  );
}
function Thread({ item, demo }: { item: PortalItem; demo: boolean }) {
  const [deliveryEvidence, setDeliveryEvidence] = useState("");
  const [editedDraft, setDraft] = useState("");
  const [editedVersion, setEditedVersion] = useState<number | null>(null);
  const draft = editedVersion === null ? item.draft : editedDraft;
  const draftVersion = editedVersion ?? item.version;
  const action = useAction();
  const command = (name: string) =>
    action.mutate(
      {
        path: `portal/items/${encodeURIComponent(item.id)}/command?demo=${demo}`,
        body: { version: draftVersion, action: name, text: draft },
      },
      { onSuccess: () => setEditedVersion(null) },
    );
  return (
    <section className="portal-thread">
      <div className="portal-thread-header">
        <div>
          <h2>{item.title}</h2>
          <p className="caption">
            {item.autonomy === 0
              ? "You’re handling this"
              : ["Paused", "Tell me", "Draft for me", "Autopilot"][
                  item.autonomy
                ]}
          </p>
        </div>
        <Takeover item={item} demo={demo} />
      </div>
      <div className="portal-messages">
        {item.messages.map((message) => (
          <article className="portal-message" key={message.id}>
            <div className="actions">
              <Mail size={14} />
              <strong>{message.author}</strong>
              <span className="caption">
                {message.channel} · {when(message.at)}
              </span>
            </div>
            {message.recipient && <p className="caption">To: {message.recipient}</p>}
            {message.subject && <h4>{message.subject}</h4>}
            {message.attachments?.map(name => <p className="caption" key={name}>Attachment referenced: {name}</p>)}
            <p>
              <Highlight text={message.text} />
            </p>
          </article>
        ))}
        {item.timeline.map((event, i) => (
          <p className="portal-system-event caption" key={i}>
            {event.actor} · {event.action} {event.detail && `— ${event.detail}`}
          </p>
        ))}
      </div>
      <div className="portal-draft">
        {item.delivery_status && (
          <div className="form">
            <p>
              Previous delivery: {item.delivery_status}. Check the email log
              before sending another reply.
            </p>
            <Link className="draw-underline" href="/emails">
              Open email log ↗
            </Link>
            <FormTextarea
              label="Delivery verification evidence"
              value={deliveryEvidence}
              onChange={(e) => setDeliveryEvidence(e.target.value)}
            />
            <div className="actions">
              {[true, false].map((sent) => (
                <Button
                  key={String(sent)}
                  variant="ghost"
                  loading={action.isPending}
                  disabled={deliveryEvidence.trim().length < 3}
                  onClick={() =>
                    action.mutate({
                      path: `portal/items/${encodeURIComponent(item.id)}/delivery-review`,
                      body: { sent, evidence: deliveryEvidence },
                    })
                  }
                >
                  {sent
                    ? "I verified it was sent"
                    : "I verified it was not sent"}
                </Button>
              ))}
            </div>
          </div>
        )}
        <FormTextarea
          label={item.draft ? "Draft · review before sending" : "Write a reply"}
          rows={6}
          value={draft}
          onChange={(e) => {
            if (editedVersion === null) setEditedVersion(item.version);
            setDraft(e.target.value);
          }}
        />
        {editedVersion !== null && editedVersion !== item.version && (
          <div className="portal-notice">
            <p>
              The record changed while you were editing. Review the conversation
              before saving or sending.
            </p>
            <Button
              variant="ghost"
              onClick={() => setEditedVersion(item.version)}
            >
              I reviewed the changes; keep my draft
            </Button>
          </div>
        )}
        <details>
          <summary>Why this reply · {item.confidence} confidence</summary>
          {item.reasons.map((reason) => (
            <p key={reason}>{reason}</p>
          ))}
        </details>
        <div className="actions">
          <Button
            loading={action.isPending}
            disabled={!draft.trim() || !!item.delivery_status}
            onClick={() =>
              action.mutate(
                {
                  path: `portal/items/${encodeURIComponent(item.id)}/send?demo=${demo}`,
                  body: {
                    version: draftVersion,
                    text: draft,
                    request_id: crypto.randomUUID(),
                  },
                },
                {
                  onSuccess: () => {
                    setDraft("");
                    setEditedVersion(null);
                  },
                },
              )
            }
          >
            {demo ? "Save reply" : "Approve & send email"}
          </Button>
          <Button
            variant="ghost"
            loading={action.isPending}
            onClick={() => command("draft")}
          >
            Save draft
          </Button>
          <Button
            variant="ghost"
            disabled={!draft}
            onClick={() => {
              setDraft("");
              setEditedVersion(null);
              action.mutate({
                path: `portal/items/${encodeURIComponent(item.id)}/command?demo=${demo}`,
                body: { version: item.version, action: "draft", text: "" },
              });
            }}
          >
            Discard draft
          </Button>
        </div>
        <State error={action.error} />
        {action.isSuccess && (
          <p className="caption" role="status">
            Saved to the record.
          </p>
        )}
      </div>
    </section>
  );
}
