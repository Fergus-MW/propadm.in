import type { ComponentProps, ReactElement } from "react";

import { cn } from "@/lib/utils";

/**
 * Status tones. The neutral names (default, secondary, outline, ghost, link) are
 * plain text; they are kept so any Badge variant can be passed straight through.
 */
export type StatusTextVariant =
  | "default"
  | "secondary"
  | "outline"
  | "ghost"
  | "link"
  | "success"
  | "warning"
  | "error"
  | "destructive"
  | "info"
  | "brand";

const UNDERLINE: Partial<Record<StatusTextVariant, string>> = {
  success: "underline decoration-success",
  warning: "underline decoration-warning",
  error: "underline decoration-destructive",
  destructive: "underline decoration-destructive",
  info: "underline decoration-info",
  brand: "underline decoration-brand",
};

/** The classes for a status: the surrounding text colour, the tone on the underline. */
export function statusTextClass(
  variant: StatusTextVariant = "default",
): string {
  return cn(
    "whitespace-nowrap decoration-2 underline-offset-4",
    UNDERLINE[variant],
  );
}

/**
 * A status in the surrounding text colour; only its underline carries the tone.
 * Neutral variants are plain text.
 */
export function StatusText({
  variant = "default",
  className,
  ...props
}: ComponentProps<"span"> & { variant?: StatusTextVariant }): ReactElement {
  return (
    <span
      data-variant={variant}
      className={cn(statusTextClass(variant), className)}
      {...props}
    />
  );
}
