/** 1px tolerance: fractional layout heights never reach an exact match. */
export function hasMoreContentBelow(
  scrollTop: number,
  clientHeight: number,
  scrollHeight: number,
): boolean {
  return scrollTop + clientHeight < scrollHeight - 1;
}
