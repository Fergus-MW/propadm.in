"use client";
// Adapted from AI Elements (vercel/ai-elements) Message: markdown via Streamdown, no plugins.
import type { HTMLAttributes } from "react";
import { memo } from "react";
import { Markdown } from "@/components/markdown";
import { cn } from "@/lib/utils";

export const Message = ({
  className,
  from,
  ...props
}: HTMLAttributes<HTMLDivElement> & { from: "user" | "assistant" }) => (
  <div
    className={cn(
      "group flex w-full max-w-[95%] flex-col gap-2",
      from === "user" ? "is-user ml-auto justify-end" : "is-assistant",
      className,
    )}
    {...props}
  />
);

export const MessageContent = ({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex w-fit min-w-0 max-w-full flex-col gap-2 overflow-hidden text-sm leading-6",
      "group-[.is-user]:ml-auto group-[.is-user]:bg-muted group-[.is-user]:px-4 group-[.is-user]:py-3 group-[.is-user]:whitespace-pre-wrap",
      className,
    )}
    {...props}
  />
);

export const MessageResponse = memo(
  Markdown,
  (previous, next) => previous.children === next.children,
);
MessageResponse.displayName = "MessageResponse";
