/**
 * Whether a link is the current page: the exact path, or (with `prefix`) any
 * page below it. "/files" does not match "/filesystem".
 */
export function isPathActive(
  pathname: string,
  href: string,
  { prefix = false }: { prefix?: boolean } = {},
): boolean {
  if (pathname === href) return true;
  return prefix && pathname.startsWith(href.endsWith("/") ? href : `${href}/`);
}
