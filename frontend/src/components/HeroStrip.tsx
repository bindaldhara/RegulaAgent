import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";

const WORDS = ["Intent", "Policy", "Tools", "Audit"];

export function HeroStrip() {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setIndex((i) => (i + 1) % WORDS.length), 2800);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="relative z-10 px-4 pb-2 text-center md:px-6">
      <h1 className="text-2xl font-bold uppercase tracking-tight text-white md:text-4xl">
        Unlock your{" "}
        <span className="relative inline-block">
          <span className="ms-glow-text bg-gradient-to-b from-white to-zinc-400 bg-clip-text text-transparent">
            regulated
          </span>
        </span>{" "}
        scheduling
      </h1>
      <p className="mx-auto mt-2 max-w-lg text-sm text-ms-muted">
        LLM proposes · workflow decides ·{" "}
        <span className="inline-block min-w-[4.5rem] text-white">
          <AnimatePresence mode="wait">
            <motion.span
              key={WORDS[index]}
              initial={{ opacity: 0, y: 8, filter: "blur(4px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -8, filter: "blur(4px)" }}
              transition={{ duration: 0.35 }}
              className="font-medium text-violet-300"
            >
              {WORDS[index]}
            </motion.span>
          </AnimatePresence>
        </span>{" "}
        enforces
      </p>
    </div>
  );
}
