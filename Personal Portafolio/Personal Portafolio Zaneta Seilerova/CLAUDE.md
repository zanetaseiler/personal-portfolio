# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Žaneta Seilerová's personal portfolio site: a single-page, dependency-free static
site (`index.html`, `styles.css`, `script.js`). No framework, no build step, no npm.
That's a deliberate original requirement, not an oversight — it needs to stay easy for
a non-developer to hand-edit and trivial to deploy as static files. Do not introduce a
bundler, framework, or package manager to "improve" it.

## Commands

There is no build/lint/test tooling — this is intentional. To preview locally:

```bash
python3 -m http.server 8000    # then open http://localhost:8000
# or: npx serve .
```

Opening `index.html` directly in a browser also works for quick checks.

## Deployment

The git repo root is **two directories above** this folder
(`Visual Studio Code Claude/`, containing `.git` and `.github/`) — this folder is a
subdirectory within it, not its own repo. GitHub Actions
(`.github/workflows/deploy.yml` at the repo root) auto-deploys to GoDaddy cPanel over
FTPS on every push to `main` that touches files under
`Personal Portafolio/Personal Portafolio Zaneta Seilerova/**`. Live at
zaneta.trafficdomseo.com. Deploys finish in under a minute; check `gh run list` or the
Actions tab. Browsers can cache stale `styles.css` right after a deploy — hard refresh
(Cmd+Shift+R) to confirm a change actually landed.

Per the user's standing instruction (see auto-memory), commit and push changes to
`github.com/zanetaseiler/personal-portfolio` with clear messages as part of finishing
work, unless told otherwise.

## Architecture

**Everything lives in three files**, organized top-to-bottom in the same order
sections appear on the page: Header/Nav, Hero, About, Core Expertise, Selected Work
(case studies), How I Work, Tools & Platforms, Toptal, Testimonials, Contact, Footer.
`index.html` has a numbered HTML comment banner (`===== N. SECTION NAME =====`) above
each section — use those to jump straight to the right place instead of reading the
whole file.

**`styles.css` — design tokens first.** The `:root` block at the top defines the
entire visual system as CSS custom properties: warm cream/terracotta color palette,
Fraunces (display/serif) + Inter (body/sans) type pairing, spacing scale, radii,
shadows, and a motion-token set (`--ease-out-expo`, `--ease-back`, `--duration-*`,
`--stagger-*`). Re-theme or re-time anything site-wide by editing a value here, not by
hunting through component rules. New animations should reuse these tokens rather than
hardcoding ad-hoc easing/durations.

**`script.js` — small, vanilla, delegation-based.** Everything runs inside a single
`DOMContentLoaded` listener: sticky-header shadow on scroll, mobile nav open/close,
active-nav-link tracking via `IntersectionObserver`, scroll-reveal animations (`.reveal`
class, fade + translateY, unobserves after first fire) via a second
`IntersectionObserver`, case-study accordion expand/collapse (CSS Grid
`0fr → 1fr` trick), and a contact-form submit handler that currently just shows an
inline "not connected yet" message (no backend wired up — see below).

**Case studies are repeated, hand-authored blocks**, not templated/generated — each of
the 5 case studies in `index.html` is its own `<details>`-like accordion block with
cover image, stat tiles, and a detail grid. Some also have a
`<p class="case-study-download">` block linking to a PDF in `assets/case-studies/`;
others don't yet. To add the download button to one that lacks it, copy that block
from an existing case study (see README for the exact pattern) rather than inventing a
new markup shape.

**No backend.** The contact form has no server behind it. Wiring it up means either
pointing the form's `action` at a Formspree endpoint or adding Netlify Forms
attributes — instructions are written as HTML comments directly above the `<form>` tag
in `index.html`.

## Content editing conventions

- Swap the photo/résumé by replacing the file at its existing path
  (`assets/images/zaneta-seilerova.jpg`, `assets/resume/zaneta-seilerova-resume.pdf`)
  with the same filename — no code changes needed.
- The **Testimonials** section is the only placeholder content site-wide — all three
  quotes are explicitly marked `[Draft placeholder — Name, Title, Company]` and are
  meant to be replaced with real testimonials as they're collected. Every other
  section (email, Toptal link, live domain, case-study details) is real content.
- LinkedIn is intentionally removed from Contact and Footer at Žaneta's request
  (marked with HTML comments at both spots) — don't re-add it without being asked.
- Motion/animation work should follow `.design/brief.md` and `.design/audit.md`
  (written for the `cinematic-web` skill pass on this site): refined/restrained motion
  only (staggered reveals, subtle parallax, spring-like hover physics) — no heavy
  pinned scroll timelines, 3D/particle effects, or scroll-jacking. Every animation
  must respect `prefers-reduced-motion` and animate only `transform`/`opacity`.
