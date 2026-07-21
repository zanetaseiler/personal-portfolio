// Motion constants for Framer Motion. Keep values conceptually in sync with
// the `--ease-*` / `--duration-*` custom properties in tokens.css — CSS vars
// can't drive spring physics directly, so these are the JS-side mirror.
export const theme = {
  spring: {
    flip: { type: 'spring' as const, stiffness: 260, damping: 20, mass: 0.9 },
    hover: { type: 'spring' as const, stiffness: 400, damping: 25 },
    settle: { type: 'spring' as const, stiffness: 220, damping: 24 },
  },
  duration: {
    fast: 0.15,
    base: 0.3,
    slow: 0.5,
  },
  easeOutExpo: [0.16, 1, 0.3, 1] as const,
};

// Suit hue anchors — mirrored from tokens.css (--hue-body/mind/spirit).
// Kept here too since cardArt.ts generates raw hsl() strings in JS and
// can't read CSS custom properties without a runtime getComputedStyle call.
export const SUIT_HUES = {
  body: 14,
  mind: 208,
  spirit: 272,
} as const;
