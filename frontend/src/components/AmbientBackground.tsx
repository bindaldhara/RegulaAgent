import { motion, useReducedMotion } from "motion/react";

/** Motionsites-inspired dark canvas + soft aurora spotlights */
export function AmbientBackground() {
  const reduce = useReducedMotion();

  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden bg-[#0a0a0c]" aria-hidden>
      <div
        className="absolute inset-0 opacity-90"
        style={{
          background:
            "radial-gradient(ellipse 90% 60% at 50% -10%, rgba(88, 28, 135, 0.35), transparent 55%), radial-gradient(ellipse 70% 50% at 100% 20%, rgba(34, 211, 238, 0.08), transparent 50%), radial-gradient(ellipse 60% 40% at 0% 80%, rgba(251, 191, 36, 0.06), transparent 45%)",
        }}
      />
      {!reduce && (
        <>
          <motion.div
            className="absolute left-1/2 top-0 h-[420px] w-[min(100%,900px)] -translate-x-1/2 rounded-full bg-white/[0.07] blur-[100px]"
            animate={{ opacity: [0.4, 0.65, 0.4], scale: [1, 1.05, 1] }}
            transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            className="absolute -right-20 top-1/4 h-72 w-72 rounded-full bg-violet-600/20 blur-[80px]"
            animate={{ x: [0, -30, 0] }}
            transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
          />
        </>
      )}
      <div className="absolute inset-0 ms-noise" />
    </div>
  );
}
