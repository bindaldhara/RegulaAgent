import { authHeaders } from "../lib/authStorage";
import type { ChatHistoryTurn } from "../types/agent";

export interface VoiceStatus {
  enabled: boolean;
  url: string | null;
  agent_name?: string;
}

export interface VoiceTokenResponse {
  token: string;
  url: string;
  room_name: string;
}

export async function fetchVoiceStatus(): Promise<VoiceStatus> {
  const response = await fetch("/api/v1/voice/status");
  if (!response.ok) {
    throw new Error("Could not load voice status");
  }
  return response.json() as Promise<VoiceStatus>;
}

export async function fetchVoiceToken(params: {
  conversation_id?: string | null;
  chat_history: ChatHistoryTurn[];
}): Promise<VoiceTokenResponse> {
  const response = await fetch("/api/v1/voice/token", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      conversation_id: params.conversation_id ?? null,
      chat_history: params.chat_history,
    }),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Voice token failed (${response.status})`);
  }
  return response.json() as Promise<VoiceTokenResponse>;
}

/** Wake Render free-tier voice worker before requesting a LiveKit token. */
export async function wakeProductionVoiceWorker(): Promise<void> {
  const wake = async (url: string) => {
    try {
      await fetch(url, { method: "GET", cache: "no-store" });
    } catch {
      /* cold start may abort; still helps Render spin up */
    }
  };
  await wake("https://regula-agent-api.onrender.com/health");
  await wake("https://regula-agent-voice.onrender.com/");
  await new Promise((resolve) => window.setTimeout(resolve, 10_000));
}
