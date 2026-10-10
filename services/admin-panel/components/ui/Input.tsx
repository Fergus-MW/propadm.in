import * as React from "react";

import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "file:text-foreground placeholder:text-placeholder selection:bg-primary selection:text-primary-foreground border-foreground flex h-9 w-full min-w-0 border-0 border-l-4 bg-transparent px-3 py-1 text-base transition-[color,box-shadow] outline-none file:inline-flex file:h-7 file:border-0 file:bg-transparent file:text-sm file:font-medium disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
        "focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]",
        "aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
        className,
      )}
      {...props}
    />
  );
}

interface FormInputProps extends React.ComponentProps<"input"> {
  label?: string;
  error?: string;
}

function FormInput({ label, error, className, id, ...props }: FormInputProps) {
  const generatedId = React.useId();
  const inputId = id ?? generatedId;

  return (
    <div className="w-full space-y-1.5">
      {label && <Label htmlFor={inputId}>{label}</Label>}
      <Input
        id={inputId}
        className={cn(
          error && "border-destructive focus-visible:ring-destructive/20",
          className,
        )}
        aria-invalid={!!error}
        {...props}
      />
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}

interface FormTextareaProps extends React.ComponentProps<"textarea"> {
  label?: string;
  error?: string;
}

function FormTextarea({
  label,
  error,
  className,
  id,
  ...props
}: FormTextareaProps) {
  const generatedId = React.useId();
  const textareaId = id ?? generatedId;

  return (
    <div className="w-full space-y-1.5">
      {label && <Label htmlFor={textareaId}>{label}</Label>}
      <Textarea
        id={textareaId}
        className={cn(
          error && "border-destructive focus-visible:ring-destructive/20",
          className,
        )}
        aria-invalid={!!error}
        {...props}
      />
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}

interface FormSelectProps extends React.ComponentProps<"select"> {
  label?: string;
  error?: string;
  options: { value: string; label: string }[];
}

function FormSelect({
  label,
  error,
  options,
  className,
  id,
  ...props
}: FormSelectProps) {
  const generatedId = React.useId();
  const selectId = id ?? generatedId;

  return (
    <div className="w-full space-y-1.5">
      {label && <Label htmlFor={selectId}>{label}</Label>}
      <select
        id={selectId}
        className={cn(
          "border-foreground placeholder:text-placeholder focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive flex h-9 w-full border-0 border-l-4 bg-transparent px-3 py-1 text-base transition-[color,box-shadow] outline-none focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
          error && "border-destructive focus-visible:ring-destructive/20",
          className,
        )}
        aria-invalid={!!error}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}

export { FormInput, FormSelect, FormTextarea, Input };
