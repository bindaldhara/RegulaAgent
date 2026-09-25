import { motion } from "motion/react";

const PROMPTS = [
  "Book a cardiologist tomorrow.",
  "Find a dentist next week.",
  "Cancel my appointment.",
  "I have severe chest pain.",
];

interface PromptPillsProps {
  onSelect: (text: string) => void;
  disabled?: boolean;
}

export function PromptPills({ onSelect, disabled }: PromptPillsProps) {
  return (
    <div className="flex flex-wrap gap-2 px-4 pb-3 md:px-0">
      {PROMPTS.map((text, i) => (
        <motion.button
          key={text}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(text)}
          className="ms-pill rounded-full px-3.5 py-1.5 text-xs text-zinc-300 transition-colors hover:border-white/20 hover:bg-white/6 disabled:opacity-40"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {text}
        </motion.button>
      ))}
    </div>
  );
}
