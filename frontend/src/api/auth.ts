import { authHeaders, setAccessToken } from "../lib/authStorage";
import { supabase, supabaseConfigured } from "../lib/supabase";
import type { PatientProfile } from "../types/auth";

async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (data.detail) return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
  } catch {
    /* ignore */
  }
  return `Request failed (${response.status})`;
}

function requireSupabaseClient() {
  if (!supabaseConfigured || !supabase) {
    throw new Error("Supabase is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.");
  }
  return supabase;
}

async function persistSessionAccessToken() {
  const client = requireSupabaseClient();
  const { data } = await client.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error("No active session");
  setAccessToken(token);
  return token;
}

export async function syncProfile(fullName: string): Promise<PatientProfile> {
  await persistSessionAccessToken();
  const response = await fetch("/api/v1/auth/profile", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ full_name: fullName }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function signUpEmail(
  email: string,
  password: string,
  fullName: string,
): Promise<PatientProfile> {
  const client = requireSupabaseClient();
  const { data, error } = await client.auth.signUp({
    email,
    password,
    options: { data: { full_name: fullName } },
  });
  if (error) throw new Error(error.message);
  if (!data.session) {
    throw new Error(
      "Check your email to confirm your account, then sign in. (Or disable email confirmation in Supabase for local dev.)",
    );
  }
  setAccessToken(data.session.access_token);
  return syncProfile(fullName);
}

export async function loginEmail(
  email: string,
  password: string,
  fullName: string,
): Promise<PatientProfile> {
  const client = requireSupabaseClient();
  const { data, error } = await client.auth.signInWithPassword({ email, password });
  if (error) throw new Error(error.message);
  if (!data.session) throw new Error("Sign in failed");
  setAccessToken(data.session.access_token);
  return syncProfile(fullName);
}

export async function requestPhoneOtp(phone: string): Promise<void> {
  const client = requireSupabaseClient();
  const { error } = await client.auth.signInWithOtp({ phone });
  if (error) throw new Error(error.message);
}

export async function verifyPhoneOtp(
  phone: string,
  code: string,
  fullName: string,
): Promise<PatientProfile> {
  const client = requireSupabaseClient();
  const { data, error } = await client.auth.verifyOtp({
    phone,
    token: code,
    type: "sms",
  });
  if (error) throw new Error(error.message);
  if (!data.session) throw new Error("Verification failed");
  setAccessToken(data.session.access_token);
  return syncProfile(fullName);
}

export async function fetchMe(): Promise<PatientProfile> {
  const client = requireSupabaseClient();
  const { data } = await client.auth.getSession();
  if (data.session?.access_token) {
    setAccessToken(data.session.access_token);
  }
  const response = await fetch("/api/v1/auth/me", { headers: { ...authHeaders() } });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function updateConsent(granted: boolean): Promise<PatientProfile> {
  const response = await fetch("/api/v1/auth/consent", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ granted }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function signOut(): Promise<void> {
  if (supabase) {
    await supabase.auth.signOut();
  }
}
