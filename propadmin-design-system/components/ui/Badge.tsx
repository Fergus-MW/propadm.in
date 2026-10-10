import { Slot } from "radix-ui";
import * as React from "react";

import {
  statusTextClass,
  type StatusTextVariant,
} from "@/components/library/StatusText";
import { cn } from "@/lib/utils";

/**
 * A status or label. Status colour is an underline, never a fill (design guide):
 * success, warning, error, info and brand underline the text in that tone; the
 * neutral variants are plain text. Prefer StatusText in new code.
 */
function Badge({
  className,
  variant = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"span"> & {
  variant?: StatusTextVariant | null;
  asChild?: boolean;
}) {
  const Comp = asChild ? Slot.Root : "span";
  const tone = variant ?? "default";

  return (
    <Comp
      data-slot="badge"
      data-variant={tone}
      className={cn(
        "inline-flex w-fit shrink-0 items-center gap-1 text-xs font-medium [&>svg]:pointer-events-none [&>svg]:size-3",
        statusTextClass(tone),
        className,
      )}
      {...props}
    />
  );
}

/** A file's processing status. */
function StatusBadge({ status }: { status: string }) {
  const variant: StatusTextVariant =
    status === "processed"
      ? "success"
      : status === "processing"
        ? "info"
        : status === "failed"
          ? "error"
          : "default";

  return <Badge variant={variant}>{status}</Badge>;
}

export { Badge, StatusBadge };
