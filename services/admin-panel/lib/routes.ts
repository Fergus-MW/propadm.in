/** Catch-all route segments retain URL escaping during client navigation. */
export function decodeRouteSegment(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

/** Breadcrumb label: the matching nav item, else the route's own last segment. */
export function sectionLabel(pathname: string, items: { href: string; label: string }[]) {
  const item = items.find((i) => i.href !== "/" && pathname.startsWith(i.href));
  if (item) return item.label;
  const segment = pathname.split("/").filter(Boolean).at(-1);
  if (!segment) return "Today";
  const words = decodeURIComponent(segment).replace(/[-_]+/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}
