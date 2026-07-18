# Design brief — cinematic-web enhancement

## Who is this for / what it's selling
Žaneta Seilerová's personal portfolio — presenting her as a Digital Marketing
Director to potential Toptal clients, founders, companies, and agencies looking for
an experienced growth/SEO/GEO/e-commerce/AI strategy leader.

## First 3-second feeling
**Premium / authoritative.** Reads like a senior consultant or agency principal —
polished, confident, credible.

## Brand adjectives
**Confident, strategic, warm.** Senior-operator energy with a human touch — not
cold/corporate, not casual.

## Reference sites
None specific requested — rely on the brief above rather than matching a named site.

## Color & type direction
**Refine, don't replace.** Keep the warm terracotta accent + cream/sand neutrals and
the Fraunces (display) / Inter (body) pairing — that identity stays. License to tune
shades, contrast, and type scale for more polish as each section is restyled, but not
to introduce a new palette or new fonts.

## Motion appetite
**Refined** — confident but restrained. Staggered scroll reveals, subtle parallax,
spring-like hover/press physics. Not the skill's maximal/cinematic default (no heavy
pinned scroll timelines, no 3D/particle accents, no aggressive scroll-jacking).

## Working agreement
- One section at a time, in the priority order from `audit.md` (Hero+Nav first).
- Show the change (code + visual) before moving to the next section.
- Motion foundation (CSS easing/duration/stagger tokens, adapted from the skill's
  `motion-tokens.ts`) gets introduced alongside the first section and reused everywhere
  after — not re-explained each time.
- Every animation ships with a `prefers-reduced-motion` fallback and animates only
  `transform`/`opacity` (already the site's existing convention).
