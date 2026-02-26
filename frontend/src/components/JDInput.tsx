"use client";

import { useState } from "react";

interface Props {
  onSubmit: (jdText: string | null, jdUrl: string | null) => void;
  isLoading: boolean;
  disabled: boolean;
}

export default function JDInput({ onSubmit, isLoading, disabled }: Props) {
  const [mode, setMode] = useState<"text" | "url">("text");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [fetchingUrl, setFetchingUrl] = useState(false);

  const handleSubmit = async () => {
    if (mode === "url" && url.trim()) {
      setFetchingUrl(true);
      try {
        const { fetchJobDescription } = await import("@/lib/api");
        const jdText = await fetchJobDescription(url.trim());
        setText(jdText);
        onSubmit(jdText, null);
      } catch (err) {
        alert(err instanceof Error ? err.message : "Failed to fetch JD");
      } finally {
        setFetchingUrl(false);
      }
    } else if (mode === "text" && text.trim()) {
      onSubmit(text.trim(), null);
    }
  };

  const canSubmit = disabled
    ? false
    : mode === "text"
      ? text.trim().length > 20
      : url.trim().length > 10;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted">
          Job Description
        </span>
        <div className="flex rounded-lg bg-surface-hover p-0.5">
          <button
            onClick={() => setMode("text")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              mode === "text"
                ? "bg-surface text-foreground shadow-sm"
                : "text-muted hover:text-foreground"
            }`}
          >
            Paste Text
          </button>
          <button
            onClick={() => setMode("url")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              mode === "url"
                ? "bg-surface text-foreground shadow-sm"
                : "text-muted hover:text-foreground"
            }`}
          >
            Job URL
          </button>
        </div>
      </div>

      {mode === "text" ? (
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste the full job description here..."
          rows={5}
          className="w-full resize-none rounded-lg border border-border bg-surface px-3 py-2 text-sm
                     placeholder:text-muted/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
        />
      ) : (
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://linkedin.com/jobs/view/... or any job posting URL"
          className="w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm
                     placeholder:text-muted/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary/30"
        />
      )}

      <button
        onClick={handleSubmit}
        disabled={!canSubmit || isLoading || fetchingUrl}
        className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white
                   transition-all hover:bg-primary-light disabled:cursor-not-allowed disabled:opacity-50"
      >
        {fetchingUrl
          ? "Fetching Job Description..."
          : isLoading
            ? "Analyzing..."
            : "Analyze Match"}
      </button>
    </div>
  );
}
