"use client";

import { useState, useEffect, useCallback } from "react";
import type { ATSScoreReport, KeywordChange, LearningSuggestion } from "@/types";
import ScoreGauge from "./ScoreGauge";

interface Props {
  pdfBlobUrl: string | null;
  isGenerating: boolean;
  onGenerate: () => void;
  onDownload: () => void;
  keywordChanges: KeywordChange[];
  originalScore: number;
  rescoreReport: ATSScoreReport | null;
  isRescoring: boolean;
  learningSuggestions: LearningSuggestion[];
}

export default function ResumePreview({
  pdfBlobUrl,
  isGenerating,
  onGenerate,
  onDownload,
  keywordChanges,
  originalScore,
  rescoreReport,
  isRescoring,
  learningSuggestions,
}: Props) {
  const [pdfComponent, setPdfComponent] = useState<React.ReactNode>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!pdfBlobUrl && !isGenerating) {
      onGenerate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadPdf = useCallback(async (url: string) => {
    setLoading(true);
    try {
      const { Document, Page, pdfjs } = await import("react-pdf");
      await import("react-pdf/dist/Page/TextLayer.css");
      await import("react-pdf/dist/Page/AnnotationLayer.css");
      pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

      const PdfViewer = () => {
        const [numPages, setNumPages] = useState<number>(0);
        return (
          <Document
            file={url}
            onLoadSuccess={({ numPages: n }) => setNumPages(n)}
            className="flex flex-col items-center gap-4"
            loading={
              <div className="flex h-32 items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              </div>
            }
          >
            {Array.from({ length: numPages }, (_, i) => (
              <Page
                key={i}
                pageNumber={i + 1}
                width={480}
                renderTextLayer={true}
                renderAnnotationLayer={false}
              />
            ))}
          </Document>
        );
      };

      setPdfComponent(<PdfViewer />);
    } catch (err) {
      console.error("Failed to render preview PDF:", err);
      setPdfComponent(<p className="text-sm text-danger">Failed to load preview.</p>);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (pdfBlobUrl) {
      setPdfComponent(null);
      loadPdf(pdfBlobUrl);
    }
  }, [pdfBlobUrl, loadPdf]);

  if (isGenerating) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16">
        <div className="h-10 w-10 animate-spin rounded-full border-3 border-primary border-t-transparent" />
        <p className="text-sm text-muted">Generating optimized resume...</p>
        <p className="text-xs text-muted/60">Applying {keywordChanges.length} keyword changes</p>
      </div>
    );
  }

  if (!pdfBlobUrl) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16">
        <div className="h-10 w-10 animate-spin rounded-full border-3 border-primary border-t-transparent" />
        <p className="text-sm text-muted">Preparing preview...</p>
      </div>
    );
  }

  const newScore = rescoreReport?.overall_score ?? null;
  const scoreDelta = newScore !== null ? Math.round(newScore - originalScore) : null;

  return (
    <div className="flex flex-col gap-4">
      {/* Score comparison card */}
      <ScoreComparison
        originalScore={originalScore}
        newScore={newScore}
        scoreDelta={scoreDelta}
        isRescoring={isRescoring}
      />

      {/* Header bar with download */}
      <div className="flex items-center justify-between rounded-lg bg-accent/5 border border-accent/20 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <svg className="h-4 w-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
          </svg>
          <span className="text-sm font-medium text-accent">
            {keywordChanges.length} changes applied
          </span>
        </div>
        <button
          onClick={onDownload}
          className="flex items-center gap-1.5 rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-white
                     transition-colors hover:bg-accent/90"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
          Download PDF
        </button>
      </div>

      {/* Learning suggestions (score < 60) */}
      {learningSuggestions.length > 0 && (
        <LearningSuggestionsCard suggestions={learningSuggestions} />
      )}

      {/* PDF Preview */}
      <div className="rounded-lg border border-border bg-surface overflow-auto">
        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : pdfComponent ? (
          <div className="p-3">{pdfComponent}</div>
        ) : null}
      </div>

      {/* Keyword changes reference */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted">
          Changes Applied
        </h3>
        <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
          {keywordChanges.map((change, i) => (
            <div key={i} className="flex items-center gap-2 text-xs rounded-md bg-surface-hover/50 px-3 py-1.5">
              <span className="text-danger line-through">{change.original}</span>
              <svg className="h-2.5 w-2.5 text-muted flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
              <span className="text-accent font-medium">{change.recommended}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}


function ScoreComparison({
  originalScore,
  newScore,
  scoreDelta,
  isRescoring,
}: {
  originalScore: number;
  newScore: number | null;
  scoreDelta: number | null;
  isRescoring: boolean;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted mb-3">
        Score Comparison
      </h3>
      <div className="flex items-center justify-around gap-4">
        {/* Original */}
        <div className="flex flex-col items-center">
          <span className="text-[10px] uppercase tracking-wider text-muted mb-1">Before</span>
          <ScoreGauge score={originalScore} />
        </div>

        {/* Arrow */}
        <div className="flex flex-col items-center gap-1">
          <svg className="h-6 w-6 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
          </svg>
          {scoreDelta !== null && (
            <span className={`text-sm font-bold ${
              scoreDelta > 0 ? "text-accent" : scoreDelta < 0 ? "text-danger" : "text-muted"
            }`}>
              {scoreDelta > 0 ? "+" : ""}{scoreDelta}
            </span>
          )}
        </div>

        {/* New */}
        <div className="flex flex-col items-center">
          <span className="text-[10px] uppercase tracking-wider text-muted mb-1">After</span>
          {isRescoring ? (
            <div className="flex h-36 w-36 items-center justify-center">
              <div className="flex flex-col items-center gap-2">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                <span className="text-xs text-muted">Scoring...</span>
              </div>
            </div>
          ) : newScore !== null ? (
            <ScoreGauge score={newScore} />
          ) : (
            <div className="flex h-36 w-36 items-center justify-center">
              <span className="text-xs text-muted">Pending</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


const PRIORITY_STYLES = {
  high: { bg: "bg-danger/10", text: "text-danger", label: "High" },
  medium: { bg: "bg-warning/10", text: "text-warning", label: "Medium" },
  low: { bg: "bg-primary/10", text: "text-primary", label: "Low" },
} as const;

function LearningSuggestionsCard({ suggestions }: { suggestions: LearningSuggestion[] }) {
  return (
    <div className="rounded-lg border border-warning/30 bg-warning/5 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <svg className="h-4 w-4 text-warning" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
        </svg>
        <h3 className="text-sm font-semibold text-warning">
          Skills to Learn
        </h3>
        <span className="text-xs text-muted ml-auto">Score below 60 — consider upskilling</span>
      </div>
      <div className="space-y-2">
        {suggestions.map((s, i) => {
          const style = PRIORITY_STYLES[s.priority] || PRIORITY_STYLES.medium;
          return (
            <div key={i} className="rounded-md bg-surface/60 px-3 py-2.5 space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{s.skill}</span>
                <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${style.bg} ${style.text}`}>
                  {style.label}
                </span>
              </div>
              {s.reason && (
                <p className="text-xs text-muted leading-relaxed">{s.reason}</p>
              )}
              {s.resources && (
                <p className="text-xs text-primary/80">{s.resources}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
