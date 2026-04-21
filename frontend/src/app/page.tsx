"use client";

import { useState, useCallback, useRef } from "react";
import ResumeUploader from "@/components/ResumeUploader";
import ResumeViewer from "@/components/ResumeViewer";
import JDInput from "@/components/JDInput";
import ScorePanel from "@/components/ScorePanel";
import ModelSelector from "@/components/ModelSelector";
import { uploadResume, getFileUrl, scoreResume, generateResume, rescoreResume } from "@/lib/api";
import { API_BASE } from "@/lib/config";
import type {
  ATSScoreReport,
  LearningSuggestion,
  ProgressEvent,
  UploadResponse,
  LLMSelection,
} from "@/types";

export default function Home() {
  const [uploadInfo, setUploadInfo] = useState<UploadResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const [progressEvents, setProgressEvents] = useState<ProgressEvent[]>([]);
  const [isScoring, setIsScoring] = useState(false);
  const [scoreError, setScoreError] = useState<string | null>(null);
  const [report, setReport] = useState<ATSScoreReport | null>(null);
  const [structuredResume, setStructuredResume] = useState<Record<string, unknown> | null>(null);
  const [jdText, setJdText] = useState<string | null>(null);

  const [isGenerating, setIsGenerating] = useState(false);
  const [previewPdfUrl, setPreviewPdfUrl] = useState<string | null>(null);

  const [rescoreReport, setRescoreReport] = useState<ATSScoreReport | null>(null);
  const [isRescoring, setIsRescoring] = useState(false);
  const [learningSuggestions, setLearningSuggestions] = useState<LearningSuggestion[]>([]);

  const [llmSelection, setLlmSelection] = useState<LLMSelection>({ provider: "local", model: "qwen2.5-coder:7b" });

  const previewBlobRef = useRef<string | null>(null);

  function revokePreview() {
    if (previewBlobRef.current) {
      URL.revokeObjectURL(previewBlobRef.current);
      previewBlobRef.current = null;
    }
    setPreviewPdfUrl(null);
    setRescoreReport(null);
    setIsRescoring(false);
    setLearningSuggestions([]);
  }

  const handleUpload = useCallback(async (file: File) => {
    setIsUploading(true);
    setReport(null);
    setProgressEvents([]);
    setScoreError(null);
    revokePreview();
    try {
      const info = await uploadResume(file);
      setUploadInfo(info);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      const hint =
        msg === "Failed to fetch" || msg.includes("NetworkError")
          ? ` Cannot reach the API. Is the backend running at ${API_BASE}?`
          : "";
      alert(msg + hint);
    } finally {
      setIsUploading(false);
    }
  }, []);

  const handleAnalyze = useCallback(
    async (jdTextInput: string | null, jdUrl: string | null) => {
      if (!uploadInfo) return;

      setIsScoring(true);
      setReport(null);
      setProgressEvents([]);
      setScoreError(null);
      revokePreview();
      if (jdTextInput) setJdText(jdTextInput);

      try {
        await scoreResume(
          uploadInfo.file_id,
          jdTextInput,
          jdUrl,
          (event) => {
            setProgressEvents((prev) => [...prev, event]);
          },
          (result) => {
            setReport(result.report);
            setStructuredResume(result.structured_resume);
            setIsScoring(false);
          },
          (message) => {
            setScoreError(message);
            setIsScoring(false);
          },
          llmSelection.provider,
          llmSelection.model,
        );
      } catch (err) {
        setScoreError(err instanceof Error ? err.message : "Scoring failed");
        setIsScoring(false);
      }
    },
    [uploadInfo, llmSelection]
  );

  const handleGeneratePreview = useCallback(async () => {
    if (!uploadInfo || !report || isGenerating) return;
    if (previewPdfUrl) return;

    setIsGenerating(true);
    try {
      const result = await generateResume(uploadInfo.file_id, report.keyword_changes);
      const pdfUrl = getFileUrl(result.file_id);
      previewBlobRef.current = pdfUrl;
      setPreviewPdfUrl(pdfUrl);

      if (structuredResume && jdText) {
        setIsRescoring(true);
        try {
          const rescoreResult = await rescoreResume(
            structuredResume,
            report.keyword_changes,
            jdText,
            llmSelection.provider,
            llmSelection.model,
          );
          setRescoreReport(rescoreResult.report);
          setLearningSuggestions(rescoreResult.learning_suggestions || []);
        } catch (err) {
          console.error("Rescore failed:", err);
        } finally {
          setIsRescoring(false);
        }
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setIsGenerating(false);
    }
  }, [uploadInfo, report, isGenerating, previewPdfUrl, structuredResume, jdText, llmSelection]);

  const handleDownload = useCallback(async () => {
    if (!previewPdfUrl) return;
    try {
      const res = await fetch(previewPdfUrl);
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = "optimized_resume.pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(objectUrl);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Download failed");
    }
  }, [previewPdfUrl]);

  const fileUrl = uploadInfo ? getFileUrl(uploadInfo.file_id) : null;

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border bg-surface px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
            </svg>
          </div>
          <div>
            <h1 className="text-base font-semibold">ATS Resume Scorer</h1>
            <p className="text-xs text-muted">Optimize your resume for any job</p>
          </div>
        </div>
        <ModelSelector value={llmSelection} onChange={setLlmSelection} />
      </header>

      {/* Two-Panel Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel - Resume + JD Input */}
        <div className="flex w-1/2 flex-col border-r border-border">
          {/* Upload Area */}
          <div className={`border-b border-border transition-all duration-200 ${
            uploadInfo && !isUploading ? "px-3 py-2" : "p-4"
          }`}>
            <ResumeUploader
              onUpload={handleUpload}
              isUploading={isUploading}
              currentFile={uploadInfo?.filename ?? null}
            />
          </div>

          {/* Resume Viewer */}
          <div className="flex-1 overflow-auto">
            <ResumeViewer
              fileUrl={fileUrl}
              fileType={uploadInfo?.file_type ?? null}
              keywordChanges={report?.keyword_changes ?? []}
            />
          </div>

          {/* JD Input */}
          <div className="border-t border-border p-4">
            <JDInput
              onSubmit={handleAnalyze}
              isLoading={isScoring}
              disabled={!uploadInfo}
            />
          </div>
        </div>

        {/* Right Panel - Score Results + Preview */}
        <div className="flex w-1/2 flex-col overflow-hidden p-5">
          <ScorePanel
            progressEvents={progressEvents}
            isScoring={isScoring}
            error={scoreError}
            report={report}
            onGenerate={handleGeneratePreview}
            onDownload={handleDownload}
            isGenerating={isGenerating}
            previewPdfUrl={previewPdfUrl}
            rescoreReport={rescoreReport}
            isRescoring={isRescoring}
            learningSuggestions={learningSuggestions}
          />
        </div>
      </div>
    </div>
  );
}
