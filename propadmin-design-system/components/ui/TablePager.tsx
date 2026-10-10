"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import type { ReactElement } from "react";

import { Button } from "@/components/ui/Button";
import { pagerRange } from "@/components/ui/pagerRange";
import { cn } from "@/lib/utils";

interface TablePagerProps {
  /** 1-indexed, matching the API. */
  page: number;
  pages: number;
  /** Rows across every page, not just this one. */
  total: number;
  /** The requested page size — the stride between pages, not this page's length. */
  pageSize: number;
  /** Rows actually rendered, so the range ends correctly on a short last page. */
  itemsOnPage: number;
  onPageChange: (page: number) => void;
  /** Plural noun for the count, e.g. "companies". */
  noun?: string;
  className?: string;
}

/**
 * Page controls and, always, the count.
 *
 * The count is not decoration and is rendered even for a single page. A paginated table
 * whose caller forgot to page is indistinguishable from a complete one — the lead-scoring
 * Rank and Screen tabs silently showed 20 of 38 companies for exactly that reason, while
 * the funnel above them described all 38. Stating "showing 1–20 of 38" makes that class of
 * bug visible on the screen instead of only in the network tab.
 */
export function TablePager({
  page,
  pages,
  total,
  pageSize,
  itemsOnPage,
  onPageChange,
  noun = "rows",
  className,
}: TablePagerProps): ReactElement {
  const { first, last } = pagerRange({ page, pageSize, itemsOnPage, total });
  const showControls = pages > 1;

  return (
    <div
      className={cn(
        "flex flex-wrap items-center justify-between gap-3 pt-3",
        className,
      )}
    >
      {/* Polite rather than assertive: a page change is a navigation the user just asked
          for, so it should be announced without interrupting anything else. */}
      <p className="text-xs text-muted-foreground" aria-live="polite">
        {last === 0
          ? `No ${noun}`
          : `Showing ${first}–${last} of ${total} ${noun}`}
      </p>
      {showControls && (
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
          >
            <ChevronLeft aria-hidden="true" />
            Previous
          </Button>
          <span className="text-xs tabular-nums text-muted-foreground">
            Page {page} of {pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= pages}
          >
            Next
            <ChevronRight aria-hidden="true" />
          </Button>
        </div>
      )}
    </div>
  );
}
