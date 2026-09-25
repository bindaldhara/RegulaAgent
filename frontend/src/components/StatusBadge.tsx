import { motion, useReducedMotion } from "motion/react";

const styles: Record<string, string> = {
  ALLOW: "bg-emerald-500/20 text-emerald-300 ring-emerald-500/40",
  DENY: "bg-rose-500/20 text-rose-300 ring-rose-500/40",
  ESCALATE: "bg-amber-500/20 text-amber-200 ring-amber-500/40",
  LOW: "bg-slate-500/20 text-slate-200 ring-slate-500/40",
  MEDIUM: "bg-sky-500/20 text-sky-200 ring-sky-500/40",
  HIGH: "bg-orange-500/20 text-orange-200 ring-orange-500/40",
  CRITICAL: "bg-red-500/20 text-red-200 ring-red-500/40",
};

export function StatusBadge({ label, tone }: { label: string; tone?: string }) {
  const reduce = useReducedMotion();
  const cls = tone ? styles[tone] ?? styles.LOW : "bg-cyan-500/15 text-cyan-200 ring-cyan-500/30";

  return (
    <motion.span
      layout
      className={`inline-flex max-w-full shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ${cls}`}
      initial={reduce ? false : { opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ type: "spring", stiffness: 500, damping: 28 }}
      key={label + tone}
    >
      {label}
    </motion.span>
  );
}
