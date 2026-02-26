"use client";

import type { ProgressEvent } from "@/types";

const STEP_ORDER = [
  { key: "resolving_jd", label: "Resolving job description" },
  { key: "parsing", label: "Extracting resume text" },
  { key: "structuring", label: "Structuring resume with AI" },
  { key: "scoring", label: "Running ATS analysis" },
  { key: "validating", label: "Validating results" },
];

interface Props {
  events: ProgressEvent[];
  isComplete: boolean;
  error: string | null;
}

export default function ProgressSteps({ events, isComplete, error }: Props) {
  const completedSteps = new Set(
    events
      .filter((e) => e.step.endsWith("_done") || e.step === "validating")
      .map((e) => e.step.replace("_done", ""))
  );

  const activeStep = events.length > 0 ? events[events.length - 1].step.replace("_done", "") : null;

  if (events.length === 0 && !error) return null;

  return (
    <div className="animate-slide-up space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
        Analysis Progress
      </h3>
      <div className="space-y-2">
        {STEP_ORDER.map(({ key, label }) => {
          const isDone = completedSteps.has(key) || isComplete;
          const isActive = activeStep === key && !isDone;

          return (
            <div key={key} className="flex items-center gap-3">
              <div className="flex-shrink-0">
                {isDone ? (
                  <div className="flex h-5 w-5 items-center justify-center rounded-full bg-accent/10">
                    <svg className="h-3 w-3 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                    </svg>
                  </div>
                ) : isActive ? (
                  <div className="flex h-5 w-5 items-center justify-center">
                    <div className="h-3 w-3 animate-pulse-ring rounded-full bg-primary" />
                  </div>
                ) : (
                  <div className="flex h-5 w-5 items-center justify-center">
                    <div className="h-2 w-2 rounded-full bg-border" />
                  </div>
                )}
              </div>
              <span
                className={`text-sm ${
                  isDone
                    ? "text-foreground"
                    : isActive
                      ? "font-medium text-primary"
                      : "text-muted/50"
                }`}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>

      {error && (
        <div className="mt-3 rounded-lg bg-danger/5 border border-danger/20 p-3">
          <p className="text-sm text-danger">{error}</p>
        </div>
      )}
    </div>
  );
}
