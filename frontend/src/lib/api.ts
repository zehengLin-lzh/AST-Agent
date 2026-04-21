import type { UploadResponse, ScoreResult, ProgressEvent, GenerateResult, RescoreResult } from "@/types";
import { API_BASE } from "@/lib/config";

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

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Per the SSE spec, events are separated by a blank line (``\n\n`` or
    // ``\r\n\r\n``).  Split on that boundary and keep the trailing partial
    // event in ``buffer`` until the next chunk arrives.
    let boundary: number;
    while ((boundary = buffer.search(/\r?\n\r?\n/)) !== -1) {
      const match = buffer.match(/\r?\n\r?\n/)!;
      const raw = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + match[0].length);
      handleSSEEvent(raw, onProgress, onComplete, onError);
    }
  }

  // Final flush in case the stream ends without a trailing blank line.
  if (buffer.trim()) {
    handleSSEEvent(buffer, onProgress, onComplete, onError);
  }
}


function handleSSEEvent(
  raw: string,
  onProgress: (event: ProgressEvent) => void,
  onComplete: (result: ScoreResult) => void,
  onError: (message: string) => void,
): void {
  let eventName = "";
  const dataLines: string[] = [];

  for (const line of raw.split(/\r?\n/)) {
    if (!line || line.startsWith(":")) continue;  // comments per SSE spec
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }

  if (!dataLines.length) return;

  let data: unknown;
  try {
    data = JSON.parse(dataLines.join("\n"));
  } catch {
    return;  // malformed JSON payload — ignore
  }

  const d = data as { step?: string; message?: string; report?: unknown };
  if (eventName === "progress" || (d.step && d.message)) {
    onProgress(data as ProgressEvent);
  } else if (eventName === "complete" || d.report) {
    onComplete(data as ScoreResult);
  } else if (eventName === "error" || (d.message && !d.step)) {
    onError(d.message ?? "Unknown error");
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
