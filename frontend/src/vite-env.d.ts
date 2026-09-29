/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
  /** Optional: GCP (or other) voice worker wake URL, e.g. http://VM_IP:8080/ */
  readonly VITE_VOICE_WAKE_URL?: string;
  /** Direct Render API origin for SSE chat (required on Vercel production). */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
