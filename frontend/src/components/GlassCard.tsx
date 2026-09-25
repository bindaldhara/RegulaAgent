import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";
import { springSnappy } from "../motion/presets";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  glow?: "cyan" | "violet" | "none";
}

const glowRing: Record<string, string> = {
  cyan: "shadow-[0_0_60px_-12px_rgba(34,211,238,0.35)]",
  violet: "shadow-[0_0_60px_-12px_rgba(167,139,250,0.35)]",
  none: "",
};

export function GlassCard({ children, className = "", glow = "none" }: GlassCardProps) {
  const reduce = useReducedMotion();

  return (
    <motion.div
      className={`ms-card relative overflow-hidden rounded-2xl backdrop-blur-xl ${glowRing[glow]} ${className}`}
      initial={reduce ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springSnappy}
    >
      <div className="pointer-events-none absolute inset-0 ms-noise" aria-hidden />
      {children}
    </motion.div>
  );
}
