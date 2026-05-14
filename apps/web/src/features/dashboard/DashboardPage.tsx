import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import * as api from "@/api/endpoints";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { StatusBadge } from "@/components/StatusBadge";

export function DashboardPage() {
  const { workspaceId = "" } = useParams();
  const docs = useQuery({
    queryKey: ["documents", workspaceId, 1],
    queryFn: () => api.fetchDocuments(workspaceId, 1, 8),
    enabled: !!workspaceId,
  });
  const sessions = useQuery({
    queryKey: ["sessions", workspaceId, 1],
    queryFn: () => api.fetchSessions(workspaceId, 1, 8),
    enabled: !!workspaceId,
  });
  const jobs = useQuery({
    queryKey: ["ingestion", workspaceId, "failed"],
    queryFn: () => api.fetchIngestionJobs({ workspace_id: workspaceId, status: "failed", page: 1, size: 5 }),
    enabled: !!workspaceId,
  });

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Dashboard</h1>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Recent activity and quick actions.</p>
      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Recent documents</h2>
            <Link to={`/app/workspace/${workspaceId}/documents`} className="text-sm font-medium text-slate-900 underline dark:text-white">
              View all
            </Link>
          </div>
          {docs.isLoading ? <LoadingSkeleton className="h-32 w-full" /> : null}
          {docs.isError ? <ErrorState title="Could not load documents" /> : null}
          {docs.data?.items.length === 0 ? <EmptyState title="No documents yet" /> : null}
          <ul className="space-y-2">
            {docs.data?.items.map((d) => (
              <li key={d.id}>
                <Link
                  to={`/app/workspace/${workspaceId}/documents/${d.id}`}
                  className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-800 dark:bg-slate-900"
                >
                  <span className="truncate font-medium">{d.filename}</span>
                  <StatusBadge status={d.status} />
                </Link>
              </li>
            ))}
          </ul>
        </section>
        <section>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Recent sessions</h2>
            <Link to={`/app/workspace/${workspaceId}/sessions`} className="text-sm font-medium text-slate-900 underline dark:text-white">
              History
            </Link>
          </div>
          {sessions.isLoading ? <LoadingSkeleton className="h-32 w-full" /> : null}
          <ul className="space-y-2">
            {sessions.data?.items.map((s) => (
              <li key={s.id}>
                <Link
                  to={`/app/workspace/${workspaceId}/sessions/${s.id}`}
                  className="block rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-800 dark:bg-slate-900"
                >
                  <div className="truncate font-medium">{s.title || "Untitled session"}</div>
                  <div className="text-xs text-slate-500">{new Date(s.created_at).toLocaleString()}</div>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </div>
      <section className="mt-8 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <h2 className="text-sm font-semibold text-slate-900 dark:text-white">Ingestion health</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Failed jobs (latest 5):{" "}
          <span className="font-mono">{jobs.data?.pagination.total ?? "—"}</span>
        </p>
        {jobs.data?.items.length ? (
          <ul className="mt-2 space-y-1 text-xs text-rose-700 dark:text-rose-300">
            {jobs.data.items.map((j) => (
              <li key={j.id}>
                <Link className="underline" to={`/app/workspace/${workspaceId}/diagnostics?job=${j.id}`}>
                  {j.id.slice(0, 8)}… {j.error_code ?? j.stage}
                </Link>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
      <div className="mt-8">
        <Link
          to={`/app/workspace/${workspaceId}/documents/upload`}
          className="inline-flex rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white dark:bg-white dark:text-slate-900"
        >
          Upload document
        </Link>
      </div>
    </div>
  );
}
