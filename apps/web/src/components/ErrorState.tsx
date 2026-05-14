export function ErrorState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-100">
      <div className="font-semibold">{title}</div>
      {detail ? <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-xs">{detail}</pre> : null}
    </div>
  );
}
