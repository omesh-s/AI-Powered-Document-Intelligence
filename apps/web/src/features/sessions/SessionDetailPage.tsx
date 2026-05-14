import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import type { Citation } from "@/api/endpoints";
import * as api from "@/api/endpoints";
import { ChatMessage } from "@/components/ChatMessage";
import { ErrorState } from "@/components/ErrorState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";

export function SessionDetailPage() {
  const { workspaceId = "", sessionId = "" } = useParams();
  const q = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => api.fetchSession(sessionId),
    enabled: !!sessionId,
  });

  if (q.isLoading) return <LoadingSkeleton className="h-40 w-full" />;
  if (q.isError || !q.data) return <ErrorState title="Session not found" />;

  const citationHref = (c: Citation) =>
    `/app/workspace/${workspaceId}/documents/${c.document_id}#chunk-${c.chunk_id ?? ""}`;

  return (
    <div>
      <div className="mb-4 text-sm">
        <Link className="text-slate-600 underline dark:text-slate-400" to={`/app/workspace/${workspaceId}/sessions`}>
          ← Sessions
        </Link>
      </div>
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Session</h1>
      <p className="mt-1 font-mono text-xs text-slate-500">{sessionId}</p>
      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        {q.data.messages.map((m) => (
          <ChatMessage
            key={m.id}
            role={m.role as "user" | "assistant"}
            content={m.content}
            citations={m.citations}
            answerability={m.answerability}
            citationHrefBuilder={m.role === "assistant" ? citationHref : undefined}
          />
        ))}
      </div>
    </div>
  );
}
