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

## Add your photo

1. Drop your headshot into `assets/images/` and name it exactly `zaneta-seilerova.jpg`
   (see `assets/images/PUT_YOUR_PHOTO_HERE.txt` for details).
2. Delete the `.txt` placeholder file once your photo is in place.
3. If your file is a `.png` instead, either rename it to `.jpg` or update the `src`
   attribute on the `<img class="hero-photo">` tag near the top of `index.html`.

## Add your résumé

1. Drop your résumé PDF into `assets/resume/` and name it exactly
   `zaneta-seilerova-resume.pdf`.
2. The "Download Résumé" button in the hero section will work immediately — no code
   changes needed.

## Add a case-study PDF

Some case studies (MOLOSOC, Draft Coffee EU / Bona Fide, SEO Growth: NitroCoffee.store,
AI Cybersecurity SaaS) have a "Download full case study (PDF)" button inside their
expanded card. These currently link straight to PDFs hosted on your own sites
(trafficdomseo.com, bonafidenitro.com, molosoc.com) rather than files in this project —
that way they stay current if you update the deck later. To add or swap one:

1. In `index.html`, find the relevant `<a href="https://..." class="btn btn-secondary" target="_blank" rel="noopener noreferrer">`
   link inside that case study's panel and update the URL.
2. To add the same button to a case study that doesn't have one yet (MOLOSOC Brand
   Positioning, Serpentine Incense, Consciousness Intervention), copy the
   `<p class="case-study-download">…</p>` block from an existing case study and paste it
   right after that case study's `</dl>`.
3. If you'd rather host the PDF locally instead of linking out, put the file in a folder
   like `assets/case-studies/`, then change the link's `href` to that relative path and
   swap `target="_blank" rel="noopener noreferrer"` for a `download` attribute (see how
   the résumé button works, above, for that pattern).

## Editing the content

Everything is in `index.html`, organized top-to-bottom in the same order as the
sections appear on the page (Hero, About, Expertise, Work, How I Work, Tools, Toptal,
Testimonials, Contact, Footer). Look for `<!-- comments -->` marking placeholders —
search the file for `PLACEHOLDER` to find every spot that still needs a real value:

- Your email address (`mailto:` links in Contact and Footer)
- Your LinkedIn profile URL
- Your Toptal profile URL
- Your live domain (used in the Open Graph tags and JSON-LD schema in `<head>`)
- Case study details (challenge, strategy, results, tools) marked `[Add ... once available]`
- Testimonials, once you have real ones to share

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

This is a fully static site, so any static host works. Two simple options:

- **Netlify / Vercel:** drag-and-drop the project folder onto their dashboard, or
  connect a Git repository for automatic deploys.
- **GitHub Pages:** push this folder to a GitHub repository and enable Pages in the
  repository settings.

Once you have a live URL, update the placeholder URLs in `index.html`'s `<head>`
(Open Graph tags and the JSON-LD `Person` schema) to match.

## Customizing the design

Colors, fonts, and spacing are all defined as CSS custom properties at the top of
`styles.css` (`:root { ... }`). Changing a value there updates it everywhere on the
site — no need to hunt through the rest of the file.
