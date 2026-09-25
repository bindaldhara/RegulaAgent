import type { PatientProfile } from "../types/auth";

/** Email or phone — whichever matches how the user signed in. */
export function profileContactLine(patient: PatientProfile): string {
  if (patient.auth_via === "phone" && patient.phone) {
    return patient.phone;
  }
  if (patient.auth_via === "email" && patient.email) {
    return patient.email;
  }
  return patient.email ?? patient.phone ?? "Signed in";
}

export function profileContactLabel(patient: PatientProfile): string {
  if (patient.auth_via === "phone") return "Phone";
  if (patient.auth_via === "email") return "Email";
  return "Contact";
}

/** e.g. "Jane Doe · jane@example.com" or "Jane Doe · +1555010001" */
export function profileNameWithContact(patient: PatientProfile): string {
  const contact = profileContactLine(patient);
  if (contact === "Signed in") {
    return patient.full_name;
  }
  return `${patient.full_name} · ${contact}`;
}

/** Second line under the name in the sign-in card. */
export function profileSignedInDetail(patient: PatientProfile): string {
  const label = profileContactLabel(patient).toLowerCase();
  return `Signed in with ${label} · ${profileContactLine(patient)}`;
}
