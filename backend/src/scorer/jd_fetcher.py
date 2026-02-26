"""Fetch and extract clean text from a job description URL.

Handles common job boards (LinkedIn, Indeed, Greenhouse, Lever, etc.)
by stripping navigation, scripts, styles, and boilerplate — keeping only
the meaningful job-description content.

LinkedIn strategy:
    LinkedIn serves JD content in two ways that work without authentication:
    1. ``/jobs/view/{id}`` — full public page with ``.description__text``
    2. ``/jobs-guest/jobs/api/jobPosting/{id}`` — lightweight guest API

    We try the guest API first (smaller payload, faster), then fall back
    to the regular page, then to generic extraction.
"""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup, Tag

log = logging.getLogger(__name__)

_TIMEOUT = 20
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_STRIP_TAGS = frozenset({
    "script", "style", "noscript", "svg", "img", "video", "audio",
    "iframe", "nav", "footer", "header", "aside", "form", "button",
})

_LINKEDIN_SELECTORS = [
    ".description__text",
    ".show-more-less-html__markup",
    ".decorated-job-posting__details",
]

_GENERIC_JD_SELECTORS = [
    '[class*="job-description"]',
    '[class*="jobDescription"]',
    '[class*="job_description"]',
    '[class*="job-details"]',
    '[class*="jobDetails"]',
    '[class*="posting-requirements"]',
    '[id*="job-description"]',
    '[id*="jobDescription"]',
    '[id*="job_description"]',
    '[data-testid*="jobDescription"]',
    "article",
    '[role="main"]',
    "main",
]

_LINKEDIN_HOST_RE = re.compile(r"(^|\.)linkedin\.com$", re.IGNORECASE)
_LINKEDIN_JOB_ID_RE = re.compile(r"/jobs/(?:view/|collections/[^/]+/\?currentJobId=)(\d+)")


# ── public API ────────────────────────────────────────────────

def fetch_jd_from_url(url: str) -> str:
    """Fetch a URL and return the job description as clean plain text.

    Raises ``ConnectionError`` on network failure and ``ValueError``
    if no usable text can be extracted.
    """
    url = url.replace("\\", "")
    _validate_url(url)
    log.info("  Fetching job description from %s …", url)

    if _is_linkedin(url):
        text = _fetch_linkedin(url)
    else:
        html = _download(url)
        text = _extract_text_generic(html)

    if not text or len(text.split()) < 20:
        raise ValueError(
            f"Could not extract meaningful job description text from {url}. "
            "The page may require JavaScript or authentication. "
            "Try saving the page content as a .txt file and using --jd instead."
        )

    log.info("  Extracted %d words from job posting", len(text.split()))
    return text


# ── LinkedIn-specific ─────────────────────────────────────────

def _is_linkedin(url: str) -> bool:
    return bool(_LINKEDIN_HOST_RE.search(urlparse(url).netloc))


def _extract_linkedin_job_id(url: str) -> str | None:
    cleaned = url.replace("\\", "")
    m = _LINKEDIN_JOB_ID_RE.search(cleaned)
    if m:
        return m.group(1)
    m2 = re.search(r"currentJobId=(\d+)", cleaned)
    return m2.group(1) if m2 else None


def _fetch_linkedin(url: str) -> str:
    """Extract JD text from a LinkedIn job posting.

    Many LinkedIn URLs (e.g. ``/jobs/collections/…``) require login.
    We always resolve to a public route using the extracted job ID:

    1. Guest API (``/jobs-guest/jobs/api/jobPosting/{id}``) — fast, clean HTML
    2. Public view (``/jobs/view/{id}``) — heavier but still no auth
    3. JSON-LD on the public page
    4. Generic extraction as last resort
    """
    job_id = _extract_linkedin_job_id(url)

    if not job_id:
        raise ValueError(
            f"Could not extract a LinkedIn job ID from {url}. "
            "Please use a URL containing /jobs/view/<id> or ?currentJobId=<id>."
        )

    text = _try_linkedin_guest_api(job_id)
    if text:
        return text
    log.info("  Guest API didn't yield content, trying public /jobs/view/ …")

    public_url = f"https://www.linkedin.com/jobs/view/{job_id}"
    html = _download(public_url)
    soup = BeautifulSoup(html, "html.parser")

    if _is_login_wall(soup):
        raise ValueError(
            f"LinkedIn job {job_id} appears to require authentication. "
            "Try opening the job in a browser, copying the description text, "
            "and using --jd-text or saving it to a file with --jd."
        )

    text = _try_linkedin_selectors(soup)
    if text:
        return text

    text = _try_json_ld(soup)
    if text:
        return text

    log.info("  LinkedIn-specific extraction failed, falling back to generic…")
    return _extract_text_generic(html)


def _is_login_wall(soup: BeautifulSoup) -> bool:
    """Detect if LinkedIn redirected to a login/auth-wall page."""
    if soup.find("form", action=lambda v: v and "login" in v.lower()):
        return True
    title = soup.title.string if soup.title else ""
    if "sign in" in title.lower() or "log in" in title.lower():
        return True
    return False


def _try_linkedin_guest_api(job_id: str) -> str | None:
    api_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    log.info("  Trying LinkedIn guest API for job %s …", job_id)
    try:
        resp = httpx.get(
            api_url, headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True,
        )
        if resp.status_code != 200 or not resp.text:
            return None
    except httpx.HTTPError:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    text = _try_linkedin_selectors(soup)
    if text:
        title = _extract_linkedin_title(soup)
        criteria = _extract_linkedin_criteria(soup)
        parts = []
        if title:
            parts.append(title)
        parts.append(text)
        if criteria:
            parts.append(criteria)
        return "\n\n".join(parts)
    return None


def _try_linkedin_selectors(soup: BeautifulSoup) -> str | None:
    for selector in _LINKEDIN_SELECTORS:
        match = soup.select_one(selector)
        if match and len(match.get_text(strip=True)) > 50:
            return _tag_to_clean_text(match)
    return None


def _extract_linkedin_title(soup: BeautifulSoup) -> str | None:
    for selector in [".top-card-layout__title", "h1", "h2"]:
        el = soup.select_one(selector)
        if el:
            title = el.get_text(strip=True)
            company_el = soup.select_one(
                ".topcard__org-name-link, .top-card-layout__company-name, "
                ".top-card-layout__second-subline a"
            )
            company = company_el.get_text(strip=True) if company_el else ""
            if company:
                return f"{title} at {company}"
            return title
    return None


def _extract_linkedin_criteria(soup: BeautifulSoup) -> str | None:
    labels = soup.select(".description__job-criteria-subheader")
    values = soup.select(".description__job-criteria-text")
    if labels and values and len(labels) == len(values):
        lines = []
        for label, value in zip(labels, values):
            l_text = label.get_text(strip=True)
            v_text = value.get_text(strip=True)
            if v_text and v_text.lower() != "not applicable":
                lines.append(f"{l_text}: {v_text}")
        if lines:
            return "\n".join(lines)
    return None


def _try_json_ld(soup: BeautifulSoup) -> str | None:
    """Extract JD from JSON-LD structured data (Schema.org JobPosting)."""
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                desc = item.get("description", "")
                if desc:
                    desc_soup = BeautifulSoup(desc, "html.parser")
                    text = desc_soup.get_text(separator="\n", strip=True)
                    if len(text) > 50:
                        title = item.get("title", "")
                        org = ""
                        hiring = item.get("hiringOrganization")
                        if isinstance(hiring, dict):
                            org = hiring.get("name", "")
                        header = f"{title} at {org}" if org else title
                        return f"{header}\n\n{text}" if header else text
    return None


# ── generic extraction ────────────────────────────────────────

def _extract_text_generic(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    text = _try_json_ld(soup)
    if text:
        return text

    for tag_name in _STRIP_TAGS:
        for el in soup.find_all(tag_name):
            el.decompose()

    content = _find_jd_container(soup)
    if content is None:
        content = soup.body or soup

    return _tag_to_clean_text(content)


def _find_jd_container(soup: BeautifulSoup) -> Tag | None:
    for selector in _GENERIC_JD_SELECTORS:
        match = soup.select_one(selector)
        if match and len(match.get_text(strip=True)) > 100:
            return match
    return None


# ── shared helpers ────────────────────────────────────────────

def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Invalid URL scheme '{parsed.scheme}'. Only http/https supported."
        )
    if not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")


def _download(url: str) -> str:
    try:
        resp = httpx.get(
            url, headers=_HEADERS, timeout=_TIMEOUT, follow_redirects=True,
        )
        resp.raise_for_status()
    except httpx.ConnectError as exc:
        raise ConnectionError(f"Could not connect to {url}: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        raise ConnectionError(
            f"HTTP {exc.response.status_code} fetching {url}"
        ) from exc
    except httpx.TimeoutException as exc:
        raise ConnectionError(f"Timeout fetching {url}: {exc}") from exc
    return resp.text


def _tag_to_clean_text(tag: Tag) -> str:
    lines: list[str] = []
    for el in tag.descendants:
        if isinstance(el, str):
            text = el.strip()
            if text:
                lines.append(text)
        elif isinstance(el, Tag) and el.name in (
            "br", "p", "div", "li", "h1", "h2", "h3", "h4", "tr",
        ):
            lines.append("\n")
    return _collapse_whitespace(lines)


def _collapse_whitespace(lines: list[str]) -> str:
    raw = " ".join(lines)
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    paragraphs = [p.strip() for p in raw.split("\n") if p.strip()]
    return "\n".join(paragraphs)
