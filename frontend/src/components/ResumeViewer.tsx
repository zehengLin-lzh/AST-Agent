"use client";

import { useState, useEffect, useCallback } from "react";
import type { KeywordChange } from "@/types";

interface Props {
  fileUrl: string | null;
  fileType: "pdf" | "docx" | null;
  keywordChanges: KeywordChange[];
}

function highlightKeywords(html: string, changes: KeywordChange[]): string {
  let result = html;
  for (const change of changes) {
    if (!change.original) continue;
    const escaped = change.original.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const regex = new RegExp(`(${escaped})`, "gi");
    result = result.replace(
      regex,
      `<span class="keyword-highlight" title="Suggested: ${change.recommended}\n${change.reason}">$1</span>`
    );
  }
  return result;
}

export default function ResumeViewer({ fileUrl, fileType, keywordChanges }: Props) {
  const [docxHtml, setDocxHtml] = useState<string | null>(null);
  const [pdfComponent, setPdfComponent] = useState<React.ReactNode>(null);
  const [loading, setLoading] = useState(false);

  const loadDocx = useCallback(async (url: string) => {
    setLoading(true);
    try {
      const mammoth = await import("mammoth");
      const res = await fetch(url);
      const arrayBuffer = await res.arrayBuffer();
      const result = await mammoth.convertToHtml({ arrayBuffer });
      setDocxHtml(result.value);
    } catch (err) {
      console.error("Failed to render DOCX:", err);
      setDocxHtml("<p>Failed to load document.</p>");
    } finally {
      setLoading(false);
    }
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
            loading={<LoadingSpinner />}
          >
            {Array.from({ length: numPages }, (_, i) => (
              <Page
                key={i}
                pageNumber={i + 1}
                width={540}
                renderTextLayer={true}
                renderAnnotationLayer={false}
              />
            ))}
          </Document>
        );
      };

      setPdfComponent(<PdfViewer />);
    } catch (err) {
      console.error("Failed to render PDF:", err);
      setPdfComponent(<p className="text-danger">Failed to load PDF.</p>);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!fileUrl || !fileType) return;
    setDocxHtml(null);
    setPdfComponent(null);

    if (fileType === "docx") {
      loadDocx(fileUrl);
    } else {
      loadPdf(fileUrl);
    }
  }, [fileUrl, fileType, loadDocx, loadPdf]);

  if (!fileUrl) {
    return (
      <div className="flex h-full items-center justify-center text-muted">
        <div className="text-center">
          <svg className="mx-auto h-16 w-16 mb-3 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
          </svg>
          <p className="text-sm">Upload a resume to preview it here</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return <LoadingSpinner />;
  }

  if (fileType === "docx" && docxHtml) {
    const highlighted = keywordChanges.length > 0
      ? highlightKeywords(docxHtml, keywordChanges)
      : docxHtml;

    return (
      <div
        className="prose prose-sm max-w-none p-6"
        dangerouslySetInnerHTML={{ __html: highlighted }}
      />
    );
  }

  if (fileType === "pdf" && pdfComponent) {
    return <div className="p-4">{pdfComponent}</div>;
  }

  return null;
}

function LoadingSpinner() {
  return (
    <div className="flex h-32 items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
    </div>
  );
}
