/**
 * Motion tokens — the shared vocabulary for all animation on this site.
 *
 * Rule: never hardcode magic easing/duration numbers in components.
 * Always animate THROUGH these tokens so the whole site feels coherent.
 *
 * Copy this file to e.g. src/lib/motion-tokens.ts
 */

// --- Easing curves (cubic-bezier) --------------------------------------------
// Expo-out style curves feel premium: fast start, long graceful settle.
export const ease = {
  out: [0.16, 1, 0.3, 1] as const,       // easeOutExpo — the workhorse for reveals
  inOut: [0.83, 0, 0.17, 1] as const,    // easeInOutExpo — for scrubbed/scroll-linked
  soft: [0.25, 1, 0.5, 1] as const,      // gentle, for small UI moves
  back: [0.34, 1.56, 0.64, 1] as const,  // slight overshoot — playful accents
};

// --- Durations (seconds) -----------------------------------------------------
// Bigger elements move slower. Keep it deliberate; cinematic ≠ fast.
export const duration = {
  fast: 0.3,
  base: 0.6,
  slow: 0.9,
  hero: 1.2,
};

// --- Stagger (seconds between children) --------------------------------------
export const stagger = {
  tight: 0.05,
  base: 0.09,
  loose: 0.14,
};

// --- Spring presets (Framer Motion) ------------------------------------------
// Use springs for anything interactive/alive. Never linear.
export const spring = {
  // snappy but settled — buttons, cards, hovers
  snappy: { type: "spring", stiffness: 400, damping: 30, mass: 0.8 } as const,
  // smooth, weighty — larger elements, drawers
  smooth: { type: "spring", stiffness: 180, damping: 26 } as const,
  // bouncy — playful accents, use sparingly
  bouncy: { type: "spring", stiffness: 300, damping: 15 } as const,
};

// --- Parallax depth ratios ---------------------------------------------------
// How much each layer moves relative to scroll. Background moves least.
export const depth = {
  background: 0.15,
  mid: 0.4,
  foreground: 0.75,
};

// --- Ready-made variants -----------------------------------------------------
export const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: duration.base, ease: ease.out },
  },
};

export const fadeIn = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: duration.base, ease: ease.out } },
};

export const scaleIn = {
  hidden: { opacity: 0, scale: 0.96 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: { duration: duration.base, ease: ease.out },
  },
};

// Container that staggers its children on scroll-in.
export const staggerContainer = (interval = stagger.base) => ({
  hidden: {},
  visible: { transition: { staggerChildren: interval } },
});
