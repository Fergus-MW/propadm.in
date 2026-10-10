"use client";
import Link from "next/link";
import { useState } from "react";
import {
  AlertTriangle,
  ArrowUpRight,
  Check,
  Circle,
  Hand,
  Play,
} from "lucide-react";
import { useAction } from "@/lib/hooks";
import {
  type PortalItem,
  progressStages,
  when,
  portalHref,
} from "@/lib/portal";
import { Button } from "../ui/Button";
import { FormTextarea } from "../ui/Input";
import { StatusText } from "../library/StatusText";
import { State } from "../common";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogHeader,
  DialogDescription,
} from "../ui/dialog";

export function Flags({ flags }: { flags: string[] }) {
  return (
    <div className="portal-flags">
      {flags.map((flag) => (
        <StatusText
          key={flag}
          variant={
            /Emergency|Fraud|breached/.test(flag)
              ? "error"
              : /Human|Unlawful/.test(flag)
                ? "brand"
                : "warning"
          }
        >
          {flag}
        </StatusText>
      ))}
    </div>
  );
}
export function Mascot() {
  return (
    <svg width="44" height="44" viewBox="0 0 48 48" aria-hidden="true">
      <path
        d="M24 5 43 19 36 42H12L5 19Z"
        fill="currentColor"
        stroke="currentColor"
        strokeWidth="5"
        strokeLinejoin="round"
      />
      <g fill="var(--background)">
        <ellipse cx="18" cy="25" rx="3" ry="5" />
        <ellipse cx="30" cy="25" rx="3" ry="5" />
      </g>
    </svg>
  );
}
export function ProgressCard({ item }: { item: PortalItem }) {
  const steps = progressStages(item);
  return (
    <section
      className={`portal-progress ${item.urgency === "Emergency" ? "is-emergency" : ""}`}
      aria-label="Repair progress"
    >
      <div className="portal-progress-heading">
        <div>
          <p className="caption">
            Repair progress
          </p>
          <h2>{steps[item.stage]}</h2>
        </div>
        <StatusText
          variant={item.urgency === "Emergency" ? "error" : "success"}
        >
          {item.urgency === "Emergency" ? "Emergency" : "Repair in progress"}
        </StatusText>
      </div>
      <ol className="portal-stepper">
        {steps.map((step, index) => (
          <li
            key={step}
            aria-current={index === item.stage ? "step" : undefined}
            className={index <= item.stage ? "reached" : ""}
          >
            {index < item.stage ? (
              <Check size={16} aria-label="Complete" />
            ) : (
              <Circle
                size={16}
                fill={index === item.stage ? "currentColor" : "none"}
              />
            )}
            <span>{step}</span>
          </li>
        ))}
      </ol>
      <div className="portal-progress-detail">
        <div>
          <p className="caption">
            {item.eta ? "Estimated arrival" : "Waiting on"}
          </p>
          <strong className="portal-large">
            {item.eta ?? item.waiting_on}
          </strong>
        </div>
        <div>
          <p>{item.contractor}</p>
          <p className="caption">Reported {when(item.reported_at)}</p>
        </div>
      </div>
      {item.autonomy === 0 && (
        <p className="portal-notice">
          <Hand size={16} /> You’re handling this. New agent actions are
          blocked.
        </p>
      )}
    </section>
  );
}
export function ItemLink({ item, demo }: { item: PortalItem; demo: boolean }) {
  return (
    <Link
      className="portal-queue-row"
      href={portalHref("maintenance", demo, item.id)}
    >
      <span className="portal-priority">
        {item.urgency === "Emergency" ? (
          <AlertTriangle size={19} />
        ) : (
          <Circle size={15} />
        )}
      </span>
      <div>
        <Flags flags={item.flags} />
        <h3>{item.title}</h3>
        <p className="caption">
          {item.property} · {item.person}
        </p>
      </div>
      <span className="caption">
        {item.due_at
          ? `Due ${when(item.due_at)}`
          : progressStages(item)[item.stage]}
      </span>
      <ArrowUpRight size={18} />
    </Link>
  );
}
export function Takeover({ item, demo }: { item: PortalItem; demo: boolean }) {
  const mutation = useAction();
  const [open, setOpen] = useState(false);
  const [instruction, setInstruction] = useState("");
  const paused = item.autonomy === 0;
  const act = (action: string) =>
    mutation.mutate(
      {
        path: `portal/items/${encodeURIComponent(item.id)}/command?demo=${demo}`,
        body: { version: item.version, action, text: instruction },
      },
      { onSuccess: () => setOpen(false) },
    );
  return (
    <>
      <Button
        variant="ghost"
        loading={mutation.isPending}
        onClick={() => (paused ? setOpen(true) : act("takeover"))}
      >
        {paused ? <Play size={16} /> : <Hand size={16} />}{" "}
        {paused ? "Hand back to AI" : "Take over"}
      </Button>
      <State error={mutation.error} />
      {open && (
        <Dialog open onOpenChange={setOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Hand back to AI</DialogTitle>
              <DialogDescription>
                AI resumes at the permitted autonomy level. Human-only decisions
                stay with you.
              </DialogDescription>
            </DialogHeader>
            <FormTextarea
              label="Instructions (optional)"
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
            />
            <Button
              loading={mutation.isPending}
              onClick={() => act("handback")}
            >
              Hand back
            </Button>
            <State error={mutation.error} />
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
