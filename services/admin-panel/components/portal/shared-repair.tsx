"use client";
import { useQuery } from "@tanstack/react-query";
import { Check, Circle } from "lucide-react";
import { when, money } from "@/lib/portal";
import { State } from "../common";
import { Mascot } from "./shared";
type Shared = {
  audience: string;
  demo: boolean;
  property: string;
  stage: number;
  steps: string[];
  contractor: string;
  eta: string | null;
  reported_at: string;
  estimate?: number | null;
  approved?: boolean;
};
export function SharedRepair({ token }: { token: string }) {
  const query = useQuery<Shared>({
    queryKey: ["shared-repair", token],
    queryFn: async () => {
      const response = await fetch(
        `/api/repair-share?token=${encodeURIComponent(token)}`,
        { cache: "no-store" },
      );
      if (!response.ok)
        throw new Error(
          "This link has expired or is unavailable. Ask your property manager for a new link.",
        );
      return response.json();
    },
    refetchInterval: 10000,
    retry: false,
  });
  const data = query.data;
  return (
    <main className="portal-shared">
      <meta name="referrer" content="no-referrer" />
      <header>
        <Mascot />
        <strong>properly</strong>
      </header>
      <State pending={query.isPending} error={query.error} />
      {data && (
        <>
          <p className="caption">
            Your repair ·{" "}
            {data.audience} view
          </p>
          <h1>{data.property}</h1>
          <p className="portal-large">{data.steps[data.stage]}</p>
          <ol className="portal-stepper">
            {data.steps.map((step, i) => (
              <li
                className={i <= data.stage ? "reached" : ""}
                key={step}
                aria-current={i === data.stage ? "step" : undefined}
              >
                {i < data.stage ? <Check size={16} /> : <Circle size={16} />}
                <span>{step}</span>
              </li>
            ))}
          </ol>
          <p>
            {data.contractor}
            {data.eta ? ` · Estimated arrival ${data.eta}` : ""}
          </p>
          <p className="caption">Reported {when(data.reported_at)}</p>
          {data.audience === "landlord" && (
            <p>
              Repair estimate {money(data.estimate ?? null)} ·{" "}
              {data.approved ? "Approved" : "Awaiting review"}
            </p>
          )}
          <p className="portal-notice">
            For changes or questions, contact your property manager through your
            usual channel.
          </p>
        </>
      )}
    </main>
  );
}
