"use client";

import type { ReactNode } from "react";
import { useId } from "react";

import { Checkbox, Label, RadioGroupItem } from "@/components/ui";
import { cn } from "@/lib/utils";

import { LEFT_RULE_CLASS } from "./styles";

/**
 * A list of options under one left rule: the list gets the rule, not each row.
 * Put OptionRows (checkboxes) or a RadioGroup of RadioRows inside.
 */
export function OptionList({
  children,
  className,
  label,
}: {
  children: ReactNode;
  className?: string;
  /** Names the group for screen readers. */
  label?: string;
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className={cn(LEFT_RULE_CLASS, "flex flex-col pl-3", className)}
    >
      {children}
    </div>
  );
}

/** A checkbox option: label, an optional one-line detail, the drawn line on hover. */
export function OptionRow({
  label,
  ariaLabel,
  detail,
  checked,
  onCheckedChange,
  disabled = false,
}: {
  label: ReactNode;
  ariaLabel?: string;
  detail?: ReactNode;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <div className="group draw-underline flex items-start gap-3 py-2">
      <Checkbox
        id={id}
        aria-label={ariaLabel}
        checked={checked}
        disabled={disabled}
        onCheckedChange={(value) => onCheckedChange(value === true)}
        className="mt-0.5"
      />
      <Label
        htmlFor={id}
        className="flex min-w-0 flex-col items-start gap-0.5 text-sm font-medium group-has-disabled:text-placeholder"
      >
        {label}
        {detail ? <span className="text-xs font-normal">{detail}</span> : null}
      </Label>
    </div>
  );
}

/** A radio option for use inside a RadioGroup. */
export function RadioRow({
  value,
  label,
  detail,
  disabled = false,
}: {
  value: string;
  label: ReactNode;
  detail?: ReactNode;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <div className="group draw-underline flex items-start gap-3 py-2">
      <RadioGroupItem
        id={id}
        value={value}
        disabled={disabled}
        className="mt-0.5"
      />
      <Label
        htmlFor={id}
        className="flex min-w-0 flex-col items-start gap-0.5 text-sm font-medium group-has-disabled:text-placeholder"
      >
        {label}
        {detail ? <span className="text-xs font-normal">{detail}</span> : null}
      </Label>
    </div>
  );
}
