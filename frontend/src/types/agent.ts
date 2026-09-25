export type Intent =
  | "BOOK_APPOINTMENT"
  | "CANCEL_APPOINTMENT"
  | "SEARCH_DOCTOR"
  | "CHECK_APPOINTMENT"
  | "UNKNOWN";

export type WorkflowStep =
  | "intent"
  | "identity"
  | "consent"
  | "action"
  | "policy"
  | "tool"
  | "result_validation"
  | "response"
  | "audit"
  | "handoff"
  | "end";

export type PolicyOutcome = "ALLOW" | "DENY" | "ESCALATE";
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type IdentityStatus = "unverified" | "pending" | "verified";
export type ConsentStatus = "not_required" | "pending" | "granted" | "denied";
export type HandoffState = "none" | "queued" | "active";

export interface ExtractedEntities {
  specialty?: string | null;
  doctor_name?: string | null;
  date?: string | null;
  slot?: string | null;
  appointment_id?: string | null;
}

export interface IntentClassification {
  intent: Intent;
  confidence: number;
  entities: ExtractedEntities;
  assistant_reply: string;
  is_emergency: boolean;
}

export interface ProposedAction {
  tool_name: string;
  arguments: Record<string, unknown>;
  risk_level: RiskLevel;
}

export interface PolicyDecision {
  outcome: PolicyOutcome;
  risk_level: RiskLevel;
  reason: string;
}

export interface AgentRunRequest {
  message: string;
  conversation_id?: string | null;
  patient_id?: string | null;
  identity_verified?: boolean;
  consent_granted?: boolean;
}

export interface AgentRunResponse {
  conversation_id: string;
  run_id: string;
  reply: string;
  current_step: WorkflowStep;
  intent: IntentClassification | null;
  identity_status: IdentityStatus;
  consent_status: ConsentStatus;
  policy: PolicyDecision | null;
  proposed_action: ProposedAction | null;
  tool_result: Record<string, unknown> | null;
  handoff_state: HandoffState;
  audit_event_count: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  runId?: string;
}
