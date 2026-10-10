import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

import { DIVIDED_GRID_CLASS } from "./styles";

export interface KeyValue {
  label: string;
  value: ReactNode;
  /** The full name or an explanation, on hover. */
  title?: string;
}

/**
 * Facts as two columns of equal cells, label and value at the same size and
 * weight, the dividers meeting across the columns. Callers drop empty values.
 */
export function KeyValueGrid({
  items,
  className,
}: {
  items: readonly KeyValue[];
  className?: string;
}) {
  if (!items.length) return null;
  return (
    <dl className={cn(DIVIDED_GRID_CLASS, "text-sm font-medium", className)}>
      {items.map((item) => (
        <div
          key={item.label}
          title={item.title}
          className="grid grid-cols-[auto_minmax(0,1fr)] items-baseline gap-x-3 py-2"
        >
          <dt>{item.label}</dt>
          <dd className="min-w-0 text-right break-words tabular-nums">
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
