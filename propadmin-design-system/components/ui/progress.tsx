"use client";

import { Progress as ProgressPrimitive } from "radix-ui";
import * as React from "react";

import { cn } from "@/lib/utils";

function Progress({
  className,
  value,
  active = false,
  ...props
}: React.ComponentProps<typeof ProgressPrimitive.Root> & {
  /** Work is still under way: the fill shimmers all the time, not just on hover. */
  active?: boolean;
}) {
  return (
    <ProgressPrimitive.Root
      data-slot="progress"
      className={cn("relative h-2 w-full overflow-hidden bg-muted", className)}
      value={value}
      {...props}
    >
      <ProgressPrimitive.Indicator
        data-slot="progress-indicator"
        data-active={active || undefined}
        className="shimmer-fill h-full w-full flex-1 bg-foreground transition-all"
        style={{ transform: `translateX(-${100 - (value ?? 0)}%)` }}
      />
    </ProgressPrimitive.Root>
  );
}

export { Progress };
