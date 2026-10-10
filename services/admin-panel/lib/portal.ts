export const stages = [
  "Reported",
  "Collecting details",
  "Triaged",
  "Landlord approval",
  "Finding a contractor",
  "Scheduled",
  "Confirmed by tenant",
  "On the way",
  "In progress",
  "Fixed?",
  "Report sent",
  "Closed",
];
export const emergencyStages = [
  "Reported",
  "Safety steps sent",
  "Emergency confirmed",
  "Make-safe dispatched",
  "On the way",
  "Made safe",
];
export type PortalItem = {
  delivery_status?: string | null;
  id: string;
  title: string;
  property: string;
  person: string;
  role: string;
  urgency: string;
  stage: number;
  emergency: boolean;
  flags: string[];
  autonomy: number;
  version: number;
  demo: boolean;
  source_id: string | null;
  reported_at: string | null;
  due_at: string | null;
  estimate: number | null;
  spend_limit: number | null;
  approved: boolean;
  contractor: string;
  eta: string | null;
  waiting_on: string;
  draft: string;
  confidence: string;
  reasons: string[];
  handover: string;
  tenant_fixed?: boolean;
  facts: { id: string; label: string }[];
  messages: {
    id: string;
    author: string;
    text: string;
    channel: string;
    at: string | null;
    direction: string;
  }[];
  timeline: { at: string; actor: string; action: string; detail?: string }[];
};
export type Trip = {
  id: string;
  prospect: string;
  status: string;
  version: number;
  travel_minutes: number;
  visits: {
    property_id: string;
    property: string;
    start: string;
    end: string;
  }[];
};
export type Prospect = {
  id: string;
  name: string;
  budget: number;
  start: string;
  end: string;
};
export type PortalData = {
  people?: { id: string; name: string }[];
  prospects?: Prospect[];
  demo: boolean;
  items: PortalItem[];
  settings: { paused: boolean };
  trips: Trip[];
  properties: {
    id: string;
    name: string;
    rent: number | null;
    occupied: boolean;
    consent: boolean;
    compliant: boolean;
    notice_hours: number;
    start: string;
    end: string;
  }[];
  prospect: Prospect | null;
};
export const progressStages = (item: PortalItem) =>
  item.emergency ? emergencyStages : stages;
export const isOpen = (item: PortalItem) =>
  item.stage < progressStages(item).length - 1;
export const needsHuman = (item: PortalItem) =>
  isOpen(item) &&
  (item.flags.some((f) =>
    [
      "Emergency",
      "Needs your OK",
      "Human only",
      "Fraud check",
      "Unlawful request",
      "Conflict",
      "Low confidence",
      "SLA breached",
      "Repeat fault",
      "Over quote",
      "Compliance due",
    ].includes(f),
  ) ||
    item.autonomy < 3 ||
    !!item.draft);
export function needsYou(items: PortalItem[]) {
  const priorities: Record<string, number> = {
    Emergency: 0,
    Urgent: 1,
    Routine: 2,
  };
  return items
    .filter(needsHuman)
    .sort(
      (a, b) =>
        (priorities[a.urgency] ?? 3) - (priorities[b.urgency] ?? 3) ||
        (a.due_at ?? "z").localeCompare(b.due_at ?? "z"),
    );
}
export const money = (value: number | null) =>
  value === null
    ? "Not recorded"
    : new Intl.NumberFormat("en-GB", {
        style: "currency",
        currency: "GBP",
        maximumFractionDigits: 0,
      }).format(value);
export function when(value: string | null) {
  if (!value) return "Not recorded";
  return new Date(value).toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}
export function portalHref(section: string, demo: boolean, id?: string) {
  return `/portal/${section}${id ? `/${encodeURIComponent(id)}` : ""}${demo ? "?demo=1" : ""}`;
}

// Present earlier sample records with the same workflow language as new records.
export function workspacePresentation(data: PortalData): PortalData {
  if (!data.demo) return data;
  const labels: Record<string, string> = {
    "Demo fixture": "Workspace setup",
    "Scenario loaded — simulated history": "Record created",
    "Demo reply simulated": "Reply saved",
    "You · demo": "You",
    "Illustrative scenario from the portal specification; no live agent action has occurred.":
      "Review the report and verify access before the next step.",
  };
  return { ...data, items: data.items.map(item => ({
    ...item,
    handover: item.handover.replace(" No real messages or calls have been sent.", ""),
    reasons: item.reasons.map(reason => labels[reason] ?? reason),
    timeline: item.timeline.map(event => ({ ...event,
      actor: labels[event.actor] ?? event.actor,
      action: labels[event.action] ?? event.action,
    })),
    messages: item.messages.map(message => ({ ...message, author: labels[message.author] ?? message.author })),
  })) };
}
