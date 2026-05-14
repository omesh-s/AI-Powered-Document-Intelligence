import type { Citation } from "@/api/endpoints";

import { CitationCard } from "@/components/CitationCard";

export function ChatMessage({
  role,
  content,
  citations,
  answerability,
  isPending,
  citationHrefBuilder,
}: {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[] | null;
  answerability?: string | null;
  isPending?: boolean;
  citationHrefBuilder?: (c: Citation) => string | undefined;
}) {
  const isAssistant = role === "assistant";
  const insufficient = answerability === "insufficient_evidence";
  return (
    <div
      className={`mb-4 flex ${isAssistant ? "justify-start" : "justify-end"}`}
      aria-live={isAssistant ? "polite" : undefined}
    >
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
          isAssistant
            ? insufficient
              ? "border border-amber-300 bg-amber-50 text-amber-950 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-50"
              : "border border-slate-200 bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            : "bg-slate-800 text-white dark:bg-slate-700"
        }`}
      >
        {isAssistant && answerability ? (
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {insufficient ? "Insufficient evidence" : "Grounded answer"}
          </div>
        ) : null}
        <div className="whitespace-pre-wrap">{isPending ? "Thinking…" : content}</div>
        {isAssistant && citations && citations.length > 0 ? (
          <div className="mt-3 space-y-2 border-t border-slate-200 pt-3 dark:border-slate-700">
            <div className="text-xs font-semibold text-slate-600 dark:text-slate-400">Citations</div>
            <div className="grid gap-2 sm:grid-cols-2">
              {citations.map((c, i) => (
                <CitationCard key={i} c={c} href={citationHrefBuilder?.(c)} />
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
