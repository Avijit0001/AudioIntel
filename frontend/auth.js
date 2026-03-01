/* ===========================
   Audio Intel — Auth Guard
   =========================== */

(function () {
  'use strict';

  const AUTH_KEY = 'audioIntelAuth';
  const USERNAME_KEY = 'audioIntelUser';

  // Pages that require authentication (filename only)
  const PROTECTED_PAGES = ['chat.html', 'about.html'];

  // ---- Helpers ----
  function isLoggedIn() {
    return localStorage.getItem(AUTH_KEY) === 'true';
  }

  function getCurrentPage() {
    const path = window.location.pathname;
    const page = path.substring(path.lastIndexOf('/') + 1) || 'index.html';
    return page;
  }

  function isProtected(page) {
    return PROTECTED_PAGES.includes(page);
  }

  // ---- Redirect Guard ----
  // If the current page is protected and the user is NOT logged in,
  // save the intended destination and redirect to login.
  function guardPage() {
    const page = getCurrentPage();
    if (isProtected(page) && !isLoggedIn()) {
      // Store the page they wanted to visit
      sessionStorage.setItem('audioIntelRedirect', page);
      window.location.href = 'login.html';
    }
  }

  // ---- Build Navbar Links ----
  // Replaces the static nav-links content with auth-aware links.
  function buildNavbar() {
    const navLinks = document.getElementById('navLinks');
    if (!navLinks) return;

    const currentPage = getCurrentPage();
    const loggedIn = isLoggedIn();
    const userName = localStorage.getItem(USERNAME_KEY) || 'User';

    // Clear existing links
    navLinks.innerHTML = '';

    // Home — always visible
    const homeLink = createNavLink('index.html', 'Home', currentPage);
    navLinks.appendChild(homeLink);

    if (loggedIn) {
      // Logged-in user sees: Home | Recommend | About | [User Avatar + Logout]
      const recommendLink = createNavLink('chat.html', 'Recommend', currentPage);
      navLinks.appendChild(recommendLink);

      const aboutLink = createNavLink('about.html', 'About', currentPage);
      navLinks.appendChild(aboutLink);

      // User greeting + Logout
      const userBadge = document.createElement('div');
      userBadge.className = 'nav-user-badge';
      userBadge.innerHTML = `
        <span class="nav-user-name">👤 ${escapeHtml(userName)}</span>
        <button class="btn btn-outline btn-sm nav-logout-btn" id="navLogoutBtn">Logout</button>
      `;
      navLinks.appendChild(userBadge);
    } else {
      // Not logged in: Home | Login / Sign Up button
      const loginLink = createNavLink('login.html', 'Login / Sign Up', currentPage);
      loginLink.classList.add('btn', 'btn-primary', 'btn-sm');
      // Override default nav styling for this button
      loginLink.style.color = '#fff';
      navLinks.appendChild(loginLink);
    }

    // Attach logout handler
    const logoutBtn = document.getElementById('navLogoutBtn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', function (e) {
        e.preventDefault();
        localStorage.removeItem(AUTH_KEY);
        localStorage.removeItem(USERNAME_KEY);
        window.location.href = 'index.html';
      });
    }
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

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ---- Login / Register helpers (used by login.html) ----
  window.audioIntelAuth = {
    login: function (email) {
      localStorage.setItem(AUTH_KEY, 'true');
      const name = email.split('@')[0];
      localStorage.setItem(USERNAME_KEY, name);
      // Redirect to saved destination or chat
      const redirect = sessionStorage.getItem('audioIntelRedirect') || 'chat.html';
      sessionStorage.removeItem('audioIntelRedirect');
      window.location.href = redirect;
    },
    register: function (fullName) {
      localStorage.setItem(AUTH_KEY, 'true');
      localStorage.setItem(USERNAME_KEY, fullName);
      const redirect = sessionStorage.getItem('audioIntelRedirect') || 'chat.html';
      sessionStorage.removeItem('audioIntelRedirect');
      window.location.href = redirect;
    },
    isLoggedIn: isLoggedIn
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
  // Guard must run first (before building navbar) so redirect happens immediately
  guardPage();
  // If we're still on this page (no redirect happened), build the navbar
  buildNavbar();
  initMobileToggle();

})();
