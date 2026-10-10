import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import * as React from "react";

import { cn } from "@/lib/utils";

// One filled action per step, in the text colour; every other action is text
// with the drawn hover line (design guide, "No grey fills"). So `brand` and
// `destructive` are ink like `default`, and `outline`, `secondary`, `ghost` and
// `link` are all the same text action: no border, fill, shadow or grey hover.
const FILLED =
  "bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50";
// A disabled text action fades its words, not its icon.
const TEXT =
  "draw-underline bg-transparent shadow-none hover:bg-transparent disabled:text-placeholder disabled:[&_svg]:text-foreground";
const TEXT_VARIANTS = ["outline", "secondary", "ghost", "link"] as const;
const TEXT_SIZES = ["default", "xs", "sm", "lg"] as const;

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-all disabled:pointer-events-none [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive",
  {
    variants: {
      variant: {
        default: FILLED,
        brand: FILLED,
        destructive: FILLED,
        outline: TEXT,
        secondary: TEXT,
        ghost: TEXT,
        link: TEXT,
      },
      size: {
        default: "h-9 px-4 py-2 has-[>svg]:px-3",
        xs: "h-6 gap-1 px-2 text-xs has-[>svg]:px-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 gap-1.5 px-3 has-[>svg]:px-2.5",
        lg: "h-10 px-6 has-[>svg]:px-4",
        icon: "size-9",
        "icon-xs": "size-6 [&_svg:not([class*='size-'])]:size-3",
        "icon-sm": "size-8",
        "icon-lg": "size-10",
      },
    },
    // A text action sits on the text, not in a padded box, so its line runs
    // exactly under the label.
    compoundVariants: [
      {
        variant: [...TEXT_VARIANTS],
        size: [...TEXT_SIZES],
        className: "h-auto px-0 py-0 has-[>svg]:px-0",
      },
    ],
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  loading = false,
  children,
  disabled,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
    loading?: boolean;
  }) {
  const Comp = asChild ? Slot.Root : "button";
  // Work in progress shimmers across a filled button; no spinner.
  const filled =
    variant === "default" || variant === "brand" || variant === "destructive";

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(
        buttonVariants({ variant, size }),
        loading && filled && "shimmer-fill",
        className,
      )}
      data-active={loading && filled ? "" : undefined}
      aria-busy={loading || undefined}
      disabled={disabled || loading}
      {...props}
    >
      {children}
    </Comp>
  );
}

export { Button, buttonVariants };
