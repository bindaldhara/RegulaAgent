import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useRef } from "react";
import type { ChatMessage, WorkflowStep } from "../types/agent";
import { slideFromLeft, slideFromRight, springSnappy } from "../motion/presets";
import { GlassCard } from "./GlassCard";
import { PromptPills } from "./PromptPills";
import { ThinkingIndicator } from "./ThinkingIndicator";
import { WorkflowPills } from "./WorkflowPills";

interface ChatPanelProps {
  messages: ChatMessage[];
  draft: string;
  onDraftChange: (value: string) => void;
  onSend: () => void;
  loading: boolean;
  error: string | null;
  currentStep?: WorkflowStep;
}

export function ChatPanel({
  messages,
  draft,
  onDraftChange,
  onSend,
  loading,
  error,
  currentStep,
}: ChatPanelProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth" });
  }, [messages, loading, reduce]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.trim() || loading) return;
    onSend();
  }

  return (
    <GlassCard className="flex min-h-0 flex-1 flex-col" glow="cyan">
      <div className="relative border-b border-white/5 px-4 py-4">
        <h2 className="text-base font-semibold text-white">Patient chat</h2>
        <p className="text-xs text-ms-muted">Copy a prompt or type below</p>
      </div>

      <WorkflowPills currentStep={currentStep} />

      <PromptPills onSelect={onDraftChange} disabled={loading} />

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        <AnimatePresence mode="popLayout">
          {messages.length === 0 && (
            <motion.p
              key="empty"
              className="py-8 text-center text-sm text-ms-muted"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              No messages yet — pick a pill above or send your own.
            </motion.p>
          )}
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              layout
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              variants={msg.role === "user" ? slideFromRight : slideFromLeft}
              initial="hidden"
              animate="visible"
              transition={springSnappy}
            >
              <div
                className={`max-w-[88%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "ms-gradient-cta font-medium"
                    : "border border-white/10 bg-black/40 text-zinc-100 whitespace-pre-wrap"
                }`}
              >
                {msg.content}
              </div>
            </motion.div>
          ))}
          {loading && <ThinkingIndicator key="thinking" />}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      <AnimatePresence>
        {error && (
          <motion.div
            className="mx-4 mb-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      <form onSubmit={handleSubmit} className="border-t border-white/5 p-4">
        <div className="flex gap-2">
          <input
            value={draft}
            onChange={(e) => onDraftChange(e.target.value)}
            disabled={loading}
            placeholder="Describe what you need…"
            className="min-w-0 flex-1 rounded-full border border-white/10 bg-black/50 px-5 py-3 text-sm text-white outline-none placeholder:text-zinc-600 focus:border-violet-400/40 disabled:opacity-50"
          />
          <motion.button
            type="submit"
            disabled={loading || !draft.trim()}
            className="ms-gradient-cta rounded-full px-6 py-3 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            Send →
          </motion.button>
        </div>
      </form>
    </GlassCard>
  );
}
