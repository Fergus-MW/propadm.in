/** Catch-all route segments retain URL escaping during client navigation. */
export function decodeRouteSegment(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}
