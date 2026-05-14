import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import * as api from "@/api/endpoints";
import { DocumentHeader } from "@/components/DocumentHeader";
import { ErrorState } from "@/components/ErrorState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { Tabs } from "@/components/Tabs";
import { useAskMutation } from "@/hooks/useAskMutation";

export function DocumentDetailPage() {
  const { workspaceId = "", documentId = "" } = useParams();
  const qc = useQueryClient();
  const bottomRef = useRef<HTMLDivElement>(null);

  const docQ = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => api.fetchDocument(documentId),
    enabled: !!documentId,
  });
  const pagesQ = useQuery({
    queryKey: ["document-pages", documentId],
    queryFn: () => api.fetchDocumentPages(documentId),
    enabled: !!documentId && docQ.data?.status === "indexed",
  });
  const chunksQ = useQuery({
    queryKey: ["document-chunks", documentId],
    queryFn: () => api.fetchDocumentChunks(documentId),
    enabled: !!documentId && docQ.data?.status === "indexed",
  });

  useEffect(() => {
    const h = window.location.hash;
    if (!h) return;
    window.setTimeout(() => document.querySelector(h)?.scrollIntoView({ behavior: "smooth", block: "start" }), 100);
  }, [pagesQ.data, chunksQ.data]);

  const reprocess = useMutation({
    mutationFn: () => api.reprocessDocument(documentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["document", documentId] });
      qc.invalidateQueries({ queryKey: ["documents", workspaceId] });
    },
  });

  const ask = useAskMutation(workspaceId);
  const [qtext, setQtext] = useState("");
  const [debug, setDebug] = useState(false);

  const citationBase = useMemo(() => `/app/workspace/${workspaceId}/documents/${documentId}`, [workspaceId, documentId]);

  if (docQ.isLoading) return <LoadingSkeleton className="h-40 w-full" />;
  if (docQ.isError || !docQ.data) return <ErrorState title="Document not available" />;

  const d = docQ.data;

  return (
    <div className="space-y-6">
      <DocumentHeader doc={d} />
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium dark:border-slate-600"
          disabled={reprocess.isPending}
          onClick={() => reprocess.mutate()}
        >
          Reprocess latest version
        </button>
        <Link
          to={`/app/workspace/${workspaceId}/query?document=${documentId}`}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white dark:bg-white dark:text-slate-900"
        >
          Open full query view
        </Link>
      </div>
      {reprocess.isError ? <ErrorState title="Reprocess failed" /> : null}
      <Tabs
        tabs={["Overview", "Pages", "Chunks", "Ask"]}
        panels={[
          <div key="o" className="space-y-3 text-sm text-slate-700 dark:text-slate-300">
            <p>
              <span className="font-medium text-slate-900 dark:text-white">Version:</span>{" "}
              <span className="font-mono text-xs">{d.latest_version_id ?? "—"}</span>
            </p>
            {d.ingestion_job ? (
              <p>
                Latest job {d.ingestion_job.id.slice(0, 8)}… — {d.ingestion_job.stage} (
                {(d.ingestion_job.progress * 100).toFixed(0)}%)
              </p>
            ) : (
              <p>No ingestion job on record.</p>
            )}
          </div>,
          <div key="p" className="space-y-6">
            {pagesQ.isLoading ? <LoadingSkeleton className="h-24 w-full" /> : null}
            {pagesQ.isError ? <ErrorState title="Could not load pages (document may still be ingesting)" /> : null}
            {pagesQ.data?.pages.map((p) => (
              <section key={p.id} id={`page-${p.page_number}`} className="scroll-mt-24 rounded-lg border border-slate-200 p-4 dark:border-slate-800">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Page {p.page_number}</h3>
                <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap text-xs text-slate-700 dark:text-slate-300">
                  {(p.markdown_text || p.raw_text || "").trim()}
                </pre>
              </section>
            ))}
          </div>,
          <div key="c" className="space-y-4">
            {chunksQ.isLoading ? <LoadingSkeleton className="h-24 w-full" /> : null}
            {chunksQ.isError ? <ErrorState title="Could not load chunks" /> : null}
            {chunksQ.data?.chunks.map((c) => (
              <article
                key={c.id}
                id={`chunk-${c.id}`}
                className="scroll-mt-24 rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800"
              >
                <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-500">
                  <span className="font-mono">chunk #{c.chunk_index}</span>
                  <span>page {c.page_number ?? "—"}</span>
                </div>
                <p className="mt-2 whitespace-pre-wrap text-slate-800 dark:text-slate-200">{c.text}</p>
              </article>
            ))}
          </div>,
          <div key="a" className="space-y-3">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Quick question scoped to this document. Opens the same grounded pipeline as the main query view.
            </p>
            <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-400">
              <input type="checkbox" checked={debug} onChange={(e) => setDebug(e.target.checked)} />
              Include retrieval debug metadata
            </label>
            <textarea
              className="w-full rounded-md border border-slate-300 bg-white p-3 text-sm dark:border-slate-700 dark:bg-slate-950"
              rows={3}
              placeholder="Ask about this document…"
              value={qtext}
              onChange={(e) => setQtext(e.target.value)}
            />
            <button
              type="button"
              disabled={ask.isPending || !qtext.trim()}
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-slate-900"
              onClick={() =>
                ask.mutate(
                  { question: qtext.trim(), document_id: documentId, debug },
                  {
                    onSuccess: () => {
                      setQtext("");
                      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
                    },
                  },
                )
              }
            >
              {ask.isPending ? "Asking…" : "Ask"}
            </button>
            {ask.data ? (
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm dark:border-slate-800 dark:bg-slate-950">
                <div className="text-xs font-semibold text-slate-500">{ask.data.message.answerability}</div>
                <p className="mt-2 whitespace-pre-wrap">{ask.data.message.content}</p>
                {ask.data.citations.length ? (
                  <ul className="mt-3 space-y-2 text-xs">
                    {ask.data.citations.map((c, i) => (
                      <li key={i}>
                        <a className="font-medium text-slate-900 underline dark:text-white" href={`${citationBase}#chunk-${c.chunk_id}`}>
                          {c.document_name} · p.{c.page_number ?? "?"} · score {c.score.toFixed(2)}
                        </a>
                        <div className="text-slate-600 dark:text-slate-400">{c.excerpt.slice(0, 200)}…</div>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : null}
            <div ref={bottomRef} />
          </div>,
        ]}
      />
    </div>
  );
}
