"use client";

import { Check, Copy } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";

import { ICON_ACTION_CLASS, LEFT_RULE_CLASS } from "./styles";

/** Copies text to the clipboard; `copied` is true for two seconds after. */
export function useCopyToClipboard(): {
  copied: boolean;
  copy: (value: string, what?: string) => Promise<void>;
} {
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 2000);
    return () => window.clearTimeout(timer);
  }, [copied]);
  return {
    copied,
    copy: async (value, what = "Copied") => {
      try {
        await navigator.clipboard.writeText(value);
        setCopied(true);
        toast.success(what);
      } catch {
        toast.error("Could not copy. Select the text and copy it instead.");
      }
    },
  };
}

/** A value to copy (a key, a URL): monospace on the left rule, one copy action. */
export function CopyField({
  value,
  label,
  className,
}: {
  value: string;
  /** Names the value, such as "API key"; read by the copy button. */
  label: string;
  className?: string;
}) {
  const { copied, copy } = useCopyToClipboard();
  return (
    <div
      className={cn(
        LEFT_RULE_CLASS,
        "flex items-start justify-between gap-3 py-1 pl-3",
        className,
      )}
    >
      <code className="min-w-0 font-mono text-sm break-all">{value}</code>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label={`Copy ${label}`}
        onClick={() => void copy(value, `${label} copied`)}
        className={cn(ICON_ACTION_CLASS, "shrink-0")}
      >
        {copied ? <Check /> : <Copy />}
      </Button>
    </div>
  );
}
