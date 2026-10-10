"use client";

import { ArrowDown, ArrowUp } from "lucide-react";
import type { ReactNode } from "react";

import { Button, TableHead } from "@/components/ui";
import { cn } from "@/lib/utils";

import { TEXT_ACTION_CLASS } from "./styles";

export type SortDirection = "asc" | "desc";

/**
 * A column header that sorts the table. The sorted column carries aria-sort,
 * keeps its line drawn and shows the direction; short label, full name on hover.
 */
export function SortableTableHead({
  label,
  fullLabel,
  active,
  direction,
  onSort,
  align = "left",
  className,
}: {
  label: ReactNode;
  fullLabel: string;
  active: boolean;
  direction: SortDirection;
  onSort: () => void;
  align?: "left" | "center" | "right";
  className?: string;
}) {
  const Arrow = direction === "asc" ? ArrowUp : ArrowDown;
  return (
    <TableHead
      aria-sort={
        active ? (direction === "asc" ? "ascending" : "descending") : undefined
      }
      className={cn(
        "group",
        align === "left" && "text-left",
        align === "center" && "text-center",
        align === "right" && "text-right",
        className,
      )}
    >
      <Button
        variant="ghost"
        size="xs"
        title={fullLabel}
        aria-label={fullLabel}
        onClick={onSort}
        className={cn(
          TEXT_ACTION_CLASS,
          "text-[length:inherit] group-aria-[sort]:after:[transform:scaleX(1)]",
          active ? "font-semibold" : "font-medium",
        )}
      >
        {label}
        {active ? <Arrow aria-hidden /> : null}
      </Button>
    </TableHead>
  );
}
