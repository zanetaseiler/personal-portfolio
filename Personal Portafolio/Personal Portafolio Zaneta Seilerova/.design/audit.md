# Codebase audit — cinematic-web enhancement

## Framework & stack
- **No framework.** Plain static `index.html` + `styles.css` + `script.js`. No build
  step, no npm, no bundler, no React.
- Deployed as static files via GitHub Actions → GoDaddy cPanel (FTPS) on every push
  to `main`. Live at zaneta.trafficdomseo.com.
- One external request: Google Fonts (Fraunces + Inter).

**Adaptation from the skill's default stack:** the `cinematic-web` skill assumes
React + Framer Motion + GSAP + Lenis + npm. This site is intentionally
dependency-free static HTML/CSS/JS — that was a deliberate original requirement
(easy for a non-developer to hand-edit, trivial static-file deploy). Installing
React would mean rebuilding the site on a different stack, not enhancing this one.
Per the skill's own "adapt, never copy" directive, I'm translating the same
vocabulary into vanilla equivalents:

| Skill concept (React) | Vanilla adaptation |
|---|---|
| `motion-tokens.ts` (ease/duration/stagger/spring) | CSS custom properties: `--ease-out-expo`, `--ease-back`, `--duration-*`, `--stagger-*` |
| `<Reveal>` / `<Stagger>` (Framer, scroll-triggered) | Extend the existing `IntersectionObserver` + `.reveal` system to support staggered children and expo easing instead of the current linear "ease" |
| `<Parallax>` (useScroll/useTransform) | Small vanilla scroll listener + `requestAnimationFrame`, transform-only, `prefers-reduced-motion`-gated |
| Spring physics | CSS cubic-bezier "back" overshoot for hovers/press (true spring physics need a JS physics loop — reserved for anything that specifically needs it) |
| `<MagneticButton>` | Vanilla `mousemove` listener translating the button, desktop-only, disabled under reduced motion and on touch |
| `AnimatePresence` page transitions | Not applicable — single-page site, anchor navigation only, no route changes |

## Existing animation already in place
- `.reveal` class: fade + `translateY(16px)` → visible on intersect, default CSS
  `ease`, 0.6s, no stagger, unobserves after firing once.
- Case-study accordion: CSS Grid `grid-template-rows: 0fr → 1fr` trick, default ease.
- Sticky header: scroll-listener toggles a shadow class past 8px scroll.
- Mobile nav: `max-height` toggle transition.
- Chevron rotation on accordion open/close.
- All of the above respects `prefers-reduced-motion` (global kill-switch in CSS).
- No parallax, no spring/overshoot easing, no stagger, no magnetic/cursor effects.

## Design tokens already defined (good foundation)
- Warm neutral palette + one disciplined terracotta accent (not default AI purple) —
  already passes that slop check.
- Type: Fraunces (display/serif) + Inter (body/sans) — a real pairing, not
  system-font-everywhere.
- Spacing scale, radii, two shadow levels already tokenized as CSS custom properties.
- Soft, tinted shadows (not harsh default box-shadow) — another slop check already passed.

**Overall: this is not a generic AI-slop site needing a rescue.** It's a deliberately
restrained, already-tasteful static site. The opportunity here is adding cinematic
motion and refining rhythm/detail — not fixing egregious mistakes.

## Section map (in DOM order)
1. Header / sticky nav + mobile menu
2. Hero (photo + name/title/intro + 3 CTAs)
3. About (lead paragraph + tag pills)
4. Core Expertise (8 icon cards, 4-col grid)
5. Selected Work (5 case-study accordions, each with cover image, stat tiles, detail grid, optional PDF download)
6. How I Work (2-col text)
7. Tools & Platforms (badge list)
8. Toptal (2-col text + button)
9. Testimonials (3 quote cards)
10. Contact (info list + form)
11. Footer

## Prioritized enhancement list (visual impact order)
1. **Hero + Nav** — first thing every visitor sees; highest leverage.
2. **Core Expertise cards** — first grid of repeated elements, sets the stagger pattern.
3. **Case Studies** — largest, most content-dense section; benefits most from
   reveal choreography and the accordion opening more fluidly.
4. **About** — tag pills are a natural stagger candidate.
5. **How I Work / Tools / Toptal** — simpler text/badge sections, lighter touch.
6. **Testimonials** — quote cards, stagger + subtle depth.
7. **Contact + Footer** — form polish, final section, lowest priority.

## Risk notes
- Live production site — every change needs a commit + push to actually go live;
  browsers have shown cached-CSS issues right after a deploy in this project before
  (hard refresh needed). Verify locally first, always.
- Google Fonts is the only external dependency; keep it that way unless the brief
  calls for something new.
- Mobile: case-study accordions and cards need any new motion to stay light —
  no heavy parallax on small screens per the skill's guardrails.
