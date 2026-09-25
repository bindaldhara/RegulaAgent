import type { Transition, Variants } from "motion/react";

export const springSnappy: Transition = {
  type: "spring",
  stiffness: 420,
  damping: 32,
  mass: 0.8,
};

export const springSoft: Transition = {
  type: "spring",
  stiffness: 260,
  damping: 28,
};

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 16, filter: "blur(6px)" },
  visible: { opacity: 1, y: 0, filter: "blur(0px)" },
};

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.92 },
  visible: { opacity: 1, scale: 1 },
};

export const slideFromRight: Variants = {
  hidden: { opacity: 0, x: 24, scale: 0.98 },
  visible: { opacity: 1, x: 0, scale: 1 },
};

export const slideFromLeft: Variants = {
  hidden: { opacity: 0, x: -24, scale: 0.98 },
  visible: { opacity: 1, x: 0, scale: 1 },
};

export const staggerContainer = (stagger = 0.06, delay = 0.05): Variants => ({
  hidden: {},
  visible: {
    transition: { staggerChildren: stagger, delayChildren: delay },
  },
});
