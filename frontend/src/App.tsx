import { motion } from "motion/react";
import { useCallback, useEffect, useState } from "react";
import { runAgent } from "./api/agent";
import { fetchMe, signOut } from "./api/auth";
import { AmbientBackground } from "./components/AmbientBackground";
import { ChatPanel } from "./components/ChatPanel";
import { HeroStrip } from "./components/HeroStrip";
import { LoginPanel } from "./components/LoginPanel";
import { RuntimePanel } from "./components/RuntimePanel";
import { SiteHeader } from "./components/SiteHeader";
import { clearAccessToken, getAccessToken } from "./lib/authStorage";
import { profileNameWithContact } from "./lib/profileContact";
import { fadeUp, staggerContainer } from "./motion/presets";
import type { PatientProfile } from "./types/auth";
import type { AgentRunResponse, ChatMessage, WorkflowStep } from "./types/agent";

function newId() {
  return crypto.randomUUID();
}

export default function App() {
  const [patient, setPatient] = useState<PatientProfile | null>(null);
  const [authLoading, setAuthLoading] = useState(true);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<AgentRunResponse | null>(null);
  const [currentStep, setCurrentStep] = useState<WorkflowStep | undefined>();

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      setAuthLoading(false);
      return;
    }
    fetchMe()
      .then(setPatient)
      .catch(() => setPatient(null))
      .finally(() => setAuthLoading(false));
  }, []);

  const sendMessage = useCallback(async () => {
    const text = draft.trim();
    if (!text || loading) return;

    setError(null);
    setDraft("");
    setLoading(true);

    setMessages((prev) => [...prev, { id: newId(), role: "user", content: text }]);

    try {
      const response = await runAgent({
        message: text,
        conversation_id: conversationId,
        chat_history: [
          ...messages.map((m) => ({ role: m.role, content: m.content })),
          { role: "user", content: text },
        ],
      });

      setConversationId(response.conversation_id);
      setLastRun(response);
      setCurrentStep(response.current_step);

      setMessages((prev) => [
        ...prev,
        { id: newId(), role: "assistant", content: response.reply, runId: response.run_id },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }, [conversationId, draft, loading]);

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

  const headerLabel = patient
    ? profileNameWithContact(patient)
    : authLoading
      ? "Checking session…"
      : "Guest · sign in to book";

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
          />
        </motion.div>

        <motion.div className="lg:col-span-3" variants={fadeUp}>
          <RuntimePanel lastRun={lastRun} loading={loading} patient={patient} />
        </motion.div>
      </motion.main>
    </div>
  );
}
