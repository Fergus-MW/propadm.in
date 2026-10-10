"use client";

import { ListFilter, X } from "lucide-react";

import { Button, Input } from "@/components/ui";
import { cn } from "@/lib/utils";

import { ICON_ACTION_CLASS } from "./styles";

/** A search field: the left rule, filter lines rather than a magnifier, a clear action. */
export function SearchInput({
  value,
  onChange,
  placeholder = "Search",
  label,
  disabled = false,
  className,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  /** Names the field for screen readers, such as "Search files". */
  label: string;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <div className={cn("relative w-full max-w-sm", className)}>
      <ListFilter
        className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2"
        aria-hidden
      />
      <Input
        type="search"
        aria-label={label}
        placeholder={placeholder}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className="pr-9 pl-9 [&::-webkit-search-cancel-button]:hidden"
      />
      {value && !disabled ? (
        <Button
          type="button"
          variant="ghost"
          size="icon-xs"
          aria-label="Clear search"
          onClick={() => onChange("")}
          className={cn(
            ICON_ACTION_CLASS,
            "absolute top-1/2 right-2 -translate-y-1/2",
          )}
        >
          <X />
        </Button>
      ) : null}
    </div>
  );
}
