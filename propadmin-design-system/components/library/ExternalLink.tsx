import { ExternalLink as ExternalLinkIcon } from "lucide-react";
import type { ReactNode } from "react";

import { getSafeHttpUrl } from "@/lib/utils";
import { cn } from "@/lib/utils";

/**
 * A link that opens in a new tab: link colour, the drawn line under the text,
 * a small external mark. An unsafe or missing URL renders the text alone.
 */
export function ExternalLink({
  href,
  children,
  className,
}: {
  href: string | null | undefined;
  children: ReactNode;
  className?: string;
}) {
  const url = getSafeHttpUrl(href ?? "");
  if (!url) return <span className={className}>{children}</span>;
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "group inline-flex items-baseline gap-1 text-brand outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50",
        className,
      )}
    >
      <span className="draw-underline">{children}</span>
      <ExternalLinkIcon className="size-3 self-center" aria-hidden />
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}
