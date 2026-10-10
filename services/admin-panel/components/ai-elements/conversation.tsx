"use client";
// Adapted from AI Elements (vercel/ai-elements) Conversation: square, flat, no AI SDK types.
import { ArrowDownIcon } from "lucide-react";
import type { ComponentProps } from "react";
import { StickToBottom, useStickToBottomContext } from "use-stick-to-bottom";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

export const Conversation = ({
  className,
  ...props
}: ComponentProps<typeof StickToBottom>) => (
  <StickToBottom
    className={cn("relative flex-1 overflow-y-hidden", className)}
    initial="smooth"
    resize="smooth"
    role="log"
    {...props}
  />
);

export const ConversationContent = ({
  className,
  ...props
}: ComponentProps<typeof StickToBottom.Content>) => (
  <StickToBottom.Content
    className={cn("mx-auto flex w-full max-w-3xl flex-col gap-8 p-4", className)}
    {...props}
  />
);

export const ConversationEmptyState = ({
  className,
  title,
  description,
  ...props
}: ComponentProps<"div"> & { title: string; description?: string }) => (
  <div
    className={cn(
      "flex size-full flex-col items-center justify-center gap-2 p-8 text-center",
      className,
    )}
    {...props}
  >
    <h2>{title}</h2>
    {description && <p className="caption">{description}</p>}
  </div>
);

export const ConversationScrollButton = () => {
  const { isAtBottom, scrollToBottom } = useStickToBottomContext();
  return isAtBottom ? null : (
    <Button
      className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-background"
      onClick={() => void scrollToBottom()}
      size="icon"
      type="button"
      variant="ghost"
      aria-label="Scroll to latest message"
    >
      <ArrowDownIcon className="size-4" />
    </Button>
  );
};
