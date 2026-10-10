import { DateTime, Interval } from "luxon";

/**
 * Centralized date formatting utilities using Luxon.
 *
 * All functions accept ISO date strings or null/undefined values
 * and handle them gracefully.
 */

/**
 * Format a date with a Luxon format string.
 * Returns "-" for null/undefined/invalid dates.
 *
 * Common formats:
 * - "LLL d, yyyy" -> "Jan 2, 2025" (date only)
 * - "LLL d, h:mm a" -> "Jan 2, 3:45 PM" (short with time)
 * - "LLL d, yyyy, h:mm a" -> "Jan 2, 2025, 3:45 PM" (full)
 */
export function formatDate(
  dateStr: string | null | undefined,
  format: string = "LLL d, yyyy",
): string {
  if (!dateStr) return "-";
  const dt = DateTime.fromISO(dateStr);
  return dt.isValid ? dt.toFormat(format) : "-";
}

/**
 * Format a date as a relative time string.
 * Examples: "2 minutes ago", "3 hours ago", "5 days ago"
 */
export function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  const dt = DateTime.fromISO(dateStr);
  if (!dt.isValid) return "";

  return dt.toRelative() ?? "";
}

/**
 * Get elapsed duration in seconds between start and end timestamps.
 * If completedAt is null, uses current time.
 */
export function getDurationSeconds(
  startedAt: string | null | undefined,
  completedAt: string | null | undefined,
): number {
  if (!startedAt) return 0;
  const start = DateTime.fromISO(startedAt);
  if (!start.isValid) return 0;
  const end = completedAt ? DateTime.fromISO(completedAt) : DateTime.now();
  if (!end.isValid) return 0;
  return Math.max(
    0,
    Math.floor(Interval.fromDateTimes(start, end).length("seconds")),
  );
}

/**
 * Format elapsed duration as "Xs", "Xm Ys", or "Xh Ym".
 * If completedAt is null, uses current time.
 */
export function formatDuration(
  startedAt: string | null | undefined,
  completedAt: string | null | undefined,
): string {
  if (!startedAt) return "-";
  const start = DateTime.fromISO(startedAt);
  if (!start.isValid) return "-";
  const end = completedAt ? DateTime.fromISO(completedAt) : DateTime.now();
  if (!end.isValid) return "-";

  const { hours, minutes, seconds } = Interval.fromDateTimes(
    start,
    end,
  ).toDuration(["hours", "minutes", "seconds"]);
  const [h, m, s] = [hours, minutes, seconds].map(Math.floor);

  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

/**
 * Format elapsed duration as "HH:MM:SS".
 * If completedAt is null, uses current time.
 */
export function formatDurationClock(
  startedAt: string | null | undefined,
  completedAt: string | null | undefined,
): string {
  if (!startedAt) return "-";
  const start = DateTime.fromISO(startedAt);
  if (!start.isValid) return "-";
  const end = completedAt ? DateTime.fromISO(completedAt) : DateTime.now();
  if (!end.isValid) return "-";
  return Interval.fromDateTimes(start, end)
    .toDuration(["hours", "minutes", "seconds"])
    .toFormat("hh:mm:ss");
}

/**
 * Format a millisecond duration as human-readable "Xh Ym Zs".
 */
export function formatElapsedMs(ms: number | null | undefined): string {
  if (ms == null || ms < 0) return "-";
  const totalSeconds = Math.floor(ms / 1000);
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}
