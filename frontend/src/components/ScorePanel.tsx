"use client";

import { useState } from "react";
import type { ATSScoreReport, LearningSuggestion, ProgressEvent } from "@/types";
import ProgressSteps from "./ProgressSteps";
import ScoreGauge from "./ScoreGauge";
import KeywordChanges from "./KeywordChanges";
import ResumePreview from "./ResumePreview";

type Tab = "score" | "preview";

interface Props {
  progressEvents: ProgressEvent[];
  isScoring: boolean;
  error: string | null;
  report: ATSScoreReport | null;
  onGenerate: () => void;
  onDownload: () => void;
  isGenerating: boolean;
  previewPdfUrl: string | null;
  rescoreReport: ATSScoreReport | null;
  isRescoring: boolean;
  learningSuggestions: LearningSuggestion[];
}

const BREAKDOWN_LABELS: Record<string, string> = {
  skills: "Technical Skills",
  experience: "Experience",
  qualifications: "Qualifications",
  soft_skills: "Soft Skills",
  tools: "Tools & Technologies",
};

function getBarColor(value: number): string {
  if (value >= 80) return "bg-accent";
  if (value >= 60) return "bg-primary";
  if (value >= 40) return "bg-warning";
  return "bg-danger";
}

export default function ScorePanel({
  progressEvents,
  isScoring,
  error,
  report,
  onGenerate,
  onDownload,
  isGenerating,
  previewPdfUrl,
  rescoreReport,
  isRescoring,
  learningSuggestions,
}: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("score");

  if (!isScoring && !report && progressEvents.length === 0 && !error) {
    return (
      <div className="flex h-full items-center justify-center text-muted">
        <div className="text-center">
          <svg className="mx-auto h-16 w-16 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
          </svg>
          <p className="text-sm">Score results will appear here</p>
          <p className="text-xs mt-1 opacity-60">Upload a resume and enter a JD to begin</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Progress Steps */}
      {(isScoring || (progressEvents.length > 0 && !report)) && (
        <div className="p-1 pb-4">
          <ProgressSteps events={progressEvents} isComplete={!!report} error={error} />
        </div>
      )}

      {/* Tabs + Content (only when report is ready) */}
      {report && (
        <>
          {/* Tab Bar */}
          <div className="flex border-b border-border mb-4">
            <button
              onClick={() => setActiveTab("score")}
              className={`relative px-4 py-2.5 text-sm font-medium transition-colors ${
                activeTab === "score"
                  ? "text-primary"
                  : "text-muted hover:text-foreground"
              }`}
            >
              <div className="flex items-center gap-1.5">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
                </svg>
                Score Analysis
              </div>
              {activeTab === "score" && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
              )}
            </button>
            <button
              onClick={() => setActiveTab("preview")}
              className={`relative px-4 py-2.5 text-sm font-medium transition-colors ${
                activeTab === "preview"
                  ? "text-primary"
                  : "text-muted hover:text-foreground"
              }`}
            >
              <div className="flex items-center gap-1.5">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                </svg>
                Optimized Resume
                {(isGenerating || previewPdfUrl) && (
                  <span className={`ml-1 inline-block h-1.5 w-1.5 rounded-full ${
                    previewPdfUrl ? "bg-accent" : "bg-warning animate-pulse"
                  }`} />
                )}
              </div>
              {activeTab === "preview" && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />
              )}
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-auto p-1">
            {activeTab === "score" ? (
              <ScoreContent report={report} />
            ) : (
              <ResumePreview
                pdfBlobUrl={previewPdfUrl}
                isGenerating={isGenerating}
                onGenerate={onGenerate}
                onDownload={onDownload}
                keywordChanges={report.keyword_changes}
                originalScore={report.overall_score}
                rescoreReport={rescoreReport}
                isRescoring={isRescoring}
                learningSuggestions={learningSuggestions}
              />
            )}
          </div>
        </>
      )}

      {/* Error only (no progress) */}
      {error && !isScoring && progressEvents.length === 0 && (
        <div className="rounded-lg bg-danger/5 border border-danger/20 p-4">
          <p className="text-sm text-danger">{error}</p>
        </div>
      )}
    </div>
  );
}

function ScoreContent({ report }: { report: ATSScoreReport }) {
  return (
    <div className="space-y-6 animate-slide-up">
      {/* Overall Score */}
      <div className="flex justify-center">
        <ScoreGauge score={report.overall_score} />
      </div>

      {/* Summary */}
      <div className="rounded-lg bg-surface-hover/50 p-4">
        <p className="text-sm leading-relaxed">{report.summary}</p>
      </div>

      {/* Score Breakdown */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
          Score Breakdown
        </h3>
        <div className="space-y-2">
          {Object.entries(report.score_breakdown).map(([key, value]) => (
            <div key={key} className="flex items-center gap-3">
              <span className="w-32 text-xs text-muted">
                {BREAKDOWN_LABELS[key] || key}
              </span>
              <div className="flex-1 h-2 rounded-full bg-border overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-1000 ease-out ${getBarColor(value)}`}
                  style={{ width: `${value}%` }}
                />
              </div>
              <span className="w-8 text-right text-xs font-medium">
                {Math.round(value)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Strengths */}
      {report.strengths.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-accent">
            Strengths
          </h3>
          <ul className="space-y-1">
            {report.strengths.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <svg className="mt-0.5 h-4 w-4 flex-shrink-0 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                </svg>
                {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Gaps */}
      {report.gaps.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-danger">
            Gaps
          </h3>
          <ul className="space-y-1">
            {report.gaps.map((g, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <svg className="mt-0.5 h-4 w-4 flex-shrink-0 text-danger" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
                </svg>
                {g}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Missing Critical Keywords */}
      {report.missing_critical_keywords.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-warning">
            Missing Critical Keywords
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {report.missing_critical_keywords.map((kw, i) => (
              <span
                key={i}
                className="rounded-full bg-warning/10 px-2.5 py-0.5 text-xs font-medium text-warning"
              >
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Keyword Changes */}
      <KeywordChanges changes={report.keyword_changes} />
    </div>
  );
}
