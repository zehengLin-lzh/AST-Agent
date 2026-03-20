"use client";

import type { KeywordChange } from "@/types";

interface Props {
  changes: KeywordChange[];
}

const IMPACT_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };
const DIFF_ORDER: Record<string, number> = { easy: 0, medium: 1, hard: 2 };

function sortChanges(changes: KeywordChange[]): KeywordChange[] {
  return [...changes].sort((a, b) => {
    const impactDiff = (IMPACT_ORDER[a.impact] ?? 1) - (IMPACT_ORDER[b.impact] ?? 1);
    if (impactDiff !== 0) return impactDiff;
    return (DIFF_ORDER[a.difficulty] ?? 0) - (DIFF_ORDER[b.difficulty] ?? 0);
  });
}

function ImpactBadge({ impact }: { impact: KeywordChange["impact"] }) {
  if (impact === "high") {
    return (
      <span className="inline-block rounded bg-danger/10 px-1.5 py-0.5 text-xs font-medium text-danger">
        High Impact
      </span>
    );
  }
  if (impact === "low") {
    return (
      <span className="inline-block rounded bg-accent/10 px-1.5 py-0.5 text-xs font-medium text-accent">
        Low
      </span>
    );
  }
  return (
    <span className="inline-block rounded bg-warning/10 px-1.5 py-0.5 text-xs font-medium text-warning">
      Medium
    </span>
  );
}

function DifficultyBadge({ difficulty }: { difficulty: KeywordChange["difficulty"] }) {
  if (difficulty === "easy") {
    return (
      <span className="inline-block rounded bg-accent/10 px-1.5 py-0.5 text-xs font-medium text-accent">
        Easy
      </span>
    );
  }
  if (difficulty === "hard") {
    return (
      <span className="inline-block rounded bg-danger/10 px-1.5 py-0.5 text-xs font-medium text-danger">
        Hard
      </span>
    );
  }
  return (
    <span className="inline-block rounded bg-warning/10 px-1.5 py-0.5 text-xs font-medium text-warning">
      Medium
    </span>
  );
}

export default function KeywordChanges({ changes }: Props) {
  if (changes.length === 0) return null;

  const sorted = sortChanges(changes);

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
        Keyword Recommendations ({changes.length})
      </h3>
      <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
        {sorted.map((change, i) => (
          <div
            key={i}
            className="animate-slide-up rounded-lg border border-border bg-surface p-3 text-sm"
            style={{ animationDelay: `${i * 50}ms` }}
          >
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="inline-block rounded bg-danger/10 px-2 py-0.5 text-xs font-medium text-danger line-through">
                {change.original}
              </span>
              <svg className="h-3 w-3 text-muted flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
              <span className="inline-block rounded bg-accent/10 px-2 py-0.5 text-xs font-medium text-accent">
                {change.recommended}
              </span>
              <span className="ml-auto flex items-center gap-1.5">
                <ImpactBadge impact={change.impact} />
                <DifficultyBadge difficulty={change.difficulty} />
              </span>
            </div>
            {change.context && (
              <p className="text-xs text-muted leading-relaxed line-clamp-2">
                {change.context}
              </p>
            )}
            {change.reason && (
              <p className="text-xs text-primary/70 mt-1">
                {change.reason}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
