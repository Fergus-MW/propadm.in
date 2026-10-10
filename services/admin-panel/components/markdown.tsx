"use client";
import remarkBreaks from "remark-breaks";
import { Streamdown, defaultRemarkPlugins } from "streamdown";
import { cn } from "@/lib/utils";

// Single newlines stay line breaks, matching the HTML the email service sends.
const remarkPlugins = [...Object.values(defaultRemarkPlugins), remarkBreaks];

/** Agent-written Markdown (chat replies, ticket completions, sent emails). */
export function Markdown({
  children,
  className,
}: {
  children: string;
  className?: string;
}) {
  return (
    <Streamdown
      mode="static"
      remarkPlugins={remarkPlugins}
      className={cn(
        "markdown size-full min-w-0 [&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
        className,
      )}
    >
      {children}
    </Streamdown>
  );
}
