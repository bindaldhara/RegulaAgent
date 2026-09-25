import { motion } from "motion/react";
import type { WorkflowStep } from "../types/agent";

const STEPS: WorkflowStep[] = [
  "intent",
  "identity",
  "consent",
  "policy",
  "tool",
  "response",
];

function stepIndex(step: WorkflowStep | undefined): number {
  if (!step) return -1;
  const order = [
    "intent",
    "identity",
    "consent",
    "action",
    "policy",
    "tool",
    "result_validation",
    "response",
    "audit",
    "handoff",
    "end",
  ];
  return order.indexOf(step);
}

interface WorkflowPillsProps {
  currentStep?: WorkflowStep;
}

export function WorkflowPills({ currentStep }: WorkflowPillsProps) {
  const activeIdx = stepIndex(currentStep);

  return (
    <div className="flex flex-wrap gap-1.5 border-b border-white/5 px-4 py-3">
      {STEPS.map((step) => {
        const idx = stepIndex(step);
        const isActive = activeIdx >= idx && activeIdx !== -1;
        const isCurrent = currentStep === step || (step === "policy" && currentStep === "action");

        return (
          <motion.span
            key={step}
            className={`rounded-full px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider ${
              isCurrent
                ? "ms-pill-active text-white"
                : isActive
                  ? "border border-white/10 bg-white/5 text-zinc-400"
                  : "ms-pill text-zinc-600"
            }`}
            layout
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
          >
            {step.replace(/_/g, " ")}
          </motion.span>
        );
      })}
    </div>
  );
}
