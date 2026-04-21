/**
 * Single source of truth for the backend URL.
 *
 * Override via the ``NEXT_PUBLIC_API_URL`` env var at build time (e.g.
 * ``NEXT_PUBLIC_API_URL=https://api.example.com npm run build``).
 */
export const API_BASE: string =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Build an absolute API URL from a relative path like "/api/upload". */
export function apiUrl(path: string): string {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}
