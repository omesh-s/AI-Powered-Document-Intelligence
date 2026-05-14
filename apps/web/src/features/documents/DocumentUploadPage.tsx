import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";

import * as api from "@/api/endpoints";
import { apiUploadPut, formatApiError } from "@/lib/apiClient";
import { ErrorState } from "@/components/ErrorState";

export function DocumentUploadPage() {
  const { workspaceId = "" } = useParams();
  const nav = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [stage, setStage] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);

  const upload = useMutation({
    mutationFn: async (f: File) => {
      setErr(null);
      setStage("Requesting upload URL…");
      const up = await api.requestUploadUrl({
        workspace_id: workspaceId,
        filename: f.name,
        content_type: f.type || "application/octet-stream",
        file_size: f.size,
      });
      setStage("Uploading to object storage…");
      await apiUploadPut(up.upload_url, f, up.required_headers);
      setStage("Finalizing document…");
      const doc = await api.finalizeDocument({
        workspace_id: workspaceId,
        filename: f.name,
        content_type: f.type || "application/octet-stream",
        file_size: f.size,
        storage_key: up.storage_key,
        checksum_sha256: null,
      });
      return doc;
    },
    onSuccess: (doc) => {
      setStage("Queued for ingestion.");
      nav(`/app/workspace/${workspaceId}/documents/${doc.id}`);
    },
    onError: (e: unknown) => {
      setStage("");
      setErr(formatApiError(e));
    },
  });

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-white">Upload document</h1>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
        Files upload directly to your configured object storage, then finalize through the API.
      </p>
      <div className="mt-8 rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <input
          type="file"
          accept=".pdf,.txt,.docx,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="block w-full text-sm"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        {stage ? <p className="mt-4 text-sm text-slate-700 dark:text-slate-300">{stage}</p> : null}
        {err ? (
          <div className="mt-4">
            <ErrorState title="Upload error" detail={err} />
          </div>
        ) : null}
        <button
          type="button"
          disabled={!file || upload.isPending}
          className="mt-6 w-full rounded-md bg-slate-900 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-slate-900"
          onClick={() => file && upload.mutate(file)}
        >
          {upload.isPending ? "Working…" : "Start upload"}
        </button>
      </div>
    </div>
  );
}
