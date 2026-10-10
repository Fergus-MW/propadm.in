import type { ReactNode } from "react";

/** One line and at most one action. It does not explain why it is empty. */
export function EmptyState({
  message,
  action,
}: {
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 py-6 text-sm">
      <p>{message}</p>
      {action}
    </div>
  );
}
