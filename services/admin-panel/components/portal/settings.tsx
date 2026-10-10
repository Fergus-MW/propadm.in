"use client";
import Link from "next/link";
import { portalHref, type PortalData } from "@/lib/portal";
import { Header, Section } from "../common";
export function PortalSettings({ data }: { data: PortalData }) {
  return (
    <>
      <Header title="Automation & safeguards" />
      <p className="portal-intro">
        {data.settings.paused
          ? "Automation is paused."
          : "Automation is available."}{" "}
        Use the workspace control above to pause new agent actions.
      </p>
      <Section title="Workspace data">
        <p>{data.demo
          ? "Sample records. Replies are stored locally; external delivery is disabled for this workspace."
          : "Connected property records. Approved replies use the connected email service."}</p>
        <Link className="draw-underline" href={portalHref("today", !data.demo)}>
          {data.demo ? "Use connected records" : "Open sample workspace"} ↗
        </Link>
      </Section>
      <Section title="Control levels">
        <dl className="portal-settings-grid">
          {[
            ["Autopilot", "Agent tools can act within the existing workflow."],
            [
              "Draft for me",
              "A person reviews before the agent can perform further actions.",
            ],
            [
              "Tell me",
              "Read-only suggestions; consequential actions remain with a person.",
            ],
            [
              "Paused",
              "You’re handling this. Agent reads and planning remain available.",
            ],
          ].map(([name, description]) => (
            <div key={name}>
              <dt>{name}</dt>
              <dd>{description}</dd>
            </div>
          ))}
        </dl>
      </Section>
      <Section title="Always-human decisions">
        <p>
          Human only, Fraud check, Unlawful request and Conflict flags prevent
          automatic hand-back. Missing spend authority blocks booking;
          completion requires tenant confirmation.
        </p>
        <p className="portal-notice">
          Pausing prevents new MCP actions. It cannot recall a message or stop
          an external call already in flight. Emergency safety action remains
          the on-call manager’s responsibility while paused.
        </p>
      </Section>
      <Section title="Connected services">
        <p>
          Existing email, voice, graph and service provider tools remain in the
          operations workspace.
        </p>
        <div className="actions">
          <Link href="/settings" className="draw-underline">
            Manage integrations ↗
          </Link>
          <Link href="/providers" className="draw-underline">
            Trusted contractors ↗
          </Link>
          <Link href="/properties" className="draw-underline">
            Properties & money ↗
          </Link>
        </div>
      </Section>
    </>
  );
}
