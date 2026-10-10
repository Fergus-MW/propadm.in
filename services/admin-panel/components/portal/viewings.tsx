"use client";
import Link from "next/link";
import { useState } from "react";
import { CalendarDays, ArrowRight } from "lucide-react";
import { useAction } from "@/lib/hooks";
import { type PortalData, money, portalHref, when } from "@/lib/portal";
import { Header, Section, State } from "../common";
import { Button } from "../ui/Button";
import { FormInput, FormSelect } from "../ui/Input";
import { StatusText } from "../library/StatusText";
import { AvailabilityEditor } from "./availability-editor";
import { EmptyState } from "../library/EmptyState";

export function Viewings({ data }: { data: PortalData }) {
  const [prospectId, setProspectId] = useState("");
  const prospect =
    data.prospect ??
    data.prospects?.find((p) => p.id === prospectId) ??
    data.prospects?.[0];
  const [selected, setSelected] = useState<string[]>([]);
  const [travel, setTravel] = useState(15);
  const action = useAction();
  return (
    <>
      <Header title="More homes. One trip." />
      <p className="portal-intro">
        Turn one availability window into a considered viewing itinerary.
      </p>
      {!data.demo && !!data.prospects?.length && (
        <FormSelect
          label="Prospect"
          value={prospect?.id}
          onChange={(e) => setProspectId(e.target.value)}
          options={data.prospects.map((p) => ({ value: p.id, label: p.name }))}
        />
      )}
      {!prospect ? (
        <EmptyState message="No prospect availability is connected yet." />
      ) : (
        <div className="portal-job-layout">
          <div>
            <Section title={prospect.name}>
              <p>
                Budget {money(prospect.budget)} / month · Available{" "}
                {when(prospect.start)} – {when(prospect.end)}
              </p>
              <p className="caption">Agent-led visits · 30 minutes per home</p>
            </Section>
            <Section title="Choose homes in visit order">
              {data.properties.map((prop) => (
                <label key={prop.id} className="portal-property-option">
                  <input
                    type="checkbox"
                    checked={selected.includes(prop.id)}
                    onChange={(e) =>
                      setSelected(
                        e.target.checked
                          ? [...selected, prop.id]
                          : selected.filter((id) => id !== prop.id),
                      )
                    }
                  />
                  <div>
                    <h3>{prop.name}</h3>
                    <p>{money(prop.rent)} / month</p>
                    <StatusText
                      variant={
                        !prop.compliant || (prop.occupied && !prop.consent)
                          ? "warning"
                          : "success"
                      }
                    >
                      {!prop.compliant
                        ? "Compliance evidence required · cannot book"
                        : prop.occupied && !prop.consent
                          ? "Tenant consent required · cannot book"
                          : "Cleared for viewing"}
                    </StatusText>
                    <p className="caption">
                      {prop.notice_hours}h minimum notice
                    </p>
                  </div>
                  {selected.includes(prop.id) && (
                    <span>Stop {selected.indexOf(prop.id) + 1}</span>
                  )}
                </label>
              ))}
            </Section>
            <FormInput
              label="Travel buffer between homes (minutes)"
              type="number"
              min={5}
              max={120}
              value={travel}
              onChange={(e) => setTravel(Number(e.target.value))}
            />
            <div className="portal-actions">
              <Button
                disabled={!selected.length || !Number.isFinite(travel)}
                loading={action.isPending}
                onClick={() =>
                  action.mutate({
                    path: `portal/trips/propose?demo=${data.demo}`,
                    body: {
                      property_ids: selected,
                      prospect_id: prospect!.id,
                      start: prospect!.start,
                      end: prospect!.end,
                      travel_minutes: travel,
                    },
                  })
                }
              >
                Propose trip <ArrowRight size={16} />
              </Button>
            </div>
            <State error={action.error} />
          </div>
          <aside>
            <Section title="Booking checks">
              <p>
                Tenant consent, compliance, notice, availability, travel buffers
                and double bookings are checked by the server.
              </p>
              <p className="portal-notice">
                Travel time is your supplied buffer, not a live route estimate.
              </p>
            </Section>
          </aside>
        </div>
      )}
      <p className="portal-actions">
        <Link
          className="draw-underline"
          href={portalHref("availability", data.demo)}
        >
          Manage availability & property viewing rules ↗
        </Link>
      </p>
      <Section title="Viewing trips">
        {data.trips.length ? (
          data.trips.map((trip) => (
            <article key={trip.id} className="portal-trip">
              <div className="actions">
                <h3>{trip.prospect}</h3>
                <StatusText
                  variant={trip.status === "Confirmed" ? "success" : "warning"}
                >
                  {trip.status}
                </StatusText>
              </div>
              <ol>
                {trip.visits.map((visit) => (
                  <li key={visit.property_id}>
                    <CalendarDays size={16} />
                    <div>
                      <strong>{visit.property}</strong>
                      <p>
                        {when(visit.start)} – {when(visit.end)}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
              {trip.status === "Proposed" && (
                <Button
                  loading={action.isPending}
                  onClick={() =>
                    action.mutate({
                      path: `portal/trips/${encodeURIComponent(trip.id)}/confirm?demo=${data.demo}`,
                      body: {},
                    })
                  }
                >
                  Confirm itinerary
                </Button>
              )}
              <p className="caption">
                {data.demo
                  ? "Itinerary recorded."
                  : "Itinerary recorded. Send invitations through the connected email workflow."}
              </p>
            </article>
          ))
        ) : (
          <EmptyState message="No trips proposed yet." />
        )}
      </Section>
    </>
  );
}
export function Calendar({
  data,
  compact = false,
}: {
  data: PortalData;
  compact?: boolean;
}) {
  const [offset, setOffset] = useState(0);
  const events = data.trips
    .filter((t) => t.status === "Confirmed")
    .flatMap((t) => t.visits.map((v) => ({ ...v, person: t.prospect })));
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  start.setDate(start.getDate() - ((start.getDay() + 6) % 7) + offset * 7);
  const days = Array.from({ length: 7 }, (_, i) => {
    const day = new Date(start);
    day.setDate(day.getDate() + i);
    return day;
  });
  if (compact)
    return events.length ? (
      <div>
        {events.map((event, i) => (
          <div key={i} className="portal-activity">
            <strong>
              {when(event.start)} · {event.property}
            </strong>
            <p>{event.person} · Viewing</p>
          </div>
        ))}
      </div>
    ) : (
      <EmptyState message="No confirmed viewing trips yet." />
    );
  return (
    <>
      <Header title="Calendar">
        <div className="actions">
          <Button variant="ghost" onClick={() => setOffset(offset - 1)}>
            ← Previous week
          </Button>
          <Button variant="ghost" onClick={() => setOffset(0)}>
            This week
          </Button>
          <Button variant="ghost" onClick={() => setOffset(offset + 1)}>
            Next week →
          </Button>
        </div>
      </Header>
      <p className="portal-intro">
        Week of{" "}
        {start.toLocaleDateString("en-GB", { day: "numeric", month: "long" })} ·
        Confirmed viewing trips · Times shown in your timezone
      </p>
      <div className="portal-calendar">
        {days.map((day) => (
          <section key={day.toISOString()}>
            <h3>
              {day.toLocaleDateString("en-GB", {
                weekday: "short",
                day: "numeric",
              })}
            </h3>
            {events
              .filter(
                (e) => new Date(e.start).toDateString() === day.toDateString(),
              )
              .map((e, i) => (
                <Link
                  key={i}
                  href={portalHref("viewings", data.demo)}
                  className="portal-calendar-event"
                >
                  <p className="caption">
                    {new Date(e.start).toLocaleTimeString("en-GB", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                  <strong>{e.property}</strong>
                  <p>{e.person}</p>
                </Link>
              ))}
          </section>
        ))}
      </div>
      <p className="caption">
        Repairs without a confirmed visit time are shown in Maintenance.
      </p>
    </>
  );
}
export function Availability({ data }: { data: PortalData }) {
  return (
    <>
      <Header title="Availability" />
      {!data.demo && (
        <Section title="Record availability and access">
          <AvailabilityEditor data={data} />
        </Section>
      )}
      {data.prospect && (
        <Section title="Prospects">
          <div className="portal-activity">
            <h3>{data.prospect.name}</h3>
            <p>
              {when(data.prospect.start)} – {when(data.prospect.end)}
            </p>
            <Link
              className="draw-underline"
              href={portalHref("viewings", data.demo)}
            >
              Build a viewing trip ↗
            </Link>
          </div>
        </Section>
      )}
      <Section title="Repair coordination">
        {data.items.length ? (
          data.items
            .filter((i) => i.stage < 9)
            .map((item) => (
              <div className="portal-queue-row" key={item.id}>
                <div>
                  <h3>{item.property}</h3>
                  <p>
                    {item.person} · {item.waiting_on}
                  </p>
                </div>
                <Link
                  className="draw-underline"
                  href={portalHref("inbox", data.demo, item.id)}
                >
                  Request times in conversation ↗
                </Link>
              </div>
            ))
        ) : (
          <EmptyState message="No repair availability records yet." />
        )}
      </Section>
    </>
  );
}
