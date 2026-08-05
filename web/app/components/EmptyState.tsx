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
    <div className="flex flex-col items-start gap-4 pt-8">
      <p className="text-[15px] leading-relaxed text-[var(--muted)]">
        Ask about an order, a return, or a shipping policy. Every reply can show
        the tools and policy clauses it used.
      </p>
      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onPick(s)}
            className="rounded-full border border-[var(--border)] bg-white/80 px-3 py-1.5 text-sm text-[var(--ink)] transition-colors hover:border-[var(--accent)] hover:text-[var(--accent)]"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
