import type { Document } from "@/api/endpoints";

import { StatusBadge } from "@/components/StatusBadge";

export function DocumentHeader({ doc }: { doc: Document }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">{doc.filename}</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            {doc.content_type} · {(doc.file_size / 1024).toFixed(1)} KB ·{" "}
            {new Date(doc.created_at).toLocaleString()}
          </p>
        </div>
        <StatusBadge status={doc.status} />
      </div>
    </div>
  );
}
