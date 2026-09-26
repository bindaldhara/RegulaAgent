import { motion } from "motion/react";
import { useCallback, useEffect, useState } from "react";
import { runAgent } from "./api/agent";
import { signOut } from "./api/auth";
import { AmbientBackground } from "./components/AmbientBackground";
import { ChatPanel } from "./components/ChatPanel";
import { HeroStrip } from "./components/HeroStrip";
import { LoginPanel } from "./components/LoginPanel";
import { RuntimePanel } from "./components/RuntimePanel";
import { SiteHeader } from "./components/SiteHeader";
import { clearAccessToken } from "./lib/authStorage";
import { supabase } from "./lib/supabase";
import { profileNameWithContact } from "./lib/profileContact";
import { fadeUp, staggerContainer } from "./motion/presets";
import type { PatientProfile } from "./types/auth";
import type { AgentRunResponse, ChatHistoryTurn, ChatMessage, WorkflowStep } from "./types/agent";

function newId() {
  return crypto.randomUUID();
}

export default function App() {
  const [patient, setPatient] = useState<PatientProfile | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<AgentRunResponse | null>(null);
  const [currentStep, setCurrentStep] = useState<WorkflowStep | undefined>();

  useEffect(() => {
    clearAccessToken();
    setPatient(null);
    if (supabase) {
      void supabase.auth.signOut({ scope: "local" });
    }
  }, []);

  const chatHistory: ChatHistoryTurn[] = messages.map((m) => ({
    role: m.role,
    content: m.content,
  }));

  const applyAgentResponse = useCallback((response: AgentRunResponse) => {
      setConversationId(response.conversation_id);
      setLastRun(response);
      setCurrentStep(response.current_step);
      setMessages((prev) => [
        ...prev,
        { id: newId(), role: "assistant", content: response.reply, runId: response.run_id },
      ]);
    },
    [],
  );

  const sendMessage = useCallback(async () => {
    const text = draft.trim();
    if (!text || loading) return;
    if (!patient) {
      setError("Sign in to send messages.");
      return;
    }

    setError(null);
    setDraft("");
    setLoading(true);

    setMessages((prev) => [...prev, { id: newId(), role: "user", content: text }]);

    try {
      const response = await runAgent({
        message: text,
        conversation_id: conversationId,
        chat_history: [...chatHistory, { role: "user", content: text }],
      });
      applyAgentResponse(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }, [applyAgentResponse, chatHistory, conversationId, draft, loading, patient]);

  const handleVoiceTurn = useCallback(
    (payload: {
      userMessage: string;
      reply: string;
      conversationId?: string;
      run?: Partial<AgentRunResponse>;
    }) => {
      setMessages((prev) => {
        let next = prev;
        if (payload.userMessage) {
          const last = next[next.length - 1];
          const hasUser = last?.role === "user" && last.content === payload.userMessage;
          next = hasUser
            ? next
            : [...next, { id: newId(), role: "user" as const, content: payload.userMessage }];
        }
        const lastAfter = next[next.length - 1];
        if (lastAfter?.role === "assistant" && lastAfter.content === payload.reply) {
          return next;
        }
        return [...next, { id: newId(), role: "assistant" as const, content: payload.reply }];
      });
      if (payload.conversationId) {
        setConversationId(payload.conversationId);
      }
      const voiceRun = payload.run;
      const hasRuntimeUpdate =
        voiceRun &&
        (voiceRun.run_id ||
          voiceRun.policy ||
          voiceRun.intent?.intent ||
          voiceRun.proposed_action ||
          voiceRun.tool_result);
      if (hasRuntimeUpdate && voiceRun) {
        const patch = Object.fromEntries(
          Object.entries(voiceRun).filter(([, v]) => v !== undefined && v !== null),
        ) as Partial<AgentRunResponse>;
        setLastRun((prev) => {
          const base = prev ?? {
            conversation_id: payload.conversationId ?? "",
            run_id: voiceRun.run_id ?? `voice-${crypto.randomUUID()}`,
            reply: payload.reply,
            current_step: voiceRun.current_step ?? "response",
            identity_status: patient ? "verified" : "unverified",
            consent_status: patient?.consent_granted ? "granted" : "pending",
            handoff_state: "none",
            audit_event_count: 0,
            intent: null,
            policy: null,
            proposed_action: null,
            tool_result: null,
          };
          return {
            ...base,
            ...patch,
            reply: payload.reply,
            run_id: voiceRun.run_id ?? base.run_id,
            identity_status:
              voiceRun.identity_status ?? base.identity_status ?? (patient ? "verified" : "unverified"),
            consent_status:
              voiceRun.consent_status ??
              base.consent_status ??
              (patient?.consent_granted ? "granted" : "pending"),
          } as AgentRunResponse;
        });
      }
      if (payload.run?.current_step) {
        setCurrentStep(payload.run.current_step);
      }
    },
    [patient],
  );

  const startNewConversation = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setLastRun(null);
    setCurrentStep(undefined);
    setError(null);
    setDraft("");
  }, []);

  const handleAuthenticated = useCallback(
    (profile: PatientProfile, options?: { resetChat?: boolean }) => {
      if (options?.resetChat) {
        startNewConversation();
      }
      setPatient(profile);
    },
    [startNewConversation],
  );

  const handleSignOut = () => {
    startNewConversation();
    void signOut().finally(() => {
      clearAccessToken();
      setPatient(null);
    });
  };

  const headerLabel = patient ? profileNameWithContact(patient) : "Guest · sign in to book";

  return (
    <div className="relative min-h-screen text-zinc-100">
      <AmbientBackground />
      <SiteHeader providerLabel={headerLabel} onSignOut={patient ? handleSignOut : undefined} />
      <HeroStrip />

      <motion.main
        className="relative z-10 mx-auto grid max-w-7xl gap-4 px-4 pb-10 pt-4 md:px-6 lg:grid-cols-12"
        variants={staggerContainer(0.08, 0.05)}
        initial="hidden"
        animate="visible"
      >
        <motion.div className="flex flex-col gap-4 lg:col-span-3" variants={fadeUp}>
          <LoginPanel
            patient={patient}
            onAuthenticated={handleAuthenticated}
            onLogout={handleSignOut}
            onNewConversation={startNewConversation}
          />
        </motion.div>

        <motion.div className="flex min-h-[min(70vh,720px)] flex-col lg:col-span-6" variants={fadeUp}>
          <ChatPanel
            messages={messages}
            draft={draft}
            onDraftChange={setDraft}
            onSend={sendMessage}
            loading={loading}
            error={error}
            currentStep={currentStep}
            signedIn={Boolean(patient)}
            consentGranted={Boolean(patient?.consent_granted)}
            conversationId={conversationId}
            chatHistory={chatHistory}
            onVoiceTurn={handleVoiceTurn}
          />
        </motion.div>

        <motion.div className="lg:col-span-3" variants={fadeUp}>
          <RuntimePanel lastRun={lastRun} loading={loading} patient={patient} />
        </motion.div>
      </motion.main>
    </div>
  );
}
