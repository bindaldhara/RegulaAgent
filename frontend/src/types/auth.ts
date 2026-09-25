export type AuthVia = "email" | "phone";

export interface PatientProfile {
  patient_id: string;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  consent_granted: boolean;
  auth_via?: AuthVia | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  patient: PatientProfile;
}
