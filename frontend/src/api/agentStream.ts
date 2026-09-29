import { runAgent } from "./agent";
import { authHeaders } from "../lib/authStorage";
import { streamApiUrl } from "../lib/apiBase";
import type { AgentRunRequest, AgentRunResponse, WorkflowStep } from "../types/agent";

export interface AgentStreamHandlers {
  onStep?: (step: WorkflowStep) => void;
  onStatus?: (message: string) => void;
  onToken: (text: string) => void;
  onDone: (response: AgentRunResponse) => void;
  onError?: (message: string) => void;
}

const STEP_STATUS: Partial<Record<WorkflowStep, string>> = {
  intent: "Understanding your request…",
  identity: "Checking sign-in…",
  consent: "Checking scheduling consent…",
  action: "Choosing next action…",
  policy: "Applying policy…",
  tool: "Looking up appointments…",
  result_validation: "Validating result…",
  response: "Preparing reply…",
  audit: "Finishing up…",
  handoff: "Connecting you to a clinician…",
};

function parseSseBlock(block: string): { event: string; data: string } | null {
  const lines = block.split("\n");
  let event = "message";
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith(":")) {
      continue;
    }
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    }
  }
  if (dataLines.length === 0) {
    return null;
  }
  return { event, data: dataLines.join("\n") };
}

function nextPaint(): Promise<void> {
  return new Promise((resolve) => {
    requestAnimationFrame(() => resolve());
  });
}

async function dispatchSseBlock(
  block: string,
  handlers: AgentStreamHandlers,
  state: { gotDone: boolean },
): Promise<void> {
  const trimmed = block.trim();
  if (!trimmed) {
    return;
  }
  const parsed = parseSseBlock(trimmed);
  if (!parsed) {
    return;
  }
  const payload = JSON.parse(parsed.data) as Record<string, unknown>;
  if (parsed.event === "step" && typeof payload.step === "string") {
    const step = payload.step as WorkflowStep;
    handlers.onStep?.(step);
    const label = STEP_STATUS[step];
    if (label) {
      handlers.onStatus?.(label);
    }
  } else if (parsed.event === "status" && typeof payload.message === "string") {
    handlers.onStatus?.(payload.message);
  } else if (parsed.event === "token" && typeof payload.text === "string") {
    handlers.onToken(payload.text);
    await nextPaint();
  } else if (parsed.event === "done") {
    state.gotDone = true;
    handlers.onDone(payload as unknown as AgentRunResponse);
  } else if (parsed.event === "error" && typeof payload.message === "string") {
    handlers.onError?.(payload.message);
    throw new Error(payload.message);
  }
}

async function consumeSseBuffer(
  buffer: string,
  handlers: AgentStreamHandlers,
  state: { gotDone: boolean },
): Promise<string> {
  const parts = buffer.split("\n\n");
  const remainder = parts.pop() ?? "";
  for (const part of parts) {
    await dispatchSseBlock(part, handlers, state);
  }
  return remainder;
}

async function runAgentStreamSse(
  request: AgentRunRequest,
  handlers: AgentStreamHandlers,
): Promise<void> {
  const url = streamApiUrl("/api/v1/agent/run/stream");
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(request),
  });

  if (response.status === 404) {
    throw new Error("STREAM_NOT_AVAILABLE");
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Streaming not supported in this browser");
  }

  const decoder = new TextDecoder();
  let buffer = "";
  const state = { gotDone: false };

  while (true) {
    const { done, value } = await reader.read();
    if (value) {
      buffer += decoder.decode(value, { stream: true });
      buffer = await consumeSseBuffer(buffer, handlers, state);
    }
    if (done) {
      buffer += decoder.decode();
      if (buffer.trim()) {
        await dispatchSseBlock(buffer, handlers, state);
      }
      break;
    }
  }

  if (!state.gotDone) {
    throw new Error("Stream ended without a done event");
  }
}

/** Non-streaming fallback when SSE is unavailable (e.g. old API build). */
async function runAgentFallback(
  request: AgentRunRequest,
  handlers: AgentStreamHandlers,
): Promise<void> {
  const response = await runAgent(request);
  if (response.reply) {
    handlers.onToken(response.reply);
  }
  handlers.onDone(response);
}

export async function runAgentStream(
  request: AgentRunRequest,
  handlers: AgentStreamHandlers,
): Promise<void> {
  try {
    await runAgentStreamSse(request, handlers);
  } catch (err) {
    if (err instanceof Error && err.message === "STREAM_NOT_AVAILABLE") {
      await runAgentFallback(request, handlers);
      return;
    }
    throw err;
  }
}
