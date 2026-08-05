"use client";

import { clausesFromTrace } from "../lib/clauses";
import type { TraceEntry } from "../lib/types";

type Props = {
  trace: TraceEntry[];
};

export default function TracePanel({ trace }: Props) {
  if (trace.length === 0) return null;

  const clauses = clausesFromTrace(trace);
  const tools = trace.map((t) => t.tool);

  return (
    <details className="trace-panel group mt-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] open:bg-white/70">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-xs text-[var(--muted)] [&::-webkit-details-marker]:hidden">
        <span
          aria-hidden
          className="inline-block text-[10px] transition-transform group-open:rotate-90"
        >
          ▶
        </span>
        <span className="font-medium text-[var(--ink)]">Tool trace</span>
        <span className="truncate">{tools.join(" → ")}</span>
        {clauses.length > 0 && (
          <span className="ml-auto flex shrink-0 flex-wrap gap-1">
            {clauses.map((id) => (
              <span
                key={id}
                className="rounded bg-[var(--accent-soft)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--accent)]"
              >
                §{id}
              </span>
            ))}
          </span>
        )}
      </summary>
      <div className="space-y-3 border-t border-[var(--border)] px-3 py-3">
        {trace.map((entry, i) => (
          <div key={`${entry.tool}-${i}`} className="text-xs">
            <div className="mb-1 font-medium text-[var(--ink)]">
              {entry.tool}
            </div>
            <pre className="overflow-x-auto rounded-md bg-[var(--code-bg)] p-2 font-mono text-[11px] leading-relaxed text-[var(--ink)]">
              {JSON.stringify(
                { input: entry.input, output: entry.output },
                null,
                2,
              )}
            </pre>
          </div>
        ))}
      </div>
    </details>
  );
}
