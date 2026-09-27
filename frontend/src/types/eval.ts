export interface EvalCaseSummary {
  id: string;
  title: string;
  category: string;
  message: string;
}

export interface EvalStatus {
  deepeval_available: boolean;
  judge_configured: boolean;
  judge_model: string | null;
  case_count: number;
  agent_provider_for_eval: string;
}

export interface StructuralCheckResult {
  passed: boolean;
  expected_policy: string;
  actual_policy: string | null;
  expected_tool: string | null;
  actual_tool: string | null;
  tool_success_ok: boolean;
  details: string[];
}

export interface DeepEvalResult {
  passed: boolean;
  score: number | null;
  threshold: number;
  reason: string | null;
  error: string | null;
  required_for_pass: boolean;
}

export interface EvalRunResponse {
  case_id: string;
  passed: boolean;
  structural: StructuralCheckResult;
  deepeval: DeepEvalResult;
  reply: string;
  run_id: string;
  agent_snapshot: Record<string, unknown>;
}
