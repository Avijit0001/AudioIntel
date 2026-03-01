/* ===========================
   Audio Intel — Auth Guard
   (Now backed by FastAPI + Supabase)
   =========================== */

(function () {
  'use strict';

  const API_BASE = 'http://localhost:8000';

  // localStorage keys
  const AUTH_KEY        = 'audioIntelAuth';
  const USERNAME_KEY    = 'audioIntelUser';
  const TOKEN_KEY       = 'audioIntelToken';
  const REFRESH_KEY     = 'audioIntelRefresh';
  const EMAIL_KEY       = 'audioIntelEmail';

  // Pages that require authentication
  const PROTECTED_PAGES = ['chat.html', 'about.html'];

  // ---- Helpers ----
  function isLoggedIn() {
    return localStorage.getItem(AUTH_KEY) === 'true';
  }

  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || '';
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
  function guardPage() {
    const page = getCurrentPage();
    if (isProtected(page) && !isLoggedIn()) {
      sessionStorage.setItem('audioIntelRedirect', page);
      window.location.href = 'login.html';
    }
  }

  // ---- Build Navbar Links ----
  function buildNavbar() {
    const navLinks = document.getElementById('navLinks');
    if (!navLinks) return;

    const currentPage = getCurrentPage();
    const loggedIn = isLoggedIn();
    const userName = localStorage.getItem(USERNAME_KEY) || 'User';

    navLinks.innerHTML = '';

    const homeLink = createNavLink('index.html', 'Home', currentPage);
    navLinks.appendChild(homeLink);

    if (loggedIn) {
      const recommendLink = createNavLink('chat.html', 'Recommend', currentPage);
      navLinks.appendChild(recommendLink);

      const aboutLink = createNavLink('about.html', 'About', currentPage);
      navLinks.appendChild(aboutLink);

      const userBadge = document.createElement('div');
      userBadge.className = 'nav-user-badge';
      userBadge.innerHTML = `
        <span class="nav-user-name">👤 ${escapeHtml(userName)}</span>
        <button class="btn btn-outline btn-sm nav-logout-btn" id="navLogoutBtn">Logout</button>
      `;
      navLinks.appendChild(userBadge);
    } else {
      const loginLink = createNavLink('login.html', 'Login / Sign Up', currentPage);
      loginLink.classList.add('btn', 'btn-primary', 'btn-sm');
      loginLink.style.color = '#fff';
      navLinks.appendChild(loginLink);
    }

    const logoutBtn = document.getElementById('navLogoutBtn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', async function (e) {
        e.preventDefault();
        // Call backend sign-out
        try {
          const token = getToken();
          if (token) {
            await fetch(`${API_BASE}/auth/signout`, {
              method: 'POST',
              headers: { 'Authorization': `Bearer ${token}` },
            });
          }
        } catch (_) { /* ignore errors during sign-out */ }
        // Clear local storage
        localStorage.removeItem(AUTH_KEY);
        localStorage.removeItem(USERNAME_KEY);
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        localStorage.removeItem(EMAIL_KEY);
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

  // ---- Login / Register via Backend API ----
  window.audioIntelAuth = {

    /**
     * Sign in through the FastAPI backend → Supabase.
     * Returns a Promise so the caller can await it.
     */
    login: async function (email, password) {
      const res = await fetch(`${API_BASE}/auth/signin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Sign-in failed');
      }

      const data = await res.json();
      // Persist auth state
      localStorage.setItem(AUTH_KEY, 'true');
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(REFRESH_KEY, data.refresh_token);
      localStorage.setItem(EMAIL_KEY, data.email);
      localStorage.setItem(USERNAME_KEY, data.full_name || email.split('@')[0]);

      // Redirect
      const redirect = sessionStorage.getItem('audioIntelRedirect') || 'chat.html';
      sessionStorage.removeItem('audioIntelRedirect');
      window.location.href = redirect;
    },

    /**
     * Register a new account through the FastAPI backend → Supabase.
     */
    register: async function (fullName, email, password) {
      const res = await fetch(`${API_BASE}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: fullName }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Registration failed');
      }

      const data = await res.json();

      if (data.access_token) {
        localStorage.setItem(AUTH_KEY, 'true');
        localStorage.setItem(TOKEN_KEY, data.access_token);
        localStorage.setItem(REFRESH_KEY, data.refresh_token);
        localStorage.setItem(EMAIL_KEY, data.email);
        localStorage.setItem(USERNAME_KEY, fullName);

        const redirect = sessionStorage.getItem('audioIntelRedirect') || 'chat.html';
        sessionStorage.removeItem('audioIntelRedirect');
        window.location.href = redirect;
      } else {
        // Email confirmation required — inform user
        alert('Account created! Please check your email to confirm your account, then sign in.');
        // Switch to login tab
        document.querySelector('.auth-tab[data-tab="login"]')?.click();
      }
    },

    isLoggedIn,
    getToken,
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
  guardPage();
  buildNavbar();
  initMobileToggle();

})();
