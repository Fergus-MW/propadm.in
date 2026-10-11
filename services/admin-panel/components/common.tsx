"use client";
import type { ReactNode } from "react";
import { Button } from "./ui/Button";
import { StatusText } from "./library/StatusText";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./ui/Table";
import { EmptyState } from "./library/EmptyState";
import { str, type RecordData } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
export function Header({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <h1>{title}</h1>
      <div className="actions">{children}</div>
    </header>
  );
}
export function State({
  pending,
  error,
  retry,
}: {
  pending?: boolean;
  error?: Error | null;
  retry?: () => void;
}) {
  if (pending)
    return (
      <div className="loading" aria-live="polite">
        <div className="shimmer-fill" data-active="" />
        Loading…
      </div>
    );
  if (error)
    return (
      <div className="notice" role="alert">
        <StatusText variant="error">{error.message}</StatusText>
        {retry && (
          <Button variant="ghost" onClick={retry}>
            Retry
          </Button>
        )}
      </div>
    );
  return null;
}
export function Status({ value }: { value: unknown }) {
  const label = str(value);
  const tone =
    /complete|done|approved|active|sent|success|cleared|reconciled|preferred|valid/.test(
      label,
    )
      ? "success"
      : /fail|error|cancel|reject|expired|suspended|do_not_use/.test(label)
        ? "error"
        : /sleep|pending|queued|review|expiring|rechecking/.test(label)
          ? "warning"
          : "info";
  return <StatusText variant={tone}>{label.replaceAll("_", " ")}</StatusText>;
}
export function Records({
  items,
  columns,
}: {
  items: RecordData[];
  columns: {
    title: string;
    key: string;
    render?: (row: RecordData) => ReactNode;
  }[];
}) {
  if (!items.length) return <EmptyState message="No records yet." />;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((c) => (
            <TableHead key={c.key}>{c.title}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item, index) => (
          <TableRow
            key={
              item.id ??
              `${str(item.entity_id ?? item.name ?? "record")}-${index}`
            }
          >
            {columns.map((c) => (
              <TableCell key={c.key}>
                {c.render ? c.render(item) : str(item[c.key])}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
export function Json({ value }: { value: unknown }) {
  return <pre className="code">{JSON.stringify(value, null, 2)}</pre>;
}
export function Confirm({
  title,
  children,
  onConfirm,
  onClose,
  pending,
  disabled,
}: {
  title: string;
  children: ReactNode;
  onConfirm: () => void;
  onClose: () => void;
  pending?: boolean;
  disabled?: boolean;
}) {
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {/* Callers pass form controls, which are invalid inside the default <p>. */}
          <DialogDescription asChild>
            <div>{children}</div>
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="ghost" onClick={onClose}>
            Keep
          </Button>
          <Button loading={pending} disabled={disabled} onClick={onConfirm}>
            Confirm
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
export function Section({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}
