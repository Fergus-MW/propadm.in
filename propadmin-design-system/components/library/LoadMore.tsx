"use client";

import { Button, Skeleton } from "@/components/ui";

import { TEXT_ACTION_CLASS } from "./styles";

/** Loads the next page of a list, with a thin skeleton while it loads. */
export function LoadMore({
  hasMore,
  isFetching,
  isError,
  onLoadMore,
  label,
  errorText,
}: {
  hasMore: boolean;
  isFetching: boolean;
  isError: boolean;
  onLoadMore: () => void;
  /** A verb, such as "Load older runs". */
  label: string;
  errorText: string;
}) {
  if (!hasMore && !isError) return null;
  return (
    <div className="space-y-1">
      <Button
        size="sm"
        variant="ghost"
        className={TEXT_ACTION_CLASS}
        disabled={isFetching}
        onClick={onLoadMore}
      >
        {label}
      </Button>
      {isFetching ? <Skeleton className="h-1 w-full" /> : null}
      {isError ? (
        <p role="alert" className="text-xs text-destructive">
          {errorText}
        </p>
      ) : null}
    </div>
  );
}
