import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const supabaseConfigured = Boolean(url?.trim() && anonKey?.trim());

export const supabase = supabaseConfigured
  ? createClient(url!, anonKey!, {
      auth: {
        persistSession: false,
        autoRefreshToken: true,
        storage: window.sessionStorage,
      },
    })
  : null;
