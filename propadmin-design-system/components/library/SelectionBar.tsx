"use client";

import { X } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui";

/** Floating bulk-action bar, shown once one or more rows are selected. */
export function SelectionBar({
  label,
  count,
  onClear,
  children,
}: {
  /** Names the region for screen readers, such as "Selected companies". */
  label: string;
  count: number;
  onClear: () => void;
  children: ReactNode;
}) {
  if (count === 0) return null;
  return (
    <div
      role="region"
      aria-label={label}
      className="fixed inset-x-4 bottom-6 z-40 mx-auto flex w-fit max-w-[calc(100vw-2rem)] flex-wrap items-center gap-2 bg-foreground py-2 pr-2 pl-4 text-background shadow-lg"
    >
      <span className="mr-2 text-sm font-medium tabular-nums">
        {count} selected
      </span>
      {children}
      <Button
        variant="ghost"
        size="icon-sm"
        onClick={onClear}
        aria-label="Clear selection"
        className="draw-underline rounded-none hover:bg-transparent hover:text-background"
      >
        <X />
      </Button>
    </div>
  );
}

/** A quiet action inside the selection bar. */
export function SelectionAction({
  onClick,
  disabled,
  children,
}: {
  onClick: () => void;
  disabled?: boolean;
  children: ReactNode;
}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={onClick}
      disabled={disabled}
      className="draw-underline rounded-none hover:bg-transparent hover:text-background"
    >
      {children}
    </Button>
  );
}
