"use client";

import type { ComponentType, ReactNode } from "react";

import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";

import { LEFT_RULE_CLASS } from "./styles";

/** One tile: no fill, the left rule, and the hover line across the whole tile. */
export const OPTION_TILE_CLASS = cn(
  LEFT_RULE_CLASS,
  "draw-underline group relative h-auto items-center justify-start gap-3 p-3 pr-12 pl-3 text-left whitespace-normal disabled:opacity-100 sm:p-4 sm:pl-3 has-[>svg]:pl-3",
);

/**
 * A choice among sources or types: icon, title, an optional chip and a count in
 * the corner. Lay several out in a grid. A disabled tile fades its words, not
 * its icon.
 */
export function OptionTile({
  icon: Icon,
  title,
  chip,
  count,
  disabled = false,
  pressed,
  onClick,
  className,
  ...aria
}: {
  icon: ComponentType<{ className?: string }>;
  title: string;
  chip?: ReactNode;
  count?: number;
  disabled?: boolean;
  /** For a tile that stays chosen; keeps its line drawn. */
  pressed?: boolean;
  onClick: (origin: HTMLButtonElement) => void;
  className?: string;
  "aria-haspopup"?: "dialog";
  "aria-expanded"?: boolean;
  "aria-controls"?: string;
}) {
  return (
    <Button
      type="button"
      variant="ghost"
      disabled={disabled}
      aria-pressed={pressed}
      onClick={(event) => onClick(event.currentTarget)}
      className={cn(
        OPTION_TILE_CLASS,
        "aria-pressed:after:[transform:scaleX(1)]",
        className,
      )}
      {...aria}
    >
      <Icon className="size-4 shrink-0 text-foreground" />
      <span className="min-w-0 text-sm font-semibold group-disabled:opacity-50">
        {title}
      </span>
      {chip ? <span className="group-disabled:opacity-50">{chip}</span> : null}
      {count && count > 0 ? (
        <span className="absolute top-3.5 right-3.5 text-xs leading-6 font-medium tabular-nums">
          {count.toLocaleString()}
        </span>
      ) : null}
    </Button>
  );
}
