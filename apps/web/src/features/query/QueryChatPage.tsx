import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";

import type { Citation, QueryMessage } from "@/api/endpoints";
import * as api from "@/api/endpoints";
import { ChatMessage } from "@/components/ChatMessage";
import { ErrorState } from "@/components/ErrorState";
import { useAskMutation } from "@/hooks/useAskMutation";
import { formatApiError } from "@/lib/apiClient";

type UiMsg = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[] | null;
  answerability?: string | null;
  debug?: Record<string, unknown> | null;
};

export function QueryChatPage() {
  const { workspaceId = "" } = useParams();
  const [sp] = useSearchParams();
  const docScoped = sp.get("document");
  const sessionFromUrl = sp.get("session");

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMsg[]>([]);
  const [question, setQuestion] = useState("");
  const [debug, setDebug] = useState(false);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const ask = useAskMutation(workspaceId);

  useEffect(() => {
    if (!sessionFromUrl) return;
    let cancelled = false;
    setLoadErr(null);
    api
      .fetchSession(sessionFromUrl)
      .then((d) => {
        if (cancelled) return;
        setSessionId(d.session.id);
        setMessages(
          d.messages.map((m: QueryMessage) => ({
            id: m.id,
            role: m.role as "user" | "assistant",
            content: m.content,
            citations: m.citations,
            answerability: m.answerability,
            debug: m.debug_json,
          })),
        );
      })
      .catch(() => {
        if (!cancelled) setLoadErr("Could not load session from URL.");
      });
    return () => {
      cancelled = true;
    };
  }, [sessionFromUrl]);

  useEffect(() => {
    listRef.current?.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, ask.isPending]);

  const citationHref = (c: Citation) =>
    `/app/workspace/${workspaceId}/documents/${c.document_id}#chunk-${c.chunk_id ?? ""}`;

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Query</h1>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
        {docScoped ? (
          <>
            Scoped to document <span className="font-mono text-xs">{docScoped}</span>.
          </>
        ) : (
          "Workspace-wide retrieval across indexed documents."
        )}
      </p>
      {sessionId ? (
        <p className="mt-2 text-xs text-slate-500">
          Session <span className="font-mono">{sessionId}</span> — share this URL with{" "}
          <span className="font-mono">?session=</span> to resume.
        </p>
      ) : null}
      {loadErr ? <ErrorState title={loadErr} /> : null}
      <div
        ref={listRef}
        className="mt-6 max-h-[min(70dvh,32rem)] min-h-[12rem] overflow-y-auto overflow-x-hidden rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
        aria-live="polite"
      >
        {messages.length === 0 && !ask.isPending ? (
          <p className="text-center text-sm text-slate-500">Ask a question to retrieve grounded context.</p>
        ) : null}
        {messages.map((m) => (
          <ChatMessage
            key={m.id}
            role={m.role}
            content={m.content}
            citations={m.citations}
            answerability={m.answerability}
            citationHrefBuilder={(c) => citationHref(c)}
          />
        ))}
        {ask.isPending ? (
          <ChatMessage role="assistant" content="" isPending citations={undefined} />
        ) : null}
      </div>
      {ask.data?.debug && debug ? (
        <pre className="mt-4 max-h-48 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">
          {JSON.stringify(ask.data.debug, null, 2)}
        </pre>
      ) : null}
      <form
        className="mt-4 space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!question.trim() || ask.isPending) return;
          const q = question.trim();
          setQuestion("");
          setMessages((prev) => [...prev, { id: `local-user-${Date.now()}`, role: "user", content: q }]);
          ask.mutate(
            { question: q, document_id: docScoped, session_id: sessionId, debug },
            {
              onSuccess: (data) => {
                setSessionId(data.session.id);
                setMessages((prev) => [
                  ...prev,
                  {
                    id: data.message.id,
                    role: "assistant",
                    content: data.message.content,
                    citations: data.citations,
                    answerability: data.message.answerability,
                    debug: data.debug ?? null,
                  },
                ]);
              },
              onError: (err: unknown) => {
                setMessages((prev) => [
                  ...prev,
                  {
                    id: `local-err-${Date.now()}`,
                    role: "assistant",
                    content: formatApiError(err),
                    answerability: "insufficient_evidence",
                  },
                ]);
              },
            },
          );
        }}
      >
        <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
          <input type="checkbox" checked={debug} onChange={(e) => setDebug(e.target.checked)} />
          Debug retrieval payload on next answer
        </label>
        <textarea
          className="w-full rounded-md border border-slate-300 bg-white p-3 text-sm dark:border-slate-700 dark:bg-slate-950"
          rows={3}
          value={question}
          placeholder="Ask a grounded question…"
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button
          type="submit"
          disabled={ask.isPending}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-slate-900"
        >
          Send
        </button>
      </form>
    </div>
  );
}
