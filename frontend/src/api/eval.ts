import type { EvalCaseSummary, EvalRunResponse, EvalStatus } from "../types/eval";

export async function fetchEvalStatus(): Promise<EvalStatus> {
  const response = await fetch("/api/v1/admin/eval/status");
  if (!response.ok) {
    throw new Error(`Eval status failed (${response.status})`);
  }
  return response.json() as Promise<EvalStatus>;
}

export async function fetchEvalCases(): Promise<EvalCaseSummary[]> {
  const response = await fetch("/api/v1/admin/eval/cases");
  if (!response.ok) {
    throw new Error(`Eval cases failed (${response.status})`);
  }
  return response.json() as Promise<EvalCaseSummary[]>;
}

export async function runEvalCase(caseId: string): Promise<EvalRunResponse> {
  const response = await fetch(`/api/v1/admin/eval/cases/${encodeURIComponent(caseId)}/run`, {
    method: "POST",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Eval run failed (${response.status})`);
  }
  return response.json() as Promise<EvalRunResponse>;
}
