import type { Citation } from "@/api/endpoints";

function shortId(id: string | null) {
  if (!id) return "—";
  return id.slice(0, 8);
}

export function CitationCard({
  c,
  href,
}: {
  c: Citation;
  href?: string;
}) {
  const inner = (
    <article className="rounded-lg border border-slate-200 bg-white p-3 text-left shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Citation</div>
      <div className="mt-1 font-medium text-slate-900 dark:text-slate-100">{c.document_name}</div>
      <dl className="mt-2 grid grid-cols-2 gap-x-2 gap-y-1 text-xs text-slate-600 dark:text-slate-400">
        <div>
          <dt className="font-medium text-slate-500">Page</dt>
          <dd>{c.page_number ?? "—"}</dd>
        </div>
        <div>
          <dt className="font-medium text-slate-500">Chunk</dt>
          <dd className="font-mono">{shortId(c.chunk_id)}</dd>
        </div>
        <div className="col-span-2">
          <dt className="font-medium text-slate-500">Score</dt>
          <dd>{c.score.toFixed(3)}</dd>
        </div>
      </dl>
      <p
        className="mt-2 line-clamp-6 text-sm text-slate-700 dark:text-slate-300"
        title={c.excerpt.length > 180 ? c.excerpt : undefined}
      >
        {c.excerpt}
      </p>
    </article>
  );
  if (href) {
    return (
      <a href={href} className="block outline-none ring-slate-400 focus-visible:ring-2">
        {inner}
      </a>
    );
  }
  return inner;
}
