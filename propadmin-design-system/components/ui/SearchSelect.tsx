"use client";

import { Command } from "cmdk";
import { Check, ChevronsUpDown } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

import { Button } from "./Button";
import { Label } from "./label";

interface SearchSelectOption {
  value: string;
  label: string;
}

interface SearchSelectProps {
  label?: string;
  error?: string;
  value: string;
  onChange: (value: string) => void;
  options: SearchSelectOption[];
  placeholder?: string;
  searchPlaceholder?: string;
  emptyText?: string;
  disabled?: boolean;
}

export function SearchSelect({
  label,
  error,
  value,
  onChange,
  options,
  placeholder = "Select option",
  searchPlaceholder = "Search…",
  emptyText = "No results found.",
  disabled = false,
}: SearchSelectProps) {
  const [open, setOpen] = React.useState(false);
  const selected = options.find((option) => option.value === value);
  const generatedId = React.useId();

  React.useEffect(() => {
    if (disabled) {
      setOpen(false);
    }
  }, [disabled]);

  return (
    <div className="w-full space-y-1.5">
      {label ? <Label htmlFor={generatedId}>{label}</Label> : null}
      <div className="relative">
        <Button
          id={generatedId}
          type="button"
          variant="outline"
          className={cn(
            "w-full justify-between font-normal",
            error ? "border-destructive" : null,
          )}
          aria-expanded={open}
          onClick={() => setOpen((current) => !current)}
          disabled={disabled}
        >
          <span className="truncate text-left">
            {selected?.label || placeholder}
          </span>
          <ChevronsUpDown className="size-4 shrink-0" />
        </Button>
        {open ? (
          <div className="absolute z-50 mt-1 w-full border bg-popover text-popover-foreground">
            <Command className="w-full">
              <Command.Input
                placeholder={searchPlaceholder}
                className="flex h-9 w-full border-b bg-transparent px-3 py-2 text-sm outline-none placeholder:text-placeholder"
              />
              <Command.List className="max-h-64 overflow-y-auto p-1">
                <Command.Empty className="px-3 py-2 text-sm text-muted-foreground">
                  {emptyText}
                </Command.Empty>
                <Command.Group>
                  {options.map((option) => (
                    <Command.Item
                      key={option.value}
                      value={option.label}
                      onSelect={() => {
                        onChange(option.value);
                        setOpen(false);
                      }}
                      className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm outline-none draw-underline data-[selected='true']:after:[transform:scaleX(1)]"
                    >
                      <Check
                        className={cn(
                          "size-4",
                          option.value === value ? "opacity-100" : "opacity-0",
                        )}
                      />
                      <span className="truncate">{option.label}</span>
                    </Command.Item>
                  ))}
                </Command.Group>
              </Command.List>
            </Command>
          </div>
        ) : null}
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
    </div>
  );
}
