import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type NoticeTone = "neutral" | "info" | "success" | "warning" | "error";

const TONE: Record<NoticeTone, string> = {
  neutral: "border-l-4 border-foreground pl-3",
  info: "bg-info-subtle p-3 text-info-text",
  success: "bg-success-subtle p-3 text-success-text",
  warning: "bg-warning-subtle p-3 text-warning-text",
  error: "bg-destructive-subtle p-3 text-destructive-text",
};

/**
 * A whole-sentence notice. A tinted surface or, when neutral, the left rule;
 * never both a tint and an outline. Short status labels use StatusText instead.
 */
export function Notice({
  tone = "neutral",
  children,
  action,
  className,
}: {
  tone?: NoticeTone;
  children: ReactNode;
  /** At most one action, as a text action. */
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      role={tone === "error" || tone === "warning" ? "alert" : "status"}
      className={cn(
        "flex flex-wrap items-center justify-between gap-x-4 gap-y-2 text-sm",
        TONE[tone],
        className,
      )}
    >
      <div className="min-w-0">{children}</div>
      {action}
    </div>
  );
}
