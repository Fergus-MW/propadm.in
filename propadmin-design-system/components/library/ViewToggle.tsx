import { Checkbox, Label } from "@/components/ui";

/** A labelled checkbox that switches a view or an optional column on or off. */
export function ViewToggle({
  id,
  label,
  title,
  checked,
  onChange,
  disabled = false,
}: {
  id: string;
  label: string;
  title?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-center gap-2" title={title}>
      <Checkbox
        id={id}
        checked={checked}
        disabled={disabled}
        onCheckedChange={(value) => onChange(value === true)}
      />
      <Label
        htmlFor={id}
        className={
          disabled
            ? "text-sm font-normal text-placeholder"
            : "text-sm font-normal"
        }
      >
        {label}
      </Label>
    </div>
  );
}
