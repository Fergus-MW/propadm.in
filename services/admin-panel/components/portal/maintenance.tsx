"use client";
import Link from "next/link";
import { useState } from "react";
import { useAction } from "@/lib/hooks";
import {
  type PortalData,
  type PortalItem,
  isOpen,
  money,
  portalHref,
  progressStages,
  when,
} from "@/lib/portal";
import { Header, State, Section } from "../common";
import { Button } from "../ui/Button";
import { FormInput, FormSelect, FormTextarea } from "../ui/Input";
import { EmptyState } from "../library/EmptyState";
import { EmergencyControls } from "./emergency-controls";
import { ShareControls } from "./share-controls";
import { Flags, ItemLink, ProgressCard, Takeover } from "./shared";
const lanes = [
  "New",
  "Collecting details",
  "Needs approval",
  "Booking",
  "Scheduled",
  "In progress",
  "Checking fix",
  "Reporting",
  "Done",
];
function lane(item: PortalItem) {
  if (item.emergency) return item.stage >= 5 ? "Checking fix" : "In progress";
  return [
    "New",
    "Collecting details",
    "New",
    "Needs approval",
    "Booking",
    "Scheduled",
    "Scheduled",
    "In progress",
    "In progress",
    "Checking fix",
    "Reporting",
    "Done",
  ][item.stage];
}
export function Maintenance({ data, id }: { data: PortalData; id?: string }) {
  const [view, setView] = useState("Board");
  const [search, setSearch] = useState("");
  const selected = data.items.find((i) => i.id === id);
  if (id)
    return selected ? (
      <Job key={id} item={selected} demo={data.demo} />
    ) : (
      <EmptyState message="Repair not found." />
    );
  const items = data.items.filter((i) =>
    `${i.property} ${i.title}`.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <>
      <Header title="Maintenance">
        <div className="portal-tabs">
          {["Board", "List"].map((v) => (
            <button
              key={v}
              aria-pressed={view === v}
              onClick={() => setView(v)}
            >
              {v}
            </button>
          ))}
        </div>
      </Header>
      <FormInput
        id="portal-search"
        label="Search repairs · ⌘K"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />
      {items
        .filter((i) => i.urgency === "Emergency" && isOpen(i))
        .map((item) => (
          <ItemLink key={item.id} item={item} demo={data.demo} />
        ))}
      {!items.length ? (
        <EmptyState message="No maintenance records match." />
      ) : view === "List" ? (
        items.map((item) => (
          <ItemLink key={item.id} item={item} demo={data.demo} />
        ))
      ) : (
        <div className="portal-board">
          {lanes.map((name) => (
            <section key={name}>
              <h2>
                {name}{" "}
                <span className="caption">
                  {items.filter((i) => lane(i) === name).length}
                </span>
              </h2>
              {items
                .filter((i) => lane(i) === name)
                .map((item) => (
                  <Link
                    key={item.id}
                    className="portal-job-card"
                    href={portalHref("maintenance", data.demo, item.id)}
                  >
                    <Flags flags={item.flags} />
                    <h3>{item.title}</h3>
                    <p>{item.property}</p>
                    <p className="caption">
                      {item.urgency} · {item.waiting_on}
                    </p>
                    <p className="caption">
                      {item.autonomy === 0
                        ? "You’re handling"
                        : "AI supervised"}
                    </p>
                  </Link>
                ))}
            </section>
          ))}
        </div>
      )}
    </>
  );
}
function Job({ item, demo }: { item: PortalItem; demo: boolean }) {
  const mutation = useAction();
  const [reason, setReason] = useState("");
  const [target, setTarget] = useState(progressStages(item)[item.stage]);
  const [spendLimit, setSpendLimit] = useState(
    item.spend_limit?.toString() ?? "",
  );
  const [urgency, setUrgency] = useState<string | null>(null);
  const act = (action: string, value = "") =>
    mutation.mutate({
      path: `portal/items/${encodeURIComponent(item.id)}/command?demo=${demo}`,
      body: { version: item.version, action, value, text: reason },
    });
  return (
    <>
      <Link
        className="draw-underline caption"
        href={portalHref("maintenance", demo)}
      >
        ← All repairs
      </Link>
      <Header title={item.title}>
        <Takeover item={item} demo={demo} />
      </Header>
      <div className="actions">
        <p>
          {item.property} · {item.person}
        </p>
        <Flags flags={item.flags} />
      </div>
      <EmergencyControls item={item} demo={demo} />
      <div className="portal-job-layout">
        <div>
          <ProgressCard item={item} />
          <Section title="The next decision">
            <h3>
              {item.emergency
                ? "Make safe now — landlord approval is not required"
                : item.approved
                ? "Spend approved — ready to find a contractor"
                : item.flags.includes("Human only")
                  ? "A person needs to decide"
                  : "Review the evidence and next step"}
            </h3>
            <p>{item.handover}</p>
            <div className="portal-decision">
              <dl>
                <dt>Repair estimate</dt>
                <dd>{money(item.estimate)}</dd>
                <dt>Landlord spend limit</dt>
                <dd>{money(item.spend_limit)}</dd>
              </dl>
              <div className="actions">
                {!item.emergency && <Button
                  loading={mutation.isPending}
                  disabled={
                    item.approved ||
                    item.flags.includes("Human only") ||
                    (item.estimate !== null &&
                      item.spend_limit !== null &&
                      item.estimate > item.spend_limit &&
                      !reason.trim())
                  }
                  onClick={() => act("approve")}
                >
                  {item.approved
                    ? "Approved"
                    : `Approve ${money(item.estimate)} repair`}
                </Button>}
                <Link
                  className="draw-underline"
                  href={portalHref("inbox", demo, item.id)}
                >
                  Open conversation ↗
                </Link>
              </div>
              <p className="caption">
                {item.emergency
                  ? "Make-safe authority is active. Normal spending checks resume once the immediate danger is resolved."
                  : "Over-limit approval requires the landlord’s approval source in the reason field. Approval records your decision. Contractor dispatch remains a separate action."}
              </p>
            </div>
          </Section>
          <Section title="Timeline">
            {item.timeline.length ? (
              item.timeline.map((event, index) => (
                <article key={index} className="portal-activity">
                  <p className="caption">
                    {when(event.at)} · {event.actor}
                  </p>
                  <strong>{event.action.replaceAll("_", " ")}</strong>
                  {event.detail && <p>{event.detail}</p>}
                </article>
              ))
            ) : (
              <EmptyState message="No portal decisions recorded yet." />
            )}
          </Section>
        </div>
        <aside>
          <Section title="Human controls">
            <div className="form">
              <FormTextarea
                label="Decision / reason / evidence"
                placeholder="Explain what changed and cite the source…"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
              <Button
                variant="ghost"
                disabled={!reason.trim()}
                loading={mutation.isPending}
                onClick={() => act("note")}
              >
                Add note
              </Button>
              <FormInput
                label="Verified spend limit (£)"
                type="number"
                min={0}
                max={100000}
                value={spendLimit}
                onChange={(e) => setSpendLimit(e.target.value)}
              />
              <Button
                variant="ghost"
                disabled={!reason.trim() || spendLimit === ""}
                loading={mutation.isPending}
                onClick={() => act("authority", spendLimit)}
              >
                Record spend authority
              </Button>
              <FormSelect
                label="Progress stage"
                value={progressStages(item).includes(target) ? target : progressStages(item)[item.stage]}
                onChange={(e) => setTarget(e.target.value)}
                options={progressStages(item).map((stage) => ({
                  value: stage,
                  label: stage,
                }))}
              />
              <Button
                variant="ghost"
                disabled={!reason.trim()}
                loading={mutation.isPending}
                onClick={() => act("stage", progressStages(item).includes(target) ? target : progressStages(item)[item.stage])}
              >
                Record stage override
              </Button>
              <FormSelect
                label="Urgency"
                value={item.emergency ? "Emergency" : urgency ?? item.urgency}
                onChange={(e) => setUrgency(e.target.value)}
                options={["Routine", "Urgent", "Emergency"].map((v) => ({
                  value: v,
                  label: v,
                }))}
              />
              <Button
                variant="ghost"
                disabled={!reason.trim()}
                loading={mutation.isPending}
                onClick={() => act("urgency", urgency ?? item.urgency)}
              >
                Update urgency
              </Button>
              <Button
                variant="ghost"
                disabled={!reason.trim()}
                loading={mutation.isPending}
                onClick={() => act("reject")}
              >
                Reject proposal & take over
              </Button>
              {item.stage === 9 && (
                <Button
                  variant="ghost"
                  disabled={!reason.trim()}
                  loading={mutation.isPending}
                  onClick={() => act("confirm_fix")}
                >
                  Record tenant fix confirmation
                </Button>
              )}
              {item.stage >= 9 && (
                <Button
                  variant="ghost"
                  loading={mutation.isPending}
                  onClick={() => act("reopen")}
                >
                  Reopen repair
                </Button>
              )}
              <State error={mutation.error} />
              {mutation.isSuccess && <p role="status">Decision recorded.</p>}
            </div>
          </Section>
          <Section title="Share progress">
            <ShareControls item={item} demo={demo} />
          </Section>
          <Section title="Evidence">
            <p>{item.confidence} confidence</p>
            {item.reasons.map((r) => (
              <p key={r}>{r}</p>
            ))}
            {item.facts.map((f) => (
              <Link
                className="draw-underline"
                href={`/entities/${encodeURIComponent(f.id)}`}
                key={f.id}
              >
                {f.label} ↗
              </Link>
            ))}
          </Section>
        </aside>
      </div>
    </>
  );
}
