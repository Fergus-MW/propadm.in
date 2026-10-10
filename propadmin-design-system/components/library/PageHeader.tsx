"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * A page's header. The breadcrumb already names the page, so the title is for
 * screen readers only; what shows is the page's actions and its section tabs.
 */
export function PageHeader({
  title,
  actions,
  tabs,
}: {
  title: string;
  actions?: ReactNode;
  tabs?: ReactNode;
}) {
  if (!actions && !tabs) return <h1 className="sr-only">{title}</h1>;
  return (
    <header className="flex min-h-9 flex-wrap items-center justify-between gap-4">
      <h1 className="sr-only">{title}</h1>
      {tabs ?? <span />}
      {actions ? (
        <div className="flex flex-wrap items-center gap-4">{actions}</div>
      ) : null}
    </header>
  );
}

/** A back link to where the user came from, then the page's own heading. */
export function SubpageHeader({
  backHref,
  backLabel,
  title,
  meta,
  actions,
  alignActions = "end",
}: {
  backHref: string;
  backLabel: string;
  title: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
  /** "start" sits the actions level with the title rather than the last line. */
  alignActions?: "start" | "end";
}) {
  return (
    <header className="flex flex-col gap-3">
      <Link
        href={backHref}
        className="draw-underline inline-flex w-fit items-center gap-1.5 text-sm font-medium outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
      >
        <ArrowLeft className="size-4" aria-hidden />
        {backLabel}
      </Link>
      <div
        className={cn(
          "flex flex-wrap justify-between gap-4",
          alignActions === "start" ? "items-start" : "items-end",
        )}
      >
        {/* basis-80: long meta wraps beside the actions instead of pushing them below. */}
        <div className="flex min-w-0 flex-1 basis-80 flex-col gap-2">
          <h1 className="text-3xl font-semibold tracking-tight break-words">
            {title}
          </h1>
          {meta}
        </div>
        {actions ? (
          <div className="flex flex-wrap items-center gap-4">{actions}</div>
        ) : null}
      </div>
    </header>
  );
}
