import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import * as api from "@/api/endpoints";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";

export function WorkspaceHomePage() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["workspaces"], queryFn: api.fetchWorkspaces });
  const create = useMutation({
    mutationFn: (name: string) => api.createWorkspace(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspaces"] }),
  });
  const [name, setName] = useState("");

  return (
    <div className="mx-auto max-w-lg py-16">
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Workspaces</h1>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">Choose a workspace to open the console.</p>
      {q.isLoading ? <LoadingSkeleton className="mt-8 h-24 w-full" /> : null}
      {q.isError ? <ErrorState title="Failed to load workspaces" /> : null}
      {q.data?.length === 0 ? (
        <EmptyState
          title="No workspaces yet"
          description="Create one below to upload documents and run grounded queries."
        />
      ) : null}
      <ul className="mt-6 space-y-2">
        {q.data?.map((w) => (
          <li key={w.id}>
            <Link
              to={`/app/workspace/${w.id}/dashboard`}
              className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm font-medium text-slate-900 shadow-sm hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:text-white dark:hover:border-slate-600"
            >
              <span>{w.name}</span>
              <span className="text-xs text-slate-500">{w.role}</span>
            </Link>
          </li>
        ))}
      </ul>
      <form
        className="mt-8 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim()) return;
          create.mutate(name.trim());
          setName("");
        }}
      >
        <input
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
          placeholder="New workspace name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button
          type="submit"
          disabled={create.isPending}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-slate-900"
        >
          Create
        </button>
      </form>
    </div>
  );
}
