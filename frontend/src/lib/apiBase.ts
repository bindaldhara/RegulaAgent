/**
 * Base URL for API calls that must stream (SSE).
 * Vercel rewrites buffer external origins — set VITE_API_BASE_URL to your Render API
 * (e.g. https://regula-agent-api.onrender.com) so /run/stream chunks reach the browser.
 * Other /api routes can keep using same-origin /api (Vercel rewrite).
 */
export function streamApiUrl(path: string): string {
  const configured = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
  // Dev: bypass Vite proxy for SSE (proxy buffers until the workflow finishes).
  const base = (
    configured ||
    (import.meta.env.DEV ? "http://localhost:8000" : "")
  ).replace(/\/$/, "");
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return base ? `${base}${suffix}` : suffix;
}
