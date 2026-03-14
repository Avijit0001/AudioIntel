/* ===========================
   Audio Intel — Navigation Helper
   (No authentication required)
   =========================== */

(function () {
  'use strict';

  const API_BASE = 'http://localhost:8000';

  // ---- Helpers ----
  function getCurrentPage() {
    const path = window.location.pathname;
    const page = path.substring(path.lastIndexOf('/') + 1) || 'index.html';
    return page;
  }

  // ---- Build Navbar Links ----
  function buildNavbar() {
    const navLinks = document.getElementById('navLinks');
    if (!navLinks) return;

    const currentPage = getCurrentPage();

    navLinks.innerHTML = '';

    const homeLink = createNavLink('index.html', 'Home', currentPage);
    navLinks.appendChild(homeLink);

    const recommendLink = createNavLink('chat.html', 'Recommend', currentPage);
    navLinks.appendChild(recommendLink);

    const aboutLink = createNavLink('about.html', 'About', currentPage);
    navLinks.appendChild(aboutLink);
  }

  function createNavLink(href, text, currentPage) {
    const a = document.createElement('a');
    a.href = href;
    a.textContent = text;
    const linkPage = href.substring(href.lastIndexOf('/') + 1);
    if (linkPage === currentPage) {
      a.classList.add('active');
    }
    return a;
  }

  // ---- Expose API_BASE for chat.js ----
  window.audioIntelAuth = {
    API_BASE,
  };

  // ---- Mobile nav toggle ----
  function initMobileToggle() {
    const toggleBtn = document.getElementById('navToggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', function () {
        document.getElementById('navLinks').classList.toggle('open');
      });
    }
  }

  // ---- Init ----
  buildNavbar();
  initMobileToggle();

})();
