export function PaginationControls({
  page,
  totalPages,
  onPage,
}: {
  page: number;
  totalPages: number;
  onPage: (p: number) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        className="rounded-md border border-slate-200 px-3 py-1 text-sm disabled:opacity-40 dark:border-slate-700"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
      >
        Previous
      </button>
      <span className="text-sm text-slate-600 dark:text-slate-400">
        Page {page} of {Math.max(totalPages, 1)}
      </span>
      <button
        type="button"
        className="rounded-md border border-slate-200 px-3 py-1 text-sm disabled:opacity-40 dark:border-slate-700"
        disabled={page >= totalPages}
        onClick={() => onPage(page + 1)}
      >
        Next
      </button>
    </div>
  );
}
