interface PagerRangeInput {
  /** 1-indexed, matching the API. */
  page: number;
  /** The requested page size: the stride between pages. */
  pageSize: number;
  /** Rows actually rendered on this page. */
  itemsOnPage: number;
  /** Rows across every page. */
  total: number;
}

export interface PagerRange {
  /** 1-indexed position of the first rendered row, or 0 when there are none. */
  first: number;
  /** 1-indexed position of the last rendered row, or 0 when there are none. */
  last: number;
}

/**
 * Which rows of the whole result set this page is showing.
 *
 * Extracted and tested because the arithmetic has one trap: the stride between pages is the
 * requested `pageSize`, but the range must *end* at what actually rendered. Using the
 * rendered count for both makes every page after the first wrong as soon as a last page is
 * short — 38 rows at 20 per page would report "showing 19–36 of 38" on page 2.
 */
export function pagerRange({
  page,
  pageSize,
  itemsOnPage,
  total,
}: PagerRangeInput): PagerRange {
  if (total === 0 || itemsOnPage === 0) return { first: 0, last: 0 };
  const first = (page - 1) * pageSize + 1;
  return { first, last: first + itemsOnPage - 1 };
}
