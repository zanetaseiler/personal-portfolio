---
name: cinematic-web
description: >-
  Enhance an existing React website to a premium, cinematic level of beauty and
  motion (Seedance / Higgsfield feel) using Framer Motion, GSAP, and Lenis.
  Use this skill when the user wants to make their site look and feel more
  polished, add scroll animations, parallax, spring physics, page transitions,
  or generally "make it beautiful / add motion / make it feel expensive." Works
  by reading the existing code first, restyling section by section, then layering
  cinematic motion with accessibility and performance guardrails. Trigger on
  phrases like "make my site beautiful", "add animations", "make it feel
  premium", "cinematic motion", "enhance the design", "add scroll effects".
---

# Cinematic Web — guided enhancement of an existing React site

You are upgrading an **existing** React codebase to a premium, cinematic level of
visual design and motion. The target feeling is Seedance / Higgsfield: depth,
choreography, spring physics, and taste — not generic AI slop.

## Prime directives (read first, every time)

1. **Read before you touch.** Never restyle or animate code you have not read.
   Understand the framework, styling system, and existing animation before changing anything.
2. **Taste comes from the user, execution comes from you.** Do not invent a
   direction. Run the intake (Step 1) and follow the user's answers. When unsure, ask.
3. **Work section by section.** Never do a single "redesign the whole site" pass.
   One component at a time, with a reviewable diff each time.
4. **Motion is the differentiator, but guardrails are non-negotiable.** Every
   animation ships with a `prefers-reduced-motion` fallback and respects the perf budget.
5. **Adapt, never copy.** Reference patterns inform structure and feel — never paste a design wholesale.

---

## Step 1 — Intake (interview the user)

Before writing any code, establish direction. Ask the user these, one message,
concise. If they already answered some, skip those.

- **Who is this site for, and what is it selling / communicating?**
- **What one feeling should a visitor have in the first 3 seconds?**
  (e.g. premium, playful, technical, editorial, futuristic)
- **Brand adjectives** — give me 3.
- **Any sites you love** the look of? (paste links/screenshots if possible)
- **Color & type** — existing brand colors/fonts, or should I propose?
- **Motion appetite** — this skill defaults to *cinematic/maximal*. Confirm, or
  dial to *refined* or *subtle*.

Write the answers to `.design/brief.md` in the repo (create the folder if needed).
This file is the source of truth for every later step.

---

## Step 2 — Audit the existing code

Do not skip this. Inspect and summarize the codebase before enhancing.

Determine and record in `.design/audit.md`:

- Framework & version (Next.js / Vite / CRA), and **App Router vs Pages / SSR vs CSR**
  (this changes how you use `"use client"` and animation libs).
- Styling system: Tailwind, CSS Modules, styled-components, vanilla CSS.
- Existing animation libraries already installed (avoid duplicates / conflicts).
- The section/component structure (nav, hero, features, etc.) — map the files.
- Risk areas: hydration-sensitive code, third-party embeds, existing scroll libs.

Then produce a **prioritized enhancement list**: for each section, note keep /
restyle / add-motion, ordered by visual impact (hero and nav first).

Confirm the list with the user before proceeding.

---

## Step 3 — Install the motion foundation

Only install what the audit says is missing. Preferred stack:

```bash
npm install motion         # Framer Motion (import from "motion/react")
npm install lenis          # smooth scroll
npm install gsap           # scroll choreography (ScrollTrigger) when Framer isn't enough
# optional depth accents only if the brief calls for it:
# npm install three @react-three/fiber @react-three/drei
```

Copy `references/motion-tokens.ts` into the project (e.g. `src/lib/motion-tokens.ts`)
and `references/motion-primitives.tsx` into `src/components/motion/`. These are the
shared vocabulary — always animate *through* these, never with ad-hoc magic numbers.

Set up Lenis once at the app root (see the comment block at the top of
`motion-primitives.tsx`).

---

## Step 4 — Restyle, section by section (static beauty first)

For each section, in priority order, before adding motion:

- **Spacing & rhythm** — generous, intentional whitespace; consistent scale.
- **Type hierarchy** — clear display/heading/body contrast; tight, deliberate leading.
- **Color & depth** — layered surfaces, soft real shadows, subtle gradients tied to brand — never the default AI purple.
- **Detail** — borders, radii, focus states, hover affordances.

Score each restyled section against `references/taste-rubric.md` before moving on.
Show the user the diff for that section and get a thumbs up.

---

## Step 5 — Layer cinematic motion

Now apply motion using the primitives. Menu of techniques (choose per the brief):

- **Entrance choreography** — `<Reveal>` / `<Stagger>` for staggered fade-up as
  content scrolls into view. Stagger children, don't animate them uniformly.
- **Scroll-linked transforms** — `useScroll` + `useTransform` for parallax and
  pinned/scrubbed sections. Use GSAP ScrollTrigger for complex pinned timelines.
- **Spring physics** — use the spring presets in the tokens; never linear easing
  for anything that should feel alive.
- **Depth & parallax** — move background/mid/foreground layers at different rates.
- **Page/route transitions** — `AnimatePresence` + the View Transitions API.
- **Micro-interactions** — magnetic buttons, hover scale, cursor-follow accents.
- **Optional hero accent** — R3F particles/shader *behind* content, only if the brief is "futuristic/maximal" and the perf budget allows.

Pacing matters more than quantity: vary durations, let things breathe, avoid
everything animating at once.

---

## Step 6 — Guardrails (mandatory, never skip)

- **Reduced motion:** every animation must degrade gracefully under
  `@media (prefers-reduced-motion: reduce)` and Framer's `useReducedMotion()`.
  The primitives already wire this — keep it intact.
- **Performance:** animate only `transform` and `opacity`. No animating layout
  properties (width/height/top/left). Use `will-change` sparingly. Keep the hero
  from blocking LCP — don't gate first paint on JS animation.
- **Mobile:** lighten or disable heavy scroll/3D effects on small screens.
- **No CLS:** reserve space so reveals don't shift layout.

---

## Step 7 — Slop audit (final pass)

Run through `references/slop-checklist.md` and fix every hit. This is what
separates "clearly AI-made" from "someone with taste made this." Report the
before/after to the user.

---

## Reference files in this skill

- `references/motion-tokens.ts` — easing curves, durations, stagger, spring presets.
- `references/motion-primitives.tsx` — reusable `<Reveal>`, `<Stagger>`, `<Parallax>`, `<MagneticButton>`, Lenis setup.
- `references/taste-rubric.md` — score restyled sections against this.
- `references/slop-checklist.md` — the AI-slop tells to eliminate.
