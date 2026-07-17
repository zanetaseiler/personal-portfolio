# Žaneta Seilerová — Portfolio Website

A clean, dependency-free HTML/CSS/JS portfolio site. No build step, no frameworks —
just `index.html`, `styles.css`, and `script.js`.

## Preview it locally

**Easiest option:** double-click `index.html` and it will open in your browser.

**Better option (recommended):** run a tiny local server so relative paths and any
future fetch-based form integration behave exactly as they will online.

```bash
cd "Personal Portafolio Zaneta Seilerova"
python3 -m http.server 8000
```

Then open `http://localhost:8000` in your browser. Press `Ctrl+C` in the terminal to stop the server.

If you have Node.js installed instead, `npx serve .` works the same way.

## Your photo and résumé

Both are already in place: `assets/images/zaneta-seilerova.jpg` and
`assets/resume/zaneta-seilerova-resume.pdf`. To swap either one later, just replace the
file at that same path with the same filename — no code changes needed. (If a
replacement photo isn't a `.jpg`, either rename it or update the `src` on the
`<img class="hero-photo">` tag near the top of `index.html`.)

## Add a case-study PDF

Some case studies (MOLOSOC, Draft Coffee EU / Bona Fide, SEO Growth: NitroCoffee.store,
AI Cybersecurity SaaS) have a "Download full case study (PDF)" button inside their
expanded card. These currently link straight to PDFs hosted on your own sites
(trafficdomseo.com, bonafidenitro.com, molosoc.com) rather than files in this project —
that way they stay current if you update the deck later. To add or swap one:

1. In `index.html`, find the relevant `<a href="https://..." class="btn btn-secondary" target="_blank" rel="noopener noreferrer">`
   link inside that case study's panel and update the URL.
2. To add the same button to a case study that doesn't have one yet (MOLOSOC Brand
   Positioning), copy the `<p class="case-study-download">…</p>` block from an existing
   case study and paste it right after that case study's `</dl>`.
3. If you'd rather host the PDF locally instead of linking out, put the file in a folder
   like `assets/case-studies/`, then change the link's `href` to that relative path and
   swap `target="_blank" rel="noopener noreferrer"` for a `download` attribute (see how
   the résumé button works, above, for that pattern).

## Editing the content

Everything is in `index.html`, organized top-to-bottom in the same order as the
sections appear on the page (Hero, About, Expertise, Work, How I Work, Tools, Toptal,
Testimonials, Contact, Footer).

The only content still marked as placeholder is the **Testimonials** section — the
three quotes there are clearly-labeled drafts (`[Draft placeholder — Name, Title,
Company]`) meant to show the tone and length that work well, not real client words.
Swap each one in for a real testimonial as you collect them. Everything else (email,
Toptal link, live domain, case study details) has real values filled in.

## Connecting the contact form

The form currently has no backend — submitting it just shows an inline "thanks, not
connected yet" message (see the `CONTACT FORM` section in `script.js`). Instructions
for both common options are already written as comments directly above the `<form>`
tag in `index.html`:

- **Formspree** — create a form at formspree.io, then set the form's `action` to your
  Formspree endpoint URL.
- **Netlify Forms** — if you host on Netlify, add `data-netlify="true"` to the `<form>`
  tag and a hidden `form-name` input; Netlify detects it automatically at deploy time.

## Publishing the site

The site is live at **zaneta.trafficdomseo.com**. This repository has a GitHub Actions
workflow (`.github/workflows/`, one level up from this folder, at the repo root) that
automatically deploys to your GoDaddy cPanel hosting over FTPS on every push to `main`.
To publish a change:

```bash
git add "Personal Portafolio/Personal Portafolio Zaneta Seilerova"
git commit -m "Describe what changed"
git push origin main
```

The deploy usually finishes in under a minute — check progress with `gh run list` or
in the "Actions" tab on GitHub. Browsers sometimes cache the old `styles.css` for a bit
after a deploy; a hard refresh (Cmd+Shift+R / Ctrl+F5) clears that up.

## Customizing the design

Colors, fonts, and spacing are all defined as CSS custom properties at the top of
`styles.css` (`:root { ... }`). Changing a value there updates it everywhere on the
site — no need to hunt through the rest of the file.
