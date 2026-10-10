"use client";

import { type LucideIcon, MoreHorizontal } from "lucide-react";
import Link from "next/link";
import { createContext, useContext } from "react";

import { Button } from "@/components/ui/Button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

export interface RowMenuItem {
  label: string;
  /** Either an action or a link (`href`). */
  onSelect?: () => void;
  href?: string;
  icon?: LucideIcon;
  /** Red, listed last after a separator; the caller confirms in a dialog that names the thing. */
  destructive?: boolean;
  disabled?: boolean;
  /** Why the item is disabled, shown on hover. */
  disabledReason?: string;
}

/** Lets a table open a row's menu from the keyboard; without it the menu manages its own open state. */
export const RowMenuControl = createContext<{
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Moves focus elsewhere as the menu closes, and says whether it did; otherwise focus returns to the trigger. */
  returnFocus: () => boolean;
} | null>(null);

/** Never lists Open: the row click opens the thing. */
export function RowMenu({
  label,
  items,
}: {
  /** The row's name, so the button reads "More actions for Acme". */
  label: string;
  items: readonly RowMenuItem[];
}) {
  const control = useContext(RowMenuControl);
  const regular = items.filter((item) => !item.destructive);
  const destructive = items.filter((item) => item.destructive);
  const render = (item: RowMenuItem) => (
    <DropdownMenuItem
      key={item.label}
      disabled={item.disabled}
      title={item.disabled ? item.disabledReason : undefined}
      onSelect={item.onSelect}
      asChild={item.href !== undefined}
      className={cn("gap-2", item.destructive && "text-destructive")}
    >
      {item.href !== undefined ? (
        <Link href={item.href}>
          {item.icon ? <item.icon className="size-4" /> : null}
          {item.label}
        </Link>
      ) : (
        <>
          {item.icon ? <item.icon className="size-4" /> : null}
          {item.label}
        </>
      )}
    </DropdownMenuItem>
  );

  return (
    <DropdownMenu open={control?.open} onOpenChange={control?.onOpenChange}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={`More actions for ${label}`}
          onClick={(event) => event.stopPropagation()}
          onKeyDown={(event) => event.stopPropagation()}
          className="ml-auto size-7 aria-expanded:after:[transform:scaleX(1)]"
        >
          <MoreHorizontal />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="min-w-48"
        // Portal events still bubble through the row's React tree.
        onClick={(event) => event.stopPropagation()}
        onKeyDown={(event) => event.stopPropagation()}
        onCloseAutoFocus={(event) => {
          if (control?.returnFocus()) event.preventDefault();
        }}
      >
        {regular.map(render)}
        {regular.length > 0 && destructive.length > 0 ? (
          <DropdownMenuSeparator />
        ) : null}
        {destructive.map(render)}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
