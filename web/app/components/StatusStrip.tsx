"use client";

import type { SessionStateView } from "../lib/types";

type Props = {
  state: SessionStateView | null;
  error: string | null;
};

export default function StatusStrip({ state, error }: Props) {
  return (
    <>
      {state?.escalated && (
        <div className="mb-2 rounded-lg border border-[#e6d9b8] bg-[#f7f1e4] px-3 py-2 text-xs text-[#5c4e2a]">
          This conversation was handed to a human specialist.
        </div>
      )}
      {state && (
        <div className="mb-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-[var(--muted)]">
          <span>
            Order:{" "}
            <span className="font-medium text-[var(--ink)]">
              {state.active_order ?? "none"}
            </span>
          </span>
          <span>
            Verified:{" "}
            <span className="font-medium text-[var(--ink)]">
              {state.verified ? "yes" : "no"}
            </span>
          </span>
        </div>
      )}
      {error && (
        <p className="mb-2 text-xs text-[#9b3b3b]" role="alert">
          {error}
        </p>
      )}
    </>
  );
}
