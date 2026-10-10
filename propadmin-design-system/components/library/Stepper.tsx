import { StatusText } from "./StatusText";

export interface Step {
  label: string;
  /** A failed step is marked with the error underline. */
  failed?: boolean;
}

/**
 * The steps of a flow or a pipeline as plain labels in order. The current step
 * keeps its line drawn; no pills, fills or numbered circles.
 */
export function Stepper({
  steps,
  current,
  label,
}: {
  steps: readonly Step[];
  /** Index of the current step. */
  current: number;
  /** Names the steps for screen readers, such as "Report steps". */
  label: string;
}) {
  return (
    <ol
      aria-label={label}
      className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm"
    >
      {steps.map((step, index) => (
        <li
          key={step.label}
          aria-current={index === current ? "step" : undefined}
          className="draw-underline font-medium aria-[current=step]:after:[transform:scaleX(1)]"
        >
          {step.failed ? (
            <StatusText variant="error">{step.label}</StatusText>
          ) : (
            step.label
          )}
        </li>
      ))}
    </ol>
  );
}
