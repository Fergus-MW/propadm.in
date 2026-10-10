"use client";
import { useState } from "react";
import { useAction } from "@/lib/hooks";
import type { PortalItem } from "@/lib/portal";
import { Button } from "../ui/Button";
import { FormSelect } from "../ui/Input";
import { State } from "../common";
export function ShareControls({
  item,
  demo,
}: {
  item: PortalItem;
  demo: boolean;
}) {
  const [audience, setAudience] = useState("tenant");
  const [share, setShare] = useState<{ id: string; token: string } | null>(
    null,
  );
  const action = useAction<{ id: string; token: string }>();
  return (
    <div className="form">
      <FormSelect
        label="Share repair progress with"
        value={audience}
        onChange={(e) => setAudience(e.target.value)}
        options={[
          { value: "tenant", label: "Tenant · no costs or internal notes" },
          { value: "landlord", label: "Landlord · includes estimate" },
        ]}
      />
      <Button
        variant="ghost"
        loading={action.isPending}
        onClick={() =>
          action.mutate(
            {
              path: `portal/items/${encodeURIComponent(item.id)}/share?demo=${demo}`,
              body: { audience },
            },
            { onSuccess: setShare },
          )
        }
      >
        Create 24-hour progress link
      </Button>
      {share && (
        <>
          <a
            className="draw-underline"
            href={`/track/${share.token}`}
            target="_blank"
            rel="noreferrer"
          >
            Open progress link ↗
          </a>
          <p className="caption">
            Anyone with this link can see this audience’s repair update until it
            expires. Share only with the intended recipient.
          </p>
          <Button
            variant="ghost"
            loading={action.isPending}
            onClick={() =>
              action.mutate(
                {
                  path: `portal/shares/${encodeURIComponent(share.id)}`,
                  method: "DELETE",
                },
                { onSuccess: () => setShare(null) },
              )
            }
          >
            Revoke this link
          </Button>
        </>
      )}
      <State error={action.error} />
    </div>
  );
}
