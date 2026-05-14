import { useMutation, useQueryClient } from "@tanstack/react-query";

import * as api from "@/api/endpoints";

export function useAskMutation(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      question: string;
      document_id?: string | null;
      session_id?: string | null;
      debug?: boolean;
    }) =>
      api.askQuery({
        workspace_id: workspaceId,
        question: vars.question,
        document_id: vars.document_id,
        session_id: vars.session_id,
        debug: vars.debug,
      }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["sessions", workspaceId] });
      qc.invalidateQueries({ queryKey: ["session", data.session.id] });
    },
  });
}
