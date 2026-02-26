import type { UploadResponse, ScoreResult, ProgressEvent, GenerateResult, RescoreResult } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function uploadResume(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Upload failed");
  }

  return res.json();
}

export function getFileUrl(fileId: string): string {
  return `${API_BASE}/api/files/${fileId}`;
}

export async function fetchJobDescription(url: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/fetch-jd`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch job description");
  }

  const data = await res.json();
  return data.text;
}

export async function scoreResume(
  fileId: string,
  jdText: string | null,
  jdUrl: string | null,
  onProgress: (event: ProgressEvent) => void,
  onComplete: (result: ScoreResult) => void,
  onError: (message: string) => void,
  provider?: string,
  model?: string,
): Promise<void> {
  const body: Record<string, string | null | undefined> = { file_id: fileId };
  if (jdText) body.jd_text = jdText;
  if (jdUrl) body.jd_url = jdUrl;
  if (provider) body.provider = provider;
  if (model) body.model = model;

  const res = await fetch(`${API_BASE}/api/score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Scoring failed");
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response stream");

  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim();
        continue;
      }
      if (line.startsWith("data:")) {
        const dataStr = line.slice(5).trim();
        if (!dataStr) continue;

        try {
          const data = JSON.parse(dataStr);

          if (currentEvent === "progress" || (data.step && data.message)) {
            onProgress(data as ProgressEvent);
          } else if (currentEvent === "complete" || data.report) {
            onComplete(data as ScoreResult);
          } else if (currentEvent === "error" || (data.message && !data.step)) {
            onError(data.message);
          }
        } catch {
          // skip unparseable lines
        }
        currentEvent = "";
      }
    }
  }
}

export async function generateResume(
  fileId: string,
  keywordChanges: Array<{
    original: string;
    recommended: string;
    context: string;
    reason: string;
  }>
): Promise<GenerateResult> {
  const res = await fetch(`${API_BASE}/api/generate-resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file_id: fileId,
      keyword_changes: keywordChanges,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Resume generation failed");
  }

  return res.json();
}

export async function rescoreResume(
  structuredResume: Record<string, unknown>,
  keywordChanges: Array<{
    original: string;
    recommended: string;
    context: string;
    reason: string;
  }>,
  jdText: string,
  provider?: string,
  model?: string,
): Promise<RescoreResult> {
  const body: Record<string, unknown> = {
    structured_resume: structuredResume,
    keyword_changes: keywordChanges,
    jd_text: jdText,
  };
  if (provider) body.provider = provider;
  if (model) body.model = model;

  const res = await fetch(`${API_BASE}/api/rescore`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Rescoring failed");
  }

  return res.json();
}
