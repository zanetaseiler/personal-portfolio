/* =========================================================================
   Žaneta Seilerová — Portfolio Scripts
   Vanilla JS, no dependencies. Organized into small, independent features
   so any one of them can be removed without breaking the others.
   ========================================================================= */

document.addEventListener('DOMContentLoaded', function () {

  /* -----------------------------------------------------------------
     STICKY HEADER SHADOW
     Adds a subtle shadow/border to the header once the page scrolls,
     so it reads as "lifted" above the content instead of blending in.
     ----------------------------------------------------------------- */
  var header = document.getElementById('site-header');

  function updateHeaderOnScroll() {
    if (window.scrollY > 8) {
      header.classList.add('is-scrolled');
    } else {
      header.classList.remove('is-scrolled');
    }
  }

  updateHeaderOnScroll();
  window.addEventListener('scroll', updateHeaderOnScroll, { passive: true });

  /* -----------------------------------------------------------------
     MOBILE MENU TOGGLE
     ----------------------------------------------------------------- */
  var menuToggle = document.getElementById('menu-toggle');
  var mainNav = document.getElementById('main-nav');

  function closeMenu() {
    menuToggle.classList.remove('is-open');
    menuToggle.setAttribute('aria-expanded', 'false');
    menuToggle.setAttribute('aria-label', 'Open menu');
    mainNav.classList.remove('is-open');
  }

  function openMenu() {
    menuToggle.classList.add('is-open');
    menuToggle.setAttribute('aria-expanded', 'true');
    menuToggle.setAttribute('aria-label', 'Close menu');
    mainNav.classList.add('is-open');
  }

  menuToggle.addEventListener('click', function () {
    var isOpen = menuToggle.classList.contains('is-open');
    if (isOpen) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  /* Close the mobile menu after a nav link is clicked, so the anchor
     scroll isn't immediately obscured by the still-open menu panel. */
  var navLinks = mainNav.querySelectorAll('.nav-link');
  navLinks.forEach(function (link) {
    link.addEventListener('click', closeMenu);
  });

  /* -----------------------------------------------------------------
     ACTIVE NAV LINK ON SCROLL
     Highlights the nav item matching whichever section is currently
     in view, using IntersectionObserver rather than scroll-position math.
     ----------------------------------------------------------------- */
  var sections = document.querySelectorAll('main section[id]');

  var navObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      var link = document.querySelector('.nav-link[href="#' + entry.target.id + '"]');
      if (!link) return;
      if (entry.isIntersecting) {
        navLinks.forEach(function (l) { l.classList.remove('is-active'); });
        link.classList.add('is-active');
      }
    });
  }, { rootMargin: '-40% 0px -55% 0px' }); /* triggers when a section is roughly centered in the viewport */

  sections.forEach(function (section) {
    navObserver.observe(section);
  });

  /* -----------------------------------------------------------------
     SCROLL-REVEAL ANIMATIONS
     Elements with the .reveal class fade/slide in once they enter the
     viewport. Runs once per element, then stops observing it.
     ----------------------------------------------------------------- */
  var revealEls = document.querySelectorAll('.reveal');

  var revealObserver = new IntersectionObserver(function (entries, observer) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  revealEls.forEach(function (el) {
    revealObserver.observe(el);
  });

  /* -----------------------------------------------------------------
     CASE STUDY ACCORDION
     Each case study panel toggles independently via aria-expanded;
     styles.css handles the open/closed animation off that attribute.
     ----------------------------------------------------------------- */
  var caseStudyToggles = document.querySelectorAll('.case-study-toggle');

  caseStudyToggles.forEach(function (toggle) {
    toggle.addEventListener('click', function () {
      var isExpanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!isExpanded));
    });
  });

  /* -----------------------------------------------------------------
     CONTACT FORM
     No backend is connected yet (see the HTML comments above the form
     for Formspree / Netlify Forms setup). For now this just validates
     the fields with the browser's built-in validation and shows a
     friendly inline message instead of actually sending anything.

     Once you connect Formspree or Netlify Forms, you can either delete
     this handler entirely (letting the form submit normally) or keep
     it and replace the body of the "if (form.checkValidity())" block
     with a fetch() call to your form endpoint.
     ----------------------------------------------------------------- */
  var contactForm = document.getElementById('contact-form');
  var formStatus = document.getElementById('form-status');

  if (contactForm) {
    contactForm.addEventListener('submit', function (event) {
      event.preventDefault();

      if (!contactForm.checkValidity()) {
        contactForm.reportValidity();
        return;
      }

      formStatus.textContent =
        'Thanks for reaching out! This form isn\'t connected to an email service yet — ' +
        'see the comments in index.html for how to connect Formspree or Netlify Forms.';
      contactForm.reset();
    });
  }

  /* -----------------------------------------------------------------
     FOOTER YEAR
     Keeps the copyright year current without manual edits.
     ----------------------------------------------------------------- */
  var footerYear = document.getElementById('footer-year');
  if (footerYear) {
    footerYear.textContent = String(new Date().getFullYear());
  }

});
