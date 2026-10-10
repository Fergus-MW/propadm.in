"use client";

import { Tabs as TabsPrimitive } from "radix-ui";
import * as React from "react";

import { cn } from "@/lib/utils";

function Tabs({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Root>) {
  return (
    <TabsPrimitive.Root
      data-slot="tabs"
      className={cn("flex flex-col gap-2", className)}
      {...props}
    />
  );
}

/** Tabs are plain labels, for switching views within a page: no pill, no fill. */
function TabsList({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <div className="-mx-1 overflow-x-auto px-1 [scrollbar-width:none]">
      <TabsPrimitive.List
        data-slot="tabs-list"
        className={cn("flex w-max items-center gap-1", className)}
        {...props}
      />
    </div>
  );
}

/** A tab label with the drawn hover line, kept drawn under the current tab. */
function TabsTrigger({
  className,
  children,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      data-slot="tabs-trigger"
      className={cn(
        "group inline-flex h-9 items-center gap-1.5 whitespace-nowrap px-3 text-sm font-medium sm:px-4",
        "focus-visible:ring-ring/50 focus-visible:outline-none focus-visible:ring-[3px]",
        "disabled:pointer-events-none disabled:text-placeholder",
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        className,
      )}
      {...props}
    >
      <span className="draw-underline group-data-[state=active]:after:[transform:scaleX(1)]">
        {children}
      </span>
    </TabsPrimitive.Trigger>
  );
}

function TabsContent({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Content>) {
  return (
    <TabsPrimitive.Content
      data-slot="tabs-content"
      className={cn("flex-1 outline-none", className)}
      {...props}
    />
  );
}

export { Tabs, TabsContent, TabsList, TabsTrigger };
