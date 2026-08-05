"use client";

const SUGGESTIONS = [
  "Where is TR-4525?",
  "Can I return TR-4527?",
  "I want to return TR-4530",
];

type Props = {
  onPick: (text: string) => void;
};

export default function EmptyState({ onPick }: Props) {
  return (
    <div className="empty-enter flex flex-col items-start gap-6 pt-10 sm:pt-14">
      <div className="space-y-2">
        <h2 className="font-display text-4xl font-medium tracking-tight text-[var(--ink)] sm:text-5xl">
          Trendly
        </h2>
        <p className="max-w-md text-[15px] leading-relaxed text-[var(--muted)]">
          Ask about an order, a return, or a shipping policy. Every reply can
          show the tools and policy clauses it used.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onPick(s)}
            className="rounded-lg border border-[var(--border)] bg-[var(--paper)] px-3.5 py-2 text-sm text-[var(--ink)] transition-colors hover:border-[var(--accent)] hover:bg-white hover:text-[var(--accent)]"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
