export function formatIntent(intent: string): string {
  return intent
    .split("_")
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(" ");
}

export function formatRisk(level: string): string {
  return level.charAt(0) + level.slice(1).toLowerCase();
}

export function formatStepStatus(value: string): string {
  return value
    .split("_")
    .map((w) => w.charAt(0) + w.slice(1).toLowerCase())
    .join(" ");
}
