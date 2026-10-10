"use client";
import { endpoint, type Entity } from "@/lib/api";
import { Section } from "../common";
import { Markdown } from "../markdown";
import { FormSelect, FormTextarea } from "../ui/Input";

export const ticketCompleted = (status: unknown) =>
  status === "resolved" || status === "closed";

export function TicketCompletion({ entity }: { entity: Entity }) {
  if (!ticketCompleted(entity.fields.status)) return null;
  return (
    <Section title="Completion">
      {([ ["final_answer", "Final answer", "answer.md"],
          ["reasoning", "Reasoning", "reasoning.md"] ] as const).map(
        ([key, label, filename]) => (
          <div key={key} className="mb-6 min-w-0">
            <div className="actions mb-3">
              <h3>{label}</h3>
              <a
                className="draw-underline"
                href={endpoint(`tickets/${encodeURIComponent(entity.id)}/exports/${filename}`)}
                download={filename}
              >
                Download {filename}
              </a>
            </div>
            <Markdown className="break-words">
              {String(entity.fields[key] ?? "")}
            </Markdown>
          </div>
        ),
      )}
    </Section>
  );
}

export function TicketCompletionEditor({
  status, finalAnswer, reasoning, onStatus, onAnswer, onReasoning,
}: {
  status: string;
  finalAnswer: string;
  reasoning: string;
  onStatus: (value: string) => void;
  onAnswer: (value: string) => void;
  onReasoning: (value: string) => void;
}) {
  const required = ticketCompleted(status);
  return (
    <>
      <FormSelect
        label="Ticket status"
        required
        value={status}
        onChange={(event) => onStatus(event.target.value)}
        options={["", "reported", "triaged", "scheduled", "in progress",
          "awaiting parts", "resolved", "closed"].map((value) => ({
            value, label: value || "Not specified",
          }))}
      />
      <FormTextarea
        label="Final answer (Markdown)"
        required={required}
        rows={6}
        value={finalAnswer}
        placeholder="State the answer, query result, or whether the instruction was executed. Explain why if it was not."
        onChange={(event) => onAnswer(event.target.value)}
      />
      <FormTextarea
        label="Reasoning (Markdown)"
        required={required}
        rows={12}
        value={reasoning}
        placeholder="Document every observable step, sources, actions, results, verification, failures and limitations. Explain how the evidence supports the outcome."
        onChange={(event) => onReasoning(event.target.value)}
      />
    </>
  );
}
