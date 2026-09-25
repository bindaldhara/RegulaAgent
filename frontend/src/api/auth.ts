import { authHeaders, setAccessToken } from "../lib/authStorage";
import type { AuthResponse, PatientProfile } from "../types/auth";

async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    if (data.detail) return typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
  } catch {
    /* ignore */
  }
  return `Request failed (${response.status})`;
}

export async function loginEmail(
  email: string,
  password: string,
  fullName: string,
): Promise<AuthResponse> {
  const response = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  const data = (await response.json()) as AuthResponse;
  setAccessToken(data.access_token);
  return data;
}

export async function requestOtp(phone: string): Promise<{ message: string; demo_code?: string }> {
  const response = await fetch("/api/v1/auth/otp/request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function verifyOtp(
  phone: string,
  code: string,
  fullName: string,
): Promise<AuthResponse> {
  const response = await fetch("/api/v1/auth/otp/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, code, full_name: fullName }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  const data = (await response.json()) as AuthResponse;
  setAccessToken(data.access_token);
  return data;
}

export async function fetchMe(): Promise<PatientProfile> {
  const response = await fetch("/api/v1/auth/me", { headers: { ...authHeaders() } });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function updateConsent(granted: boolean): Promise<AuthResponse> {
  const response = await fetch("/api/v1/auth/consent", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ granted }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  const data = (await response.json()) as AuthResponse;
  setAccessToken(data.access_token);
  return data;
}
