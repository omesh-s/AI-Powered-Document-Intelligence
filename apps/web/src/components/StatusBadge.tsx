const statusStyles: Record<string, string> = {
  indexed: "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-100",
  failed: "bg-rose-100 text-rose-900 dark:bg-rose-900/40 dark:text-rose-100",
  queued: "bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100",
  uploaded: "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-100",
  succeeded: "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/40 dark:text-emerald-100",
  running: "bg-sky-100 text-sky-900 dark:bg-sky-900/40 dark:text-sky-100",
  pending: "bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100",
  default: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
};

export function StatusBadge({ status }: { status: string }) {
  const cls = statusStyles[status] ?? statusStyles.default;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {status}
    </span>
  );
}
