import { cn } from "@/lib/utils";

import { LEFT_RULE_CLASS } from "./styles";

/** Preformatted text (JSON, a raw record): monospace on the left rule, no grey box. */
export function CodeBlock({
  children,
  className,
}: {
  children: string;
  className?: string;
}) {
  return (
    <pre
      className={cn(
        LEFT_RULE_CLASS,
        "overflow-x-auto py-1 pl-3 font-mono text-xs whitespace-pre-wrap break-words",
        className,
      )}
    >
      {children}
    </pre>
  );
}
