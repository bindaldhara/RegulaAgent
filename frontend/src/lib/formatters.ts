export function formatIntent(intent: string | undefined | null): string {
  if (!intent) return "—";
  return intent
    .split("_")
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(" ");
}

export function formatRisk(level: string | undefined | null): string {
  if (!level) return "—";
  return level.charAt(0) + level.slice(1).toLowerCase();
}

export function formatStepStatus(value: string | undefined | null): string {
  if (!value) return "—";
  return value
    .split("_")
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(" ");
}
