import { type ReactNode, useState } from "react";

export function Tabs({
  tabs,
  panels,
  initial = 0,
}: {
  tabs: string[];
  panels: ReactNode[];
  initial?: number;
}) {
  const [i, setI] = useState(initial);
  return (
    <div>
      <div className="flex gap-1 border-b border-slate-200 dark:border-slate-800" role="tablist">
        {tabs.map((t, idx) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={i === idx}
            className={`rounded-t-md px-4 py-2 text-sm font-medium ${
              i === idx
                ? "border border-b-0 border-slate-200 bg-white text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            }`}
            onClick={() => setI(idx)}
          >
            {t}
          </button>
        ))}
      </div>
      <div className="rounded-b-xl border border-t-0 border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        {panels[i]}
      </div>
    </div>
  );
}
