import { authHeaders } from "../lib/authStorage";
import type { AgentRunRequest, AgentRunResponse } from "../types/agent";

export async function runAgent(request: AgentRunRequest): Promise<AgentRunResponse> {
  const response = await fetch("/api/v1/agent/run", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }

  return response.json() as Promise<AgentRunResponse>;
}
