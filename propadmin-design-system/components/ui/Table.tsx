import * as React from "react";

import { TablePager } from "@/components/ui/TablePager";
import { cn } from "@/lib/utils";

// No outer box and no header fill: a table sits directly on the canvas and is
// separated from it by whitespace. The only rules are the one under the header
// and the ones between rows, which is what makes a dense grid scannable.
// A sticky header pins to its nearest scrolling box, so with `stickyHeader` the
// container stops being one: the header pins to the page's scroller instead, and
// a table wider than the page scrolls sideways with the page. A sticky element
// stops at the scroller's padding; a layout sets --table-sticky-top to minus that
// padding so the header meets the top edge. The header rule is drawn on the
// cells, because a row border would not move with them.
const STICKY_HEADER_CLASS =
  "overflow-x-visible [&_thead_th]:sticky [&_thead_th]:top-[var(--table-sticky-top,0px)] [&_thead_th]:z-20 [&_thead_th]:bg-background [&_thead_th]:shadow-[inset_0_-1px_0_var(--color-border)]";

/**
 * Two table designs. `standard` (the default) is the list of records, such as
 * scoring runs: roomy rows, one or two lines each. `dense` packs many columns of
 * figures, such as the companies table. Every head and cell takes its size
 * from the table, so a page sets only widths and alignment per column.
 */
export type TableDensity = "standard" | "dense";

function Table({
  className,
  stickyHeader = false,
  density = "standard",
  ...props
}: React.ComponentProps<"table"> & {
  stickyHeader?: boolean;
  density?: TableDensity;
}) {
  return (
    <div
      data-slot="table-container"
      className={cn(
        "relative w-full overflow-x-auto",
        stickyHeader && STICKY_HEADER_CLASS,
      )}
    >
      <table
        data-slot="table"
        data-density={density}
        className={cn("w-full caption-bottom text-sm", className)}
        {...props}
      />
    </div>
  );
}

function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
  return (
    <thead
      data-slot="table-header"
      className={cn("[&_tr]:border-b", className)}
      {...props}
    />
  );
}

function TableBody({ className, ...props }: React.ComponentProps<"tbody">) {
  return (
    <tbody
      data-slot="table-body"
      className={cn("[&_tr:last-child]:border-0", className)}
      {...props}
    />
  );
}

function TableFooter({ className, ...props }: React.ComponentProps<"tfoot">) {
  return (
    <tfoot
      data-slot="table-footer"
      className={cn("border-t font-medium [&>tr]:last:border-b-0", className)}
      {...props}
    />
  );
}

function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  return (
    <tr
      data-slot="table-row"
      className={cn(
        "data-[state=selected]:bg-muted border-b transition-colors",
        className,
      )}
      {...props}
    />
  );
}

function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        "h-10 px-4 text-left align-middle font-medium whitespace-nowrap [[data-density=dense]_&]:h-9 [[data-density=dense]_&]:px-2 [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]",
        className,
      )}
      {...props}
    />
  );
}

function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return (
    <td
      data-slot="table-cell"
      className={cn(
        "p-4 align-middle whitespace-nowrap [[data-density=dense]_&]:px-2 [[data-density=dense]_&]:py-2 [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]",
        className,
      )}
      {...props}
    />
  );
}

function TableCaption({
  className,
  ...props
}: React.ComponentProps<"caption">) {
  return (
    <caption
      data-slot="table-caption"
      className={cn("mt-4 text-sm", className)}
      {...props}
    />
  );
}

// Data table component for easy usage
interface Column<T> {
  key: string;
  header: React.ReactNode;
  render?: (item: T) => React.ReactNode;
  className?: string;
  headerClassName?: string;
  cellClassName?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string;
  onRowClick?: (item: T) => void;
  /** One line, no explanation of why it is empty. */
  emptyMessage?: string;
  tableClassName?: string;
  stickyHeader?: boolean;
  density?: TableDensity;
}

function DataTable<T>({
  columns,
  data,
  keyExtractor,
  onRowClick,
  emptyMessage = "Nothing here yet.",
  tableClassName,
  stickyHeader = false,
  density = "standard",
}: DataTableProps<T>) {
  if (data.length === 0) {
    return <p className="py-6 text-sm">{emptyMessage}</p>;
  }

  return (
    <Table
      className={tableClassName}
      stickyHeader={stickyHeader}
      density={density}
    >
      <TableHeader>
        <TableRow>
          {columns.map((col) => (
            <TableHead
              key={col.key}
              className={cn(col.className, col.headerClassName)}
            >
              {col.header}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.map((item) => (
          <TableRow
            key={keyExtractor(item)}
            onClick={onRowClick ? () => onRowClick(item) : undefined}
            className={
              onRowClick ? "group draw-underline cursor-pointer" : undefined
            }
          >
            {columns.map((col) => (
              <TableCell
                key={col.key}
                className={cn(col.className, col.cellClassName)}
              >
                {col.render
                  ? col.render(item)
                  : // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- Generic T requires assertion for dynamic key access
                    (item as Record<string, unknown>)[col.key]?.toString() ||
                    "-"}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

/** The older pager API; it renders the one pager, TablePager. */
function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  if (total === 0) return null;
  const pages = Math.ceil(total / pageSize);
  const itemsOnPage = Math.min(pageSize, total - (page - 1) * pageSize);
  return (
    <TablePager
      page={page}
      pages={pages}
      total={total}
      pageSize={pageSize}
      itemsOnPage={itemsOnPage}
      onPageChange={onPageChange}
      noun="results"
    />
  );
}

export {
  DataTable,
  Pagination,
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
};
