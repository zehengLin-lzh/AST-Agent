export interface UploadResponse {
  file_id: string;
  filename: string;
  page_count: number;
  file_type: "pdf" | "docx";
}

export interface KeywordChange {
  original: string;
  recommended: string;
  context: string;
  reason: string;
}

export interface JDKeyword {
  keyword: string;
  category: string;
  found_in_resume: boolean;
  added_via_recommendation: boolean;
  notes: string;
}

export interface ScoreBreakdown {
  skills: number;
  experience: number;
  qualifications: number;
  soft_skills: number;
  tools: number;
}

export interface ATSScoreReport {
  overall_score: number;
  score_breakdown: ScoreBreakdown;
  summary: string;
  keyword_changes: KeywordChange[];
  jd_keywords: JDKeyword[];
  missing_critical_keywords: string[];
  strengths: string[];
  gaps: string[];
}

export interface ScoreResult {
  report: ATSScoreReport;
  structured_resume: Record<string, unknown>;
}

export interface ProgressEvent {
  step: string;
  message: string;
}

export interface ProviderInfo {
  id: string;
  label: string;
  models: string[];
  default_model: string;
  configured: boolean;
}

export interface LLMSelection {
  provider: string;
  model: string;
}

export interface LearningSuggestion {
  skill: string;
  priority: "high" | "medium" | "low";
  reason: string;
  resources: string;
}

export interface RescoreResult {
  report: ATSScoreReport;
  learning_suggestions: LearningSuggestion[];
}

export interface GenerateResult {
  file_id: string;
}
