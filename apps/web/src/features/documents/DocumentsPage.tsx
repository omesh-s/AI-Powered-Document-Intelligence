import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import * as api from "@/api/endpoints";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PaginationControls } from "@/components/PaginationControls";
import { StatusBadge } from "@/components/StatusBadge";

export function DocumentsPage() {
  const { workspaceId = "" } = useParams();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string>("");
  const size = 15;
  const q = useQuery({
    queryKey: ["documents", workspaceId, page, status],
    queryFn: () => api.fetchDocuments(workspaceId, page, size, status || undefined),
    enabled: !!workspaceId,
  });
  const totalPages = useMemo(() => {
    const t = q.data?.pagination.total ?? 0;
    return Math.max(1, Math.ceil(t / size));
  }, [q.data?.pagination.total, size]);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Documents</h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Workspace library with ingestion status.</p>
        </div>
        <Link
          to={`/app/workspace/${workspaceId}/documents/upload`}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-slate-900"
        >
          Upload
        </Link>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <label className="text-sm text-slate-600 dark:text-slate-400">
          Status{" "}
          <select
            className="ml-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All</option>
            <option value="indexed">indexed</option>
            <option value="queued">queued</option>
            <option value="failed">failed</option>
            <option value="uploaded">uploaded</option>
          </select>
        </label>
      </div>
      {q.isLoading ? <LoadingSkeleton className="mt-6 h-40 w-full" /> : null}
      {q.isError ? <ErrorState title="Failed to load documents" /> : null}
      {!q.isLoading && q.data?.items.length === 0 ? <EmptyState title="No documents match filters" /> : null}
      <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
            <tr>
              <th className="px-4 py-3">File</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Job</th>
              <th className="px-4 py-3">Created</th>
            </tr>
          </thead>
          <tbody>
            {q.data?.items.map((d) => (
              <tr key={d.id} className="border-b border-slate-100 dark:border-slate-800">
                <td className="px-4 py-3">
                  <Link
                    className="font-medium text-slate-900 underline dark:text-white"
                    to={`/app/workspace/${workspaceId}/documents/${d.id}`}
                  >
                    {d.filename}
                  </Link>
                  <div className="text-xs text-slate-500">{d.content_type}</div>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={d.status} />
                </td>
                <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">
                  {d.ingestion_job ? (
                    <>
                      {d.ingestion_job.stage} · {(d.ingestion_job.progress * 100).toFixed(0)}%
                    </>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-4 py-3 text-xs text-slate-600 dark:text-slate-400">
                  {new Date(d.created_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex justify-end">
        <PaginationControls page={page} totalPages={totalPages} onPage={setPage} />
      </div>
    </div>
  );
}
