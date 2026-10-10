"use client";
import { useState } from "react";
import { useAction } from "@/lib/hooks";
import { type PortalItem } from "@/lib/portal";
import { Section, State } from "../common";
import { Button } from "../ui/Button";
import { FormTextarea } from "../ui/Input";

export function EmergencyControls({ item, demo }: { item: PortalItem; demo: boolean }) {
  const [evidence, setEvidence] = useState("");
  const mutation = useAction();
  function record(action: string, value = "") {
    mutation.mutate({
      path: `portal/items/${encodeURIComponent(item.id)}/command?demo=${demo}`,
      body: { version: item.version, action, value, text: evidence },
    }, { onSuccess: () => setEvidence("") });
  }
  return (
    <Section title={item.emergency ? "Emergency make-safe active" : "Emergency override"}>
      <p>{item.emergency
        ? "You are handling this emergency. Arrange qualified make-safe assistance now and notify the on-call manager and landlord. Record actions as they happen."
        : "If there is immediate danger, take over and activate make-safe. Missing forms, photos, quotes or landlord approval must not delay this response."}</p>
      <p className="portal-notice">
        This control works while automation is paused. It records authority for make-safe work above the spend limit; it does not send messages or dispatch a contractor. Privacy, identity and contractor qualification checks still apply.
      </p>
      <div className="form">
        <FormTextarea
          label="Emergency evidence and action taken"
          placeholder="What danger was confirmed, by whom, and what needs to happen now?"
          value={evidence}
          onChange={event => setEvidence(event.target.value)}
        />
        <div className="actions">
          <Button disabled={!evidence.trim()} loading={mutation.isPending}
            onClick={() => record(item.emergency ? "stage" : "emergency_override", item.emergency ? "Made safe" : "")}>
            {item.emergency ? "Confirm made safe — continue repair" : "Activate emergency make-safe & take over"}
          </Button>
          {!item.emergency && item.urgency === "Emergency" && (
            <Button variant="ghost" disabled={!evidence.trim()} loading={mutation.isPending}
              onClick={() => record("emergency_stand_down")}>
              Rule out emergency — keep urgent
            </Button>
          )}
        </div>
        <State error={mutation.error} />
        {mutation.isSuccess && <p role="status">Emergency decision recorded.</p>}
      </div>
    </Section>
  );
}
