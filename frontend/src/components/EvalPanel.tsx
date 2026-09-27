import { motion } from "motion/react";
import { useCallback, useEffect, useState } from "react";
import { fetchEvalCases, fetchEvalStatus, runEvalCase } from "../api/eval";
import type { EvalCaseSummary, EvalRunResponse, EvalStatus } from "../types/eval";
import { fadeUp, staggerContainer } from "../motion/presets";
import { GlassCard } from "./GlassCard";

const categoryColors: Record<string, string> = {
  happy_path: "bg-emerald-500/15 text-emerald-200",
  policy: "bg-amber-500/15 text-amber-200",
  adversarial: "bg-rose-500/15 text-rose-200",
  escalation: "bg-violet-500/15 text-violet-200",
};

function ResultBadge({ result }: { result: EvalRunResponse }) {
  const label = result.passed ? "Pass" : "Fail";
  const cls = result.passed
    ? "bg-emerald-500/20 text-emerald-300"
    : "bg-rose-500/20 text-rose-300";
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${cls}`}>
      {label}
    </span>
  );
}

export function EvalPanel({ className = "" }: { className?: string }) {
  const [status, setStatus] = useState<EvalStatus | null>(null);
  const [cases, setCases] = useState<EvalCaseSummary[]>([]);
  const [results, setResults] = useState<Record<string, EvalRunResponse>>({});
  const [runningId, setRunningId] = useState<string | null>(null);
  const [runAllBusy, setRunAllBusy] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(() => new Set());
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const toggleExpanded = useCallback((caseId: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(caseId)) {
        next.delete(caseId);
      } else {
        next.add(caseId);
      }
      return next;
    });
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        const [s, c] = await Promise.all([fetchEvalStatus(), fetchEvalCases()]);
        setStatus(s);
        setCases(c);
      } catch (err) {
        setLoadError(err instanceof Error ? err.message : "Could not load eval cases");
      }
    })();
  }, []);

  const anyRunBusy = Boolean(runningId) || runAllBusy;

  const handleRun = useCallback(async (caseId: string) => {
    setError(null);
    setRunningId(caseId);
    try {
      const result = await runEvalCase(caseId);
      setResults((prev) => ({ ...prev, [caseId]: result }));
      setExpandedIds((prev) => new Set(prev).add(caseId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eval run failed");
    } finally {
      setRunningId(null);
    }
  }, []);

  const handleRunAll = useCallback(async () => {
    if (cases.length === 0 || anyRunBusy) return;
    setError(null);
    setRunAllBusy(true);
    for (const c of cases) {
      setRunningId(c.id);
      try {
        const result = await runEvalCase(c.id);
        setResults((prev) => ({ ...prev, [c.id]: result }));
        setExpandedIds((prev) => new Set(prev).add(c.id));
      } catch (err) {
        setError(err instanceof Error ? err.message : `Eval run failed (${c.title})`);
        break;
      }
    }
    setRunningId(null);
    setRunAllBusy(false);
  }, [anyRunBusy, cases]);

  const passCount = cases.filter((c) => results[c.id]?.passed).length;
  const ranCount = cases.filter((c) => results[c.id]).length;

  return (
    <GlassCard className={`flex min-h-0 flex-col p-4 ${className}`} glow="violet">
      <div className="mb-3 shrink-0">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <h2 className="text-sm font-semibold text-white">Evaluation (DeepEval)</h2>
          <button
            type="button"
            disabled={cases.length === 0 || anyRunBusy}
            onClick={() => void handleRunAll()}
            className="shrink-0 rounded-lg border border-violet-400/40 bg-violet-600/20 px-3 py-1.5 text-[11px] font-medium text-violet-100 hover:bg-violet-600/35 disabled:opacity-40"
          >
            {runAllBusy
              ? `Running… ${cases.find((x) => x.id === runningId)?.title ?? ""}`.trim()
              : "Run all"}
          </button>
        </div>
        {ranCount > 0 ? (
          <p className="mt-1 text-[10px] text-zinc-500">
            {passCount}/{ranCount} passed
            {ranCount === cases.length ? " (full suite)" : ""}
          </p>
        ) : null}
        {status && (
          <p className="mt-1 text-[10px] text-zinc-500">
            Agent: {status.agent_provider_for_eval} · DeepEval:{" "}
            {status.deepeval_available ? "ready" : "missing"} · Judge:{" "}
            {status.judge_configured ? status.judge_model ?? "configured" : "not configured"}
          </p>
        )}
      </div>

      {loadError ? (
        <p className="text-xs text-rose-300">{loadError}</p>
      ) : null}
      {error ? <p className="mb-2 text-xs text-rose-300">{error}</p> : null}

      <motion.ul
        className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1"
        variants={staggerContainer(0.04, 0.02)}
        initial="hidden"
        animate="visible"
      >
        {cases.map((c) => {
          const result = results[c.id];
          const busy = runningId === c.id;
          const expanded = expandedIds.has(c.id);
          const catClass = categoryColors[c.category] ?? "bg-white/5 text-zinc-400";

          return (
            <motion.li
              key={c.id}
              variants={fadeUp}
              className="rounded-xl border border-white/5 bg-black/30 p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <button
                  type="button"
                  onClick={() => toggleExpanded(c.id)}
                  className="min-w-0 flex-1 rounded-lg text-left outline-none hover:bg-white/[0.03] focus-visible:ring-1 focus-visible:ring-violet-400/40 -m-1 p-1"
                  aria-expanded={expanded}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className="text-[10px] text-zinc-500 transition-transform"
                      aria-hidden
                      style={{ transform: expanded ? "rotate(90deg)" : "rotate(0deg)" }}
                    >
                      ▶
                    </span>
                    <p className="text-xs font-medium text-zinc-100">{c.title}</p>
                    {result ? <ResultBadge result={result} /> : null}
                  </div>
                  <span
                    className={`mt-1 inline-block rounded px-1.5 py-0.5 text-[9px] uppercase tracking-wide ${catClass}`}
                  >
                    {c.category.replace("_", " ")}
                  </span>
                  {!expanded ? (
                    <p className="mt-1.5 line-clamp-1 text-[11px] text-zinc-500">{c.message}</p>
                  ) : null}
                </button>
                <button
                  type="button"
                  disabled={busy || anyRunBusy}
                  onClick={() => void handleRun(c.id)}
                  className="shrink-0 rounded-lg bg-violet-600/90 px-2.5 py-1.5 text-[11px] font-medium text-white hover:bg-violet-500 disabled:opacity-40"
                >
                  {busy ? "Running…" : "Run eval"}
                </button>
              </div>

              {expanded ? (
                <div className="mt-2 space-y-2 border-t border-white/5 pt-2">
                  <p className="text-[11px] text-zinc-400">
                    <span className="text-zinc-500">Prompt: </span>
                    {c.message}
                  </p>
                  {result ? (
                    <div className="space-y-1.5 text-[10px] text-zinc-400">
                      <p>
                        Structural:{" "}
                        <span
                          className={
                            result.structural.passed ? "text-emerald-300" : "text-rose-300"
                          }
                        >
                          {result.structural.passed ? "pass" : "fail"}
                        </span>
                        {result.structural.details.length > 0
                          ? ` — ${result.structural.details.join("; ")}`
                          : null}
                      </p>
                      <p>
                        G-Eval
                        {result.deepeval.required_for_pass === false ? (
                          <span className="text-zinc-600"> (advisory)</span>
                        ) : null}
                        :{" "}
                        {result.deepeval.error ? (
                          <span className="text-rose-300">{result.deepeval.error}</span>
                        ) : (
                          <span
                            className={
                              result.deepeval.passed
                                ? "text-emerald-300"
                                : result.deepeval.required_for_pass
                                  ? "text-rose-300"
                                  : "text-amber-200"
                            }
                          >
                            {result.deepeval.passed ? "pass" : "fail"}
                            {result.deepeval.score != null
                              ? ` (${(result.deepeval.score * 100).toFixed(0)}%)`
                              : ""}
                          </span>
                        )}
                      </p>
                      {result.deepeval.reason ? (
                        <p className="text-zinc-500 italic">{result.deepeval.reason}</p>
                      ) : null}
                      <p className="whitespace-pre-wrap text-zinc-500">{result.reply}</p>
                    </div>
                  ) : (
                    <p className="text-[10px] text-zinc-600">Run eval to see results.</p>
                  )}
                </div>
              ) : null}
            </motion.li>
          );
        })}
      </motion.ul>
    </GlassCard>
  );
}
