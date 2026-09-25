import { motion } from "motion/react";

interface SiteHeaderProps {
  providerLabel: string;
  onSignOut?: () => void;
}

export function SiteHeader({ providerLabel, onSignOut }: SiteHeaderProps) {
  return (
    <>
      <div className="border-b border-violet-500/30 bg-gradient-to-r from-violet-950/80 via-violet-900/40 to-violet-950/80 px-4 py-1.5 text-center text-[11px] text-violet-100/90">
        Policy-bounded agent runtime · healthcare scheduling demo
      </div>
      <header className="relative z-10 flex items-center justify-between px-4 py-4 md:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-sm font-bold">
            R
          </div>
          <span className="text-sm font-semibold tracking-tight text-white">RegulaAgent</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-[10px] font-medium uppercase tracking-wider text-amber-200/90 sm:inline">
            Fresh build
          </span>
          <motion.span
            className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-ms-muted"
            animate={{ opacity: [0.7, 1, 0.7] }}
            transition={{ duration: 3, repeat: Infinity }}
          >
            {providerLabel}
          </motion.span>
        </div>
      </header>
    </>
  );
}
