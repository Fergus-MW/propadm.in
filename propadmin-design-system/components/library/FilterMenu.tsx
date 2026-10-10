"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";

import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
  Input,
} from "@/components/ui";
import { cn } from "@/lib/utils";

import { MENU_TRIGGER_CLASS } from "./styles";

export interface FilterOption {
  value: string;
  label: string;
}

/**
 * One filter in a table's filter row: a text trigger naming the current choice,
 * its line kept drawn while the menu is open or a choice other than "all" is
 * set. `searchable` adds a field for long option lists.
 */
export function FilterMenu({
  label,
  value,
  options,
  onChange,
  allLabel,
  searchable = false,
}: {
  /** What is being filtered, such as "Status". */
  label: string;
  /** The chosen value, or null for every option. */
  value: string | null;
  options: readonly FilterOption[];
  onChange: (value: string | null) => void;
  /** The "every option" choice, such as "Any status". */
  allLabel: string;
  searchable?: boolean;
}) {
  const [query, setQuery] = useState("");
  const chosen = options.find((option) => option.value === value);
  const shown = query
    ? options.filter((option) =>
        option.label.toLowerCase().includes(query.toLowerCase()),
      )
    : options;
  return (
    <DropdownMenu onOpenChange={(open) => !open && setQuery("")}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          aria-label={`${label}: ${chosen?.label ?? allLabel}`}
          aria-pressed={value !== null}
          className={cn(
            MENU_TRIGGER_CLASS,
            "aria-pressed:after:[transform:scaleX(1)]",
          )}
        >
          {chosen?.label ?? allLabel}
          <ChevronDown aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="max-h-80 min-w-48">
        {searchable ? (
          <div className="p-1">
            <Input
              aria-label={`Find a ${label.toLowerCase()}`}
              placeholder="Find"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => event.stopPropagation()}
            />
          </div>
        ) : null}
        <DropdownMenuRadioGroup
          value={value ?? ""}
          onValueChange={(next) => onChange(next === "" ? null : next)}
        >
          <DropdownMenuRadioItem value="">{allLabel}</DropdownMenuRadioItem>
          {shown.map((option) => (
            <DropdownMenuRadioItem key={option.value} value={option.value}>
              {option.label}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
