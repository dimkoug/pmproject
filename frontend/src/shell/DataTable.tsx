import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import type {
  ColumnDef,
  RowSelectionState,
  SortingState,
  ColumnFiltersState,
} from "@tanstack/react-table";
import { Icon } from "./icons";

export type DataTableProps<T> = {
  columns: ColumnDef<T, any>[];
  data: T[];
  isLoading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: ReactNode;
  globalSearch?: boolean;
  searchPlaceholder?: string;
  pageSizeOptions?: number[];
  defaultPageSize?: number;
  enableSelection?: boolean;
  onRowClick?: (row: T) => void;
  onSelectionChange?: (rows: T[]) => void;
  rowKey?: (row: T, index: number) => string;
  className?: string;
  skeletonRows?: number;
  /** Renders inside the toolbar whenever at least one row is selected. The
   * function gets the current selected rows and a `clear()` helper. */
  bulkActions?: (selected: T[], clear: () => void) => ReactNode;
  /** Persist table state (page size, sort, global filter) under this key. */
  stateStorageKey?: string;
};

export default function DataTable<T>({
  columns,
  data,
  isLoading = false,
  emptyTitle = "Nothing here yet",
  emptyDescription,
  emptyAction,
  globalSearch = true,
  searchPlaceholder = "Search…",
  pageSizeOptions = [25, 50, 100],
  defaultPageSize = 25,
  enableSelection = false,
  onRowClick,
  onSelectionChange,
  rowKey,
  className,
  skeletonRows = 6,
  bulkActions,
  stateStorageKey,
}: DataTableProps<T>) {
  // Persisted state hydration — page size, sort, global search filter. Guarded
  // by try/catch so a corrupt localStorage entry never crashes the table.
  const persisted = useMemo(() => {
    if (!stateStorageKey || typeof window === "undefined") return null;
    try {
      const raw = window.localStorage.getItem(`dt:${stateStorageKey}`);
      return raw ? JSON.parse(raw) as { sorting?: SortingState; globalFilter?: string; pageSize?: number } : null;
    } catch {
      return null;
    }
  }, [stateStorageKey]);

  const [sorting, setSorting] = useState<SortingState>(persisted?.sorting ?? []);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState(persisted?.globalFilter ?? "");
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});

  const resolvedColumns = useMemo<ColumnDef<T, any>[]>(() => {
    if (!enableSelection) return columns;
    const selectCol: ColumnDef<T, any> = {
      id: "__select",
      header: ({ table }) => (
        <input
          type="checkbox"
          aria-label="Select all rows"
          checked={table.getIsAllRowsSelected()}
          ref={(el) => {
            if (el) el.indeterminate = table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected();
          }}
          onChange={table.getToggleAllRowsSelectedHandler()}
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          aria-label="Select row"
          checked={row.getIsSelected()}
          onChange={row.getToggleSelectedHandler()}
          onClick={(e) => e.stopPropagation()}
        />
      ),
      enableSorting: false,
      size: 32,
    };
    return [selectCol, ...columns];
  }, [columns, enableSelection]);

  const table = useReactTable({
    data,
    columns: resolvedColumns,
    state: { sorting, columnFilters, globalFilter, rowSelection },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    onRowSelectionChange: (updater) => {
      setRowSelection((prev) => {
        const next = typeof updater === "function" ? updater(prev) : updater;
        if (onSelectionChange) {
          const rows = data.filter((_, i) => next[String(i)]);
          onSelectionChange(rows);
        }
        return next;
      });
    },
    getRowId: rowKey ? (row, i) => rowKey(row, i) : undefined,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: persisted?.pageSize ?? defaultPageSize } },
  });

  // Persist state back to localStorage on each change (debounce not needed —
  // these are user-driven events, not per-keystroke animations).
  if (stateStorageKey && typeof window !== "undefined") {
    try {
      const snap = JSON.stringify({
        sorting, globalFilter,
        pageSize: table.getState().pagination.pageSize,
      });
      window.localStorage.setItem(`dt:${stateStorageKey}`, snap);
    } catch { /* quota / privacy mode */ }
  }

  const selectedRows = useMemo(
    () => data.filter((_, i) => rowSelection[String(i)]),
    [data, rowSelection],
  );
  const clearSelection = () => setRowSelection({});

  const rows = table.getRowModel().rows;
  const totalRows = table.getFilteredRowModel().rows.length;
  const { pageIndex, pageSize } = table.getState().pagination;
  const firstRow = totalRows === 0 ? 0 : pageIndex * pageSize + 1;
  const lastRow = Math.min((pageIndex + 1) * pageSize, totalRows);

  const hasSelection = selectedRows.length > 0;

  return (
    <div className={`data-table ${className ?? ""}`}>
      {(globalSearch || (hasSelection && bulkActions)) && (
        <div className="data-table-toolbar">
          {globalSearch && (
            <div className="data-table-search">
              <Icon.Search size={14} aria-hidden />
              <input
                type="search"
                value={globalFilter}
                onChange={(e) => setGlobalFilter(e.target.value)}
                placeholder={searchPlaceholder}
                aria-label="Search table"
              />
            </div>
          )}
          {hasSelection && bulkActions && (
            <div className="data-table-bulk" role="toolbar" aria-label="Bulk actions">
              <span className="data-table-bulk-count">
                {selectedRows.length} selected
              </span>
              <div className="data-table-bulk-actions">
                {bulkActions(selectedRows, clearSelection)}
              </div>
              <button
                type="button"
                className="btn btn-sm btn-ghost"
                onClick={clearSelection}
                aria-label="Clear selection"
              >
                Clear
              </button>
            </div>
          )}
        </div>
      )}
      <div className="data-table-scroll">
        <table className="data-table-el">
          <thead className="data-table-head">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const sortDir = header.column.getIsSorted();
                  return (
                    <th
                      key={header.id}
                      style={{ width: header.getSize() }}
                      className={canSort ? "sortable" : ""}
                    >
                      {header.isPlaceholder ? null : (
                        <button
                          type="button"
                          className="data-table-th-btn"
                          onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                          disabled={!canSort}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {canSort && (
                            <span className="data-table-sort" aria-hidden>
                              {sortDir === "asc" ? (
                                <Icon.ArrowUp size={12} />
                              ) : sortDir === "desc" ? (
                                <Icon.ArrowDown size={12} />
                              ) : (
                                <Icon.ChevronDown size={12} style={{ opacity: 0.35 }} />
                              )}
                            </span>
                          )}
                        </button>
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {isLoading ? (
              Array.from({ length: skeletonRows }).map((_, i) => (
                <tr key={`skeleton-${i}`} className="data-table-skeleton-row">
                  {resolvedColumns.map((_, ci) => (
                    <td key={ci}>
                      <span className="data-table-skeleton-cell" />
                    </td>
                  ))}
                </tr>
              ))
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={resolvedColumns.length} className="data-table-empty">
                  <div className="data-table-empty-body">
                    <strong>{emptyTitle}</strong>
                    {emptyDescription && <p>{emptyDescription}</p>}
                    {emptyAction && <div className="data-table-empty-action">{emptyAction}</div>}
                  </div>
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={row.id}
                  className={`${row.getIsSelected() ? "selected" : ""} ${onRowClick ? "clickable" : ""}`}
                  onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {!isLoading && totalRows > 0 && (
        <div className="data-table-footer">
          <div className="data-table-footer-info">
            {firstRow}–{lastRow} of {totalRows}
          </div>
          <div className="data-table-footer-controls">
            <label className="data-table-pagesize">
              Rows:
              <select
                value={pageSize}
                onChange={(e) => table.setPageSize(Number(e.target.value))}
              >
                {pageSizeOptions.map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </label>
            <div className="data-table-pager">
              <button
                type="button"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                aria-label="Previous page"
              >
                <Icon.ChevronLeft size={14} />
              </button>
              <span>
                Page {pageIndex + 1} / {Math.max(1, table.getPageCount())}
              </span>
              <button
                type="button"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                aria-label="Next page"
              >
                <Icon.ChevronRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
