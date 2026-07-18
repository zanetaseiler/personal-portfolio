# AI-slop checklist — eliminate every hit

These are the tells that scream "an AI made this." Scan the site and fix each one.

## Color
- [ ] Default purple/indigo → blue gradient on a white background. Replace with a brand-driven palette.
- [ ] Pure `#000` on pure `#fff`. Use slightly warmed/cooled near-blacks and off-whites.
- [ ] Rainbow of accent colors. Pick one accent, use it with discipline.

## Depth & shadows
- [ ] Default `box-shadow` (harsh, uniform grey). Use soft, layered, tinted shadows.
- [ ] Flat everything OR drop-shadow on everything. Depth should be selective and intentional.

## Typography
- [ ] System font everywhere with no hierarchy. Set a real type scale.
- [ ] Centered walls of text. Vary alignment; give text a measure (~60–75ch).
- [ ] Default line-height. Tune it.

## Layout
- [ ] Everything full-width, edge to edge, evenly spaced. Introduce rhythm and asymmetry.
- [ ] Three identical feature cards in a row with an icon + heading + lorem. Make them earn their place.
- [ ] Cramped padding. Let it breathe.

## Motion
- [ ] No motion at all (static = feels cheap for this brief).
- [ ] Everything fades in at once on load. Use scroll-triggered stagger.
- [ ] Linear easing / uniform durations. Use spring/expo and vary timing.
- [ ] Motion that fights the user (janky scroll-jacking, blocking interaction).
- [ ] No `prefers-reduced-motion` fallback.

## Content & imagery
- [ ] Generic stock photos that don't match the brand.
- [ ] Placeholder/lorem text left in.
- [ ] Emoji used as icons.

## Performance
- [ ] Animating width/height/top/left (causes jank). Animate transform/opacity only.
- [ ] Hero animation blocks LCP / first paint.
- [ ] Heavy 3D/scroll effects running unchanged on mobile.

**Report:** list every item found and how it was fixed.
