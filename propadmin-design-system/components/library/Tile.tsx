import Link from "next/link";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";

import { StatusText } from "./StatusText";

const TILE =
  "group draw-underline flex min-h-28 flex-col gap-2 py-3 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50";

/**
 * A figure that links to where it comes from: label, number, one line of meta.
 * No fill; the drawn line runs along the bottom on hover. `attention` marks the
 * label with the warning underline.
 */
export function Tile({
  label,
  href,
  value,
  unit,
  meta,
  attention = false,
  isLoading = false,
  isError = false,
  onRetry,
}: {
  label: string;
  href: string;
  value: ReactNode;
  unit?: ReactNode;
  meta?: ReactNode;
  attention?: boolean;
  isLoading?: boolean;
  /** No number to show: the tile offers `onRetry` instead of its link. */
  isError?: boolean;
  onRetry?: () => void;
}) {
  const caption = (
    <StatusText
      variant={attention ? "warning" : "default"}
      className="text-xs font-medium"
    >
      {label}
    </StatusText>
  );

  if (isLoading) {
    return (
      <div className={TILE} aria-busy="true">
        {caption}
        <Skeleton className="h-9 w-16" />
        <Skeleton className="h-4 w-40" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className={TILE} role="status">
        {caption}
        <p className="text-sm">Could not load.</p>
        {onRetry ? (
          <Button variant="ghost" onClick={onRetry} className="w-fit">
            Try again
          </Button>
        ) : null}
      </div>
    );
  }

  return (
    <Link href={href} className={TILE}>
      {caption}
      <span className="text-3xl font-semibold tracking-tight tabular-nums">
        {value}
        {unit ? (
          <span className="ml-1 text-sm font-medium tracking-normal">
            {unit}
          </span>
        ) : null}
      </span>
      {meta ? <span className="text-sm">{meta}</span> : null}
    </Link>
  );
}
