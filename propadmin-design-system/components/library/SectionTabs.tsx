"use client";

import { CornerDownRight } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { StatusText } from "./StatusText";

export interface SectionTab {
  href: string;
  label: string;
  /** Shown only when it asks for action (design guide 4.1). */
  count?: number | null;
  /** Paths below `href` that should also mark this tab active. */
  matchPrefix?: boolean;
  /** Sub-sections, drawn nested right after this tab. */
  children?: readonly SectionTab[];
}

export function isSectionTabActive(pathname: string, tab: SectionTab): boolean {
  if (pathname === tab.href) return true;
  return tab.matchPrefix === true && pathname.startsWith(`${tab.href}/`);
}

function TabLink({
  tab,
  pathname,
  nested = false,
}: {
  tab: SectionTab;
  pathname: string;
  nested?: boolean;
}) {
  const active = isSectionTabActive(pathname, tab);
  return (
    <Link
      href={tab.href}
      aria-current={active ? "page" : undefined}
      // No fill: the hover line is drawn under the label, and stays
      // drawn under the current section's.
      className="group flex h-9 items-center gap-2 px-3 text-sm sm:px-4 font-medium whitespace-nowrap outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
    >
      {nested ? <CornerDownRight aria-hidden className="size-3.5" /> : null}
      <span className="draw-underline group-aria-[current=page]:after:[transform:scaleX(1)]">
        {tab.label}
      </span>
      {tab.count ? (
        <StatusText variant="warning" className="tabular-nums">
          {tab.count}
        </StatusText>
      ) : null}
    </Link>
  );
}

/** Tabs that switch between the main jobs of a feature. Links, not local state. */
export function SectionTabs({
  label,
  tabs,
}: {
  /** Names the navigation for screen readers, such as "Lead scoring sections". */
  label: string;
  tabs: readonly SectionTab[];
}) {
  const pathname = usePathname() ?? "";
  return (
    <nav
      aria-label={label}
      className="-mx-1 overflow-x-auto [scrollbar-width:none]"
    >
      <ul className="flex w-max gap-1">
        {tabs.map((tab) => (
          <li key={tab.href} className="flex">
            <TabLink tab={tab} pathname={pathname} />
            {tab.children?.length ? (
              <ul className="flex">
                {tab.children.map((child) => (
                  <li key={child.href}>
                    <TabLink tab={child} pathname={pathname} nested />
                  </li>
                ))}
              </ul>
            ) : null}
          </li>
        ))}
      </ul>
    </nav>
  );
}
