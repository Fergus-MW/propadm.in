"use client";
import { workspacePresentation } from "@/lib/portal";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowUpRight, Pause, Play } from "lucide-react";
import { api } from "@/lib/api";
import { useAction, useLive } from "@/lib/hooks";
import {
  type PortalData,
  isOpen,
  needsYou,
  portalHref,
  when,
} from "@/lib/portal";
import { Header, State, Section } from "../common";
import { Button } from "../ui/Button";
import { StatGrid } from "../library/StatGrid";
import { EmptyState } from "../library/EmptyState";
import { ItemLink, Mascot } from "./shared";
import { Inbox } from "./inbox";
import { Maintenance } from "./maintenance";
import { Viewings, Calendar, Availability } from "./viewings";
import { PortalSettings } from "./settings";

export function Portal({
  section = "today",
  id,
}: {
  section?: string;
  id?: string;
}) {
  const demo = useSearchParams().get("demo") === "1";
  useLive("portal/stream");
  const query = useQuery<PortalData>({
    queryKey: ["portal", demo],
    queryFn: () => api(`portal?demo=${demo}`),
    refetchInterval: 5000,
  });
  const action = useAction();
  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === "k") {
        event.preventDefault();
        document.querySelector<HTMLInputElement>("#portal-search")?.focus();
      }
    };
    document.addEventListener("keydown", listener);
    return () => document.removeEventListener("keydown", listener);
  }, []);
  if (!query.data)
    return (
      <State
        pending={query.isPending}
        error={query.error}
        retry={() => void query.refetch()}
      />
    );
  const data = workspacePresentation(query.data);
  return (
    <div className="portal-workspace">
      <div className="portal-mode">
        <span>
          Property workspace
        </span>
        <div className="actions">
          <Link className="draw-underline" href={portalHref("settings", demo)}>
            Workspace settings
          </Link>
          <Button
            variant="ghost"
            loading={action.isPending}
            onClick={() =>
              action.mutate({
                path: `portal/settings?demo=${demo}`,
                method: "PATCH",
                body: { paused: !data.settings.paused },
              })
            }
          >
            {data.settings.paused ? <Play size={14} /> : <Pause size={14} />}{" "}
            {data.settings.paused ? "Resume automation" : "Pause automation"}
          </Button>
        </div>
      </div>
      <State error={action.error ?? query.error} />
      {demo && !data.items.length ? (
        <div className="portal-welcome">
          <Mascot />
          <h1>Meet your new working day.</h1>
          <p>
            Manage maintenance, approvals and viewing trips in one place.
          </p>
          <Button
            loading={action.isPending}
            onClick={() => action.mutate({ path: "portal/demo", body: {} })}
          >
            Open workspace <ArrowUpRight size={16} />
          </Button>
        </div>
      ) : (
        <>
          <nav className="portal-tabs" aria-label="Portal views">
            {[
              "today",
              "inbox",
              "maintenance",
              "viewings",
              "calendar",
              "availability",
              "settings",
            ].map((name) => (
              <Link
                key={name}
                aria-current={name === section ? "page" : undefined}
                href={portalHref(name, demo)}
              >
                {name === "today"
                  ? "Today"
                  : name[0].toUpperCase() + name.slice(1)}
              </Link>
            ))}
          </nav>
          {data.settings.paused && (
            <p className="portal-notice">
              <Pause size={16} /> Automation paused. New agent actions are
              blocked; calls or sends already in flight cannot be recalled.
            </p>
          )}
          {section === "today" ? (
            <Today data={data} />
          ) : section === "inbox" ? (
            <Inbox data={data} id={id} />
          ) : section === "maintenance" ? (
            <Maintenance data={data} id={id} />
          ) : section === "viewings" ? (
            <Viewings data={data} />
          ) : section === "calendar" ? (
            <Calendar data={data} />
          ) : section === "availability" ? (
            <Availability data={data} />
          ) : section === "settings" ? (
            <PortalSettings data={data} />
          ) : (
            <EmptyState message="This portal page does not exist." />
          )}
        </>
      )}
    </div>
  );
}
export function PortalAlert() {
  const demo = useSearchParams().get("demo") === "1";
  const query = useQuery<PortalData>({
    queryKey: ["portal", demo],
    queryFn: () => api(`portal?demo=${demo}`),
    refetchInterval: 5000,
    retry: false,
  });
  const emergencies =
    query.data?.items.filter((i) => i.urgency === "Emergency" && isOpen(i)) ??
    [];
  if (!emergencies.length) return null;
  return (
    <Link
      className="portal-emergency-banner"
      href={portalHref("maintenance", demo, emergencies[0].id)}
    >
      <AlertTriangle size={18} />
      <strong>

        {emergencies.length} open{" "}
        {emergencies.length === 1 ? "emergency" : "emergencies"}
      </strong>
      <span>
        {emergencies[0].property} · {emergencies[0].title}
      </span>
      <ArrowUpRight size={18} />
    </Link>
  );
}
function Today({ data }: { data: PortalData }) {
  const queue = needsYou(data.items);
  const open = data.items.filter(isOpen);
  const recent = data.items
    .flatMap((item) => item.timeline.map((event) => ({ ...event, item })))
    .sort((a, b) => b.at.localeCompare(a.at))
    .slice(0, 5);
  return (
    <>
      <Header title="A little oversight. A lot moving.">
        <Mascot />
      </Header>
      <p className="portal-intro">
        Your portfolio, in order. Start with what needs you.
      </p>
      <StatGrid
        stats={[
          { label: "Needs you", value: queue.length },
          { label: "Open repairs", value: open.length },
          {
            label: "AI handling",
            value: open.filter((i) => i.autonomy === 3).length,
          },
          {
            label: "Viewing trips",
            value: data.trips.filter((t) => t.status === "Confirmed").length,
          },
        ]}
      />
      <div className="portal-today-grid">
        <Section title="Needs you">
          <div>
            {queue.length ? (
              queue.map((item) => (
                <ItemLink key={item.id} item={item} demo={data.demo} />
              ))
            ) : (
              <EmptyState message="Nothing needs your attention." />
            )}
          </div>
        </Section>
        <Section title="Recent activity">
          {recent.length ? (
            recent.map((event, index) => (
              <div className="portal-activity" key={index}>
                <p className="caption">
                  {when(event.at)} · {event.actor}
                </p>
                <p>{event.action.replaceAll("_", " ")}</p>
                <Link
                  className="draw-underline caption"
                  href={portalHref("maintenance", data.demo, event.item.id)}
                >
                  {event.item.property}
                </Link>
              </div>
            ))
          ) : (
            <EmptyState message="No portal actions recorded yet." />
          )}
          <Link className="draw-underline" href="/actions">
            View system audit log ↗
          </Link>
        </Section>
      </div>
      <Section title="Your schedule">
        <Calendar data={data} compact />
      </Section>
    </>
  );
}
