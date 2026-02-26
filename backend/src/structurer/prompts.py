"""Prompt templates used by :class:`~src.structurer.resume_structurer.ResumeStructurer`."""

SYSTEM_PROMPT = """\
You are a precise resume information extractor.
You receive resume text that has already been parsed from a PDF or DOCX file.
Your ONLY job is to return a single JSON object matching the schema below.
Never add commentary — return raw JSON only."""

USER_PROMPT_TEMPLATE = """\
Extract structured data from the following resume text.

--- RESUME TEXT ---
{resume_text}
--- END ---

Return a JSON object with EXACTLY this structure (use null for missing strings, [] for missing arrays):

{{
  "contactInfo": {{
    "name":        "Full name",
    "phoneNumber": "Phone number or null",
    "email":       "Email address or null",
    "linkedIn":    "LinkedIn URL or null",
    "location":    "City, State or null",
    "website":     "Personal website URL or null",
    "github":      "GitHub URL or null"
  }},
  "summary": "Professional summary / objective text or null",
  "experience": [
    {{
      "company":       "Company name",
      "role":          "Job title",
      "yearOfService": "Date range as written (e.g. Jan 2020 - Present)",
      "location":      "City, State or null",
      "highlight":     ["Achievement / bullet point 1", "..."]
    }}
  ],
  "skill": ["Individual skill 1", "Individual skill 2"],
  "education": [
    {{
      "name":   "University / school name",
      "degree": "Degree and major",
      "time":   "Date range as written"
    }}
  ],
  "projects": [
    {{
      "name":         "Project name",
      "description":  "Brief description or null",
      "technologies": ["Tech1", "Tech2"],
      "time":         "Date range or null",
      "highlight":    ["Detail 1", "..."]
    }}
  ],
  "certifications": [
    {{
      "name":   "Certification name",
      "issuer": "Issuing organisation or null",
      "time":   "Date or null"
    }}
  ],
  "awards": [
    {{
      "name":   "Award name",
      "issuer": "Issuing organisation or null",
      "time":   "Date or null"
    }}
  ],
  "languages": ["Language 1", "Language 2"],
  "additionalSections": {{
    "Section Name": "Content or structured data for any section not listed above"
  }}
}}

Rules:
1. Extract information EXACTLY as written — do not invent data.
2. Every experience bullet point / achievement is a separate string in "highlight".
3. Every individual skill is a separate string in "skill" (split comma-separated lists).
4. If a standard section is missing, keep its default (null or []).
5. Put any section that does not fit the above keys into "additionalSections"."""
