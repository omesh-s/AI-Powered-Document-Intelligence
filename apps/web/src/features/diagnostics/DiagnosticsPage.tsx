import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "react-router-dom";

import * as api from "@/api/endpoints";
import { ErrorState } from "@/components/ErrorState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PaginationControls } from "@/components/PaginationControls";
import { StatusBadge } from "@/components/StatusBadge";

export function DiagnosticsPage() {
  const { workspaceId = "" } = useParams();
  const [sp] = useSearchParams();
  const jobFromUrl = sp.get("job");
  const [page, setPage] = useState(1);
  const [selectedJob, setSelectedJob] = useState<string | null>(jobFromUrl);

  const list = useQuery({
    queryKey: ["ingestion", workspaceId, page],
    queryFn: () => api.fetchIngestionJobs({ workspace_id: workspaceId, page, size: 15 }),
    enabled: !!workspaceId,
  });
  const detail = useQuery({
    queryKey: ["ingestion-job", selectedJob],
    queryFn: () => api.fetchIngestionJob(selectedJob!),
    enabled: !!selectedJob,
  });

  const totalPages = Math.max(1, Math.ceil((list.data?.pagination.total ?? 0) / 15));

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Diagnostics</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Ingestion jobs for this workspace. Select a row to inspect stage, progress, and metrics JSON.
        </p>
        {list.isLoading ? <LoadingSkeleton className="mt-4 h-40 w-full" /> : null}
        {list.isError ? <ErrorState title="Could not load jobs" /> : null}
        <ul className="mt-4 space-y-2 text-sm">
          {list.data?.items.map((j) => (
            <li key={j.id}>
              <button
                type="button"
                className={`w-full rounded-lg border px-3 py-2 text-left ${
                  selectedJob === j.id
                    ? "border-slate-900 bg-slate-100 dark:border-white dark:bg-slate-800"
                    : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
                }`}
                onClick={() => setSelectedJob(j.id)}
              >
                <div className="flex justify-between gap-2">
                  <span className="font-mono text-xs">{j.id.slice(0, 8)}…</span>
                  <StatusBadge status={j.status} />
                </div>
                <div className="text-xs text-slate-600 dark:text-slate-400">
                  {j.stage} · {(j.progress * 100).toFixed(0)}%
                </div>
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-4 flex justify-end">
          <PaginationControls page={page} totalPages={totalPages} onPage={setPage} />
        </div>
      </div>
      <div>
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Job detail</h2>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Metrics and errors from the worker pipeline.</p>
        {!selectedJob ? <p className="mt-2 text-sm text-slate-500">Select a job.</p> : null}
        {detail.isLoading ? <LoadingSkeleton className="mt-4 h-32 w-full" /> : null}
        {detail.data ? (
          <div className="mt-4 space-y-2 rounded-xl border border-slate-200 bg-white p-4 text-sm dark:border-slate-800 dark:bg-slate-900">
            <p>
              <span className="font-medium">Document:</span> {detail.data.document.filename}
            </p>
            {detail.data.job.error_code ? (
              <p className="text-rose-700 dark:text-rose-300">
                {detail.data.job.error_code}: {detail.data.job.error_message}
              </p>
            ) : null}
            <pre className="max-h-80 overflow-auto rounded bg-slate-950 p-3 text-xs text-slate-100">
              {JSON.stringify(detail.data.metrics ?? {}, null, 2)}
            </pre>
          </div>
        ) : null}
      </div>
    </div>
  );
}
