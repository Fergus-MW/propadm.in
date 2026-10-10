import type { ComponentProps, ReactNode } from "react";

import { cn } from "@/lib/utils";

/** A content group on the page: no fill, no border, no rounding. */
export function Surface({ className, ...props }: ComponentProps<"section">) {
  return <section className={cn("min-w-0 py-2", className)} {...props} />;
}

/**
 * A section heading, only where two sections on one page would otherwise be
 * confused. No sentence under it: if it needs explaining, rename it.
 */
export function SurfaceHeader({
  title,
  actions,
}: {
  title: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-base font-semibold">{title}</h2>
      {actions ? (
        <div className="flex flex-wrap items-center gap-4">{actions}</div>
      ) : null}
    </div>
  );
}
