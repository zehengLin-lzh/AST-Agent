"use client";

import { useCallback, useRef, useState } from "react";

interface Props {
  onUpload: (file: File) => void;
  isUploading: boolean;
  currentFile: string | null;
}

export default function ResumeUploader({ onUpload, isUploading, currentFile }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFile = useCallback(
    (file: File) => {
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (ext !== "pdf" && ext !== "docx") {
        alert("Please upload a PDF or DOCX file.");
        return;
      }
      onUpload(file);
    },
    [onUpload]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const fileInput = (
    <input
      ref={inputRef}
      type="file"
      accept=".pdf,.docx"
      className="hidden"
      onChange={(e) => {
        const file = e.target.files?.[0];
        if (file) handleFile(file);
        e.target.value = "";
      }}
    />
  );

  if (currentFile && !isUploading) {
    return (
      <div
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={`
          flex items-center justify-between rounded-lg border px-3 py-2 transition-all duration-200
          ${dragActive
            ? "border-primary bg-blue-50/50"
            : "border-border bg-surface-hover/30"
          }
        `}
      >
        {fileInput}
        <div className="flex items-center gap-2 min-w-0">
          <FileIcon filename={currentFile} />
          <span className="truncate text-sm font-medium">{currentFile}</span>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); inputRef.current?.click(); }}
          className="flex-shrink-0 flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium
                     text-primary hover:bg-primary/10 transition-colors"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 7.5h-.75A2.25 2.25 0 0 0 4.5 9.75v7.5a2.25 2.25 0 0 0 2.25 2.25h7.5a2.25 2.25 0 0 0 2.25-2.25v-7.5a2.25 2.25 0 0 0-2.25-2.25h-.75m-6 3.75 3 3m0 0 3-3m-3 3V1.5" />
          </svg>
          Replace
        </button>
      </div>
    );
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
      onDragLeave={() => setDragActive(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`
        relative cursor-pointer rounded-xl border-2 border-dashed p-6 text-center
        transition-all duration-200
        ${dragActive
          ? "border-primary bg-blue-50/50"
          : "border-border hover:border-primary/40 hover:bg-surface-hover"
        }
        ${isUploading ? "pointer-events-none opacity-60" : ""}
      `}
    >
      {fileInput}

      <div className="flex flex-col items-center gap-2">
        <svg className="h-8 w-8 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0 3 3m-3-3-3 3M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775 5.25 5.25 0 0 1 10.233-2.33 3 3 0 0 1 3.758 3.848A3.752 3.752 0 0 1 18 19.5H6.75Z" />
        </svg>

        {isUploading ? (
          <p className="text-sm text-muted">Uploading...</p>
        ) : (
          <div>
            <p className="text-sm font-medium text-foreground">
              Drop your resume here or <span className="text-primary">browse</span>
            </p>
            <p className="text-xs text-muted mt-1">PDF or DOCX format</p>
          </div>
        )}
      </div>
    </div>
  );
}

function FileIcon({ filename }: { filename: string }) {
  const isPdf = filename.toLowerCase().endsWith(".pdf");
  return (
    <div className={`flex h-6 w-6 flex-shrink-0 items-center justify-center rounded ${
      isPdf ? "bg-red-100 text-red-600" : "bg-blue-100 text-blue-600"
    }`}>
      <span className="text-[9px] font-bold leading-none">
        {isPdf ? "PDF" : "DOC"}
      </span>
    </div>
  );
}
