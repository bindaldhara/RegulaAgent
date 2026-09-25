import { AnimatePresence, motion } from "motion/react";
import type { ReactNode } from "react";
import type { PatientProfile } from "../types/auth";
import type { AgentRunResponse } from "../types/agent";
import { profileNameWithContact } from "../lib/profileContact";
import { formatIntent, formatRisk, formatStepStatus } from "../lib/formatters";
import { fadeUp, springSnappy, staggerContainer } from "../motion/presets";
import { GlassCard } from "./GlassCard";
import { StatusBadge } from "./StatusBadge";
import { ThinkingIndicator } from "./ThinkingIndicator";

interface RuntimePanelProps {
  lastRun: AgentRunResponse | null;
  loading: boolean;
  patient?: PatientProfile | null;
}

function Metric({
  label,
  children,
  className = "",
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      className={`rounded-xl border border-white/5 bg-black/30 p-3 ${className}`}
      variants={fadeUp}
    >
      <p className="text-[10px] font-medium uppercase tracking-wider text-ms-muted">{label}</p>
      <div className="mt-1.5 text-sm">{children}</div>
    </motion.div>
  );
}

function StepStatus({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
          ok ? "bg-emerald-500/20 text-emerald-300" : "bg-zinc-700/50 text-zinc-500"
        }`}
        aria-hidden
      >
        {ok ? "✓" : "·"}
      </span>
      <span className={`text-sm ${ok ? "text-zinc-200" : "text-zinc-500"}`}>{label}</span>
    </div>
  );
}

function executionLabel(lastRun: AgentRunResponse): string {
  if (lastRun.tool_result?.status === "deferred") {
    return "Waiting on scheduling API (demo)";
  }
  if (lastRun.tool_result) return "Completed";
  if (lastRun.proposed_action && lastRun.policy?.outcome === "ALLOW") {
    return "Not started";
  }
  if (lastRun.policy?.outcome === "DENY") return "Blocked by policy";
  return "—";
}

export function RuntimePanel({ lastRun, loading, patient }: RuntimePanelProps) {
  return (
    <AnimatePresence mode="wait">
      {loading && (
        <motion.div key="load" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <GlassCard className="p-5">
            <ThinkingIndicator />
            <p className="mt-2 text-sm text-ms-muted">Running workflow…</p>
          </GlassCard>
        </motion.div>
      )}

      {!loading && !lastRun && (
        <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={springSnappy}>
          <GlassCard className="p-5">
            <p className="text-sm text-ms-muted">
              After you send a message, you&apos;ll see policy, intent, and tool status here.
            </p>
          </GlassCard>
        </motion.div>
      )}

      {!loading && lastRun && (
        <motion.div
          key={lastRun.run_id}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={springSnappy}
        >
          <GlassCard className="p-4" glow={lastRun.policy?.outcome === "ESCALATE" ? "violet" : "none"}>
            <div className="mb-4 border-b border-white/5 pb-3">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-ms-muted">This response</h2>
              <p className="mt-1 text-sm text-zinc-300">
                {patient ? profileNameWithContact(patient) : "Guest session"}
              </p>
              <p className="mt-0.5 text-[10px] text-zinc-600" title={lastRun.run_id}>
                Ref {lastRun.run_id.slice(0, 8)}
              </p>
            </div>

            <motion.div
              className="grid grid-cols-1 gap-2 sm:grid-cols-2"
              variants={staggerContainer(0.04)}
              initial="hidden"
              animate="visible"
            >
              <Metric label="Intent" className="sm:col-span-2">
                {lastRun.intent ? (
                  <div>
                    <p className="text-sm font-medium leading-snug text-zinc-100">
                      {formatIntent(lastRun.intent.intent)}
                    </p>
                    <p className="mt-1 text-[11px] text-zinc-500">
                      {(lastRun.intent.confidence * 100).toFixed(0)}% confidence
                    </p>
                  </div>
                ) : (
                  "—"
                )}
              </Metric>

              <Metric label="Policy">
                {lastRun.policy ? (
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[10px] text-zinc-600">Decision</span>
                      <StatusBadge label={lastRun.policy.outcome} tone={lastRun.policy.outcome} />
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[10px] text-zinc-600">Risk</span>
                      <StatusBadge
                        label={formatRisk(lastRun.policy.risk_level)}
                        tone={lastRun.policy.risk_level}
                      />
                    </div>
                    <p className="text-[11px] leading-snug text-zinc-500">{lastRun.policy.reason}</p>
                  </div>
                ) : (
                  "—"
                )}
              </Metric>

              <Metric label="Access">
                <div className="space-y-2">
                  <StepStatus
                    ok={lastRun.identity_status === "verified"}
                    label={
                      lastRun.identity_status === "verified"
                        ? "Signed in"
                        : formatStepStatus(lastRun.identity_status)
                    }
                  />
                  <StepStatus
                    ok={lastRun.consent_status === "granted"}
                    label={
                      lastRun.consent_status === "granted"
                        ? "Scheduling consent"
                        : lastRun.consent_status === "not_required"
                          ? "Consent not required"
                          : "Consent needed"
                    }
                  />
                </div>
              </Metric>

              <Metric label="Tool" className="sm:col-span-2">
                {lastRun.proposed_action ? (
                  <div>
                    <code className="rounded-md bg-black/40 px-2 py-0.5 text-xs text-cyan-300">
                      {lastRun.proposed_action.tool_name}
                    </code>
                    <p className="mt-1.5 text-[11px] text-zinc-500">{executionLabel(lastRun)}</p>
                  </div>
                ) : (
                  <p className="text-zinc-500">No tool proposed</p>
                )}
              </Metric>
            </motion.div>

            {lastRun.proposed_action &&
              Object.keys(lastRun.proposed_action.arguments).length > 0 && (
                <motion.details className="mt-3 group" variants={fadeUp}>
                  <summary className="cursor-pointer text-[10px] font-medium uppercase tracking-wider text-zinc-600 hover:text-zinc-400">
                    Tool arguments
                  </summary>
                  <pre className="mt-2 max-h-24 overflow-auto rounded-xl border border-white/5 bg-black/50 p-2 text-[10px] text-zinc-500">
                    {JSON.stringify(lastRun.proposed_action.arguments, null, 2)}
                  </pre>
                </motion.details>
              )}

            {lastRun.handoff_state === "queued" && (
              <p className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2 py-1.5 text-[11px] text-amber-100">
                Human handoff queued — do not continue automated scheduling.
              </p>
            )}
          </GlassCard>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
