import { motion } from "motion/react";

export function ThinkingIndicator() {
  return (
    <motion.div
      className="flex items-center gap-2 text-xs text-ms-muted"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="h-1 w-1 rounded-full bg-violet-400"
          animate={{ opacity: [0.2, 1, 0.2], scale: [1, 1.3, 1] }}
          transition={{ duration: 1, repeat: Infinity, delay: i * 0.12 }}
        />
      ))}
      <span>Thinking…</span>
    </motion.div>
  );
}
