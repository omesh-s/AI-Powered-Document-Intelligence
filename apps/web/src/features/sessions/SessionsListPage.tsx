import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import * as api from "@/api/endpoints";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { PaginationControls } from "@/components/PaginationControls";

export function SessionsListPage() {
  const { workspaceId = "" } = useParams();
  const [sp] = useSearchParams();
  const docFilter = sp.get("document") ?? "";
  const [page, setPage] = useState(1);
  const size = 20;
  const q = useQuery({
    queryKey: ["sessions", workspaceId, page, docFilter],
    queryFn: () => api.fetchSessions(workspaceId, page, size, docFilter || undefined),
    enabled: !!workspaceId,
  });
  const totalPages = Math.max(1, Math.ceil((q.data?.pagination.total ?? 0) / size));

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Sessions</h1>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">Continue a prior conversation from the query view.</p>
      {q.isLoading ? <LoadingSkeleton className="mt-6 h-32 w-full" /> : null}
      {q.isError ? <ErrorState title="Failed to load sessions" /> : null}
      {!q.isLoading && q.data?.items.length === 0 ? <EmptyState title="No sessions yet" /> : null}
      <ul className="mt-4 space-y-2">
        {q.data?.items.map((s) => (
          <li key={s.id}>
            <Link
              to={`/app/workspace/${workspaceId}/sessions/${s.id}`}
              className="block rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm dark:border-slate-800 dark:bg-slate-900"
            >
              <div className="font-medium">{s.title || "Untitled"}</div>
              <div className="text-xs text-slate-500">{new Date(s.created_at).toLocaleString()}</div>
            </Link>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex justify-end">
        <PaginationControls page={page} totalPages={totalPages} onPage={setPage} />
      </div>
    </div>
  );
}
