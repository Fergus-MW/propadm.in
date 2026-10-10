import type { ReactElement, ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface Stat {
  label: string;
  value: ReactNode;
  /** Explains the label on hover, instead of a caption under the figure. */
  title?: string;
}

/**
 * Figures as plain label-over-number items: no tile fill, the drawn line on hover.
 * Callers drop zero and empty figures before passing them in.
 */
export function StatGrid({
  stats,
  className,
}: {
  stats: readonly Stat[];
  className?: string;
}): ReactElement | null {
  if (!stats.length) return null;
  return (
    <dl
      className={cn(
        "grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-3 lg:grid-cols-4",
        className,
      )}
    >
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="group draw-underline pb-2"
          title={stat.title}
        >
          <dt className="text-xs">{stat.label}</dt>
          <dd className="mt-1 text-2xl font-medium tabular-nums">
            {stat.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
