/**
 * VendorBridge — Sidebar Loader (Direct Inject, no fetch needed)
 * ─────────────────────────────────────────────────────────────
 * HOW TO USE IN ANY PAGE:
 *   1. Add <div id="sidebar-root"></div> at start of .page-wrapper
 *   2. Set active page:  window.SIDEBAR_ACTIVE = 'vendors';
 *   3. Include this script: <script src="../assets/js/sidebar-loader.js"></script>
 */

(function () {
  "use strict";

  // ── Inject CSS ─────────────────────────────────────────────
  const STYLE = `
    .sidebar {
      width: 240px; min-height: 100vh;
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border-primary);
      display: flex; flex-direction: column;
      position: fixed; top: 0; left: 0; bottom: 0;
      z-index: 100; transition: transform 0.25s ease;
    }
    .sidebar-logo {
      padding: 20px 18px 16px;
      display: flex; align-items: center; gap: 10px;
      border-bottom: 1px solid var(--border-primary);
      min-height: 64px; text-decoration: none;
    }
    .sidebar-logo .logo-icon {
      width: 34px; height: 34px; background: var(--accent-primary);
      border-radius: 9px; display: flex; align-items: center; justify-content: center;
      font-family: 'Syne', sans-serif; font-size: 15px; font-weight: 800; color: #fff;
      flex-shrink: 0; box-shadow: 0 4px 12px rgba(79,142,247,0.3);
    }
    .sidebar-logo .logo-text {
      font-family: 'Syne', sans-serif; font-size: 1.05rem; font-weight: 700;
      letter-spacing: -0.02em; color: var(--text-primary);
    }
    .sidebar-logo .logo-text em { color: var(--accent-primary); font-style: normal; }
    .sidebar-nav { flex: 1; padding: 10px 8px; overflow-y: auto; }
    .nav-section-label {
      font-size: 0.65rem; font-weight: 600; letter-spacing: 0.1em;
      text-transform: uppercase; color: var(--text-muted); padding: 12px 10px 4px;
    }
    .nav-item {
      display: flex; align-items: center; gap: 10px;
      padding: 9px 10px; font-size: 0.875rem; font-weight: 500;
      color: var(--text-secondary); text-decoration: none;
      border-radius: 8px; cursor: pointer; margin-bottom: 2px;
      transition: background 0.18s ease, color 0.18s ease;
      position: relative;
    }
    .nav-item:hover { background: var(--bg-tertiary); color: var(--text-primary); text-decoration: none; }
    .nav-item.active { color: var(--accent-primary); background: var(--accent-primary-light); }
    .nav-item .nav-icon { font-size: 1rem; width: 20px; text-align: center; display: flex; align-items: center; justify-content: center; }
    .nav-badge {
      margin-left: auto; background: var(--accent-primary); color: #fff;
      font-size: 0.65rem; font-weight: 700; padding: 1px 7px;
      border-radius: 100px; min-width: 20px; text-align: center;
    }
    .sidebar-footer { padding: 12px 8px; border-top: 1px solid var(--border-primary); }
    .sidebar-user {
      display: flex; align-items: center; gap: 10px;
      padding: 8px 10px; border-radius: 10px; cursor: pointer;
      transition: background 0.18s ease; position: relative;
    }
    .sidebar-user:hover { background: var(--bg-tertiary); }
    .user-avatar {
      width: 34px; height: 34px;
      background: linear-gradient(135deg, var(--accent-primary), #7c5fcf);
      border-radius: 50%; display: flex; align-items: center; justify-content: center;
      font-size: 0.75rem; font-weight: 700; color: #fff; flex-shrink: 0;
    }
    .user-info { flex: 1; min-width: 0; }
    .user-name { font-size: 0.8rem; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .user-role { font-size: 0.68rem; color: var(--text-muted); }
    .user-settings-btn {
      width: 26px; height: 26px; border: none; background: none;
      color: var(--text-muted); font-size: 0.9rem; cursor: pointer;
      border-radius: 6px; display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; transition: background 0.15s, color 0.15s;
    }
    .user-settings-btn:hover { background: var(--accent-primary-light); color: var(--accent-primary); }

    /* Settings flyout */
    .settings-flyout {
      display: none; position: absolute; bottom: calc(100% + 8px); left: 0; right: 0;
      background: var(--bg-card); border: 1px solid var(--border-primary);
      border-radius: 12px; box-shadow: 0 12px 32px rgba(0,0,0,0.35);
      z-index: 200; overflow: hidden; animation: vbFlyoutIn 0.18s ease;
    }
    .settings-flyout.open { display: block; }
    @keyframes vbFlyoutIn { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
    .flyout-header {
      padding: 12px 14px 8px; font-size: 0.68rem; font-weight: 700;
      letter-spacing: 0.08em; text-transform: uppercase;
      color: var(--text-muted); border-bottom: 1px solid var(--border-primary);
    }
    .flyout-item {
      display: flex; align-items: center; gap: 10px; padding: 10px 14px;
      font-size: 0.82rem; font-weight: 500; color: var(--text-secondary);
      cursor: pointer; transition: background 0.15s, color 0.15s;
      border-bottom: 1px solid var(--border-secondary); text-decoration: none;
    }
    .flyout-item:last-child { border-bottom: none; }
    .flyout-item:hover { background: var(--bg-tertiary); color: var(--text-primary); text-decoration: none; }
    .flyout-item.danger { color: #ef4444; }
    .flyout-item.danger:hover { background: rgba(239,68,68,0.08); }
    .flyout-item .fi-icon {
      width: 28px; height: 28px; border-radius: 7px;
      display: flex; align-items: center; justify-content: center;
      font-size: 0.85rem; flex-shrink: 0; background: var(--bg-tertiary);
    }
    .flyout-theme-row {
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 14px; border-bottom: 1px solid var(--border-secondary);
    }
    .flyout-theme-label {
      display: flex; align-items: center; gap: 10px;
      font-size: 0.82rem; font-weight: 500; color: var(--text-secondary);
    }
    .flyout-theme-label .fi-icon {
      width: 28px; height: 28px; border-radius: 7px; background: var(--bg-tertiary);
      display: flex; align-items: center; justify-content: center; font-size: 0.85rem;
    }
    .theme-toggle-pill {
      width: 38px; height: 21px; background: var(--bg-tertiary);
      border: 1px solid var(--border-primary); border-radius: 100px;
      cursor: pointer; position: relative; transition: background 0.25s; flex-shrink: 0;
    }
    .theme-toggle-pill.dark-on { background: var(--accent-primary); border-color: var(--accent-primary); }
    .theme-toggle-pill::after {
      content: ''; position: absolute; top: 2px; left: 2px;
      width: 15px; height: 15px; border-radius: 50%; background: #fff;
      transition: transform 0.25s; box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    }
    .theme-toggle-pill.dark-on::after { transform: translateX(17px); }

    /* Mobile */
    .sidebar-overlay { display: none; position: fixed; inset: 0; z-index: 99; background: rgba(0,0,0,0.5); }
    .sidebar-overlay.show { display: block; }
    @media (max-width: 900px) {
      .sidebar { transform: translateX(-100%); }
      .sidebar.open { transform: translateX(0); }
    }
  `;

  // ── Inject HTML ────────────────────────────────────────────
  const HTML = `
    <aside class="sidebar" id="sidebar">
      <a href="dashboard.html" class="sidebar-logo">
        <div class="logo-icon">V</div>
        <span class="logo-text">Vendor<em>Bridge</em></span>
      </a>

      <nav class="sidebar-nav">
        <div class="nav-section-label">Main</div>
        <a href="dashboard.html"       class="nav-item" data-page="dashboard">
          <span class="nav-icon">🏠</span> Dashboard
        </a>
        <a href="vendors.html"         class="nav-item" data-page="vendors">
          <span class="nav-icon">🏢</span> Vendors
        </a>
        <a href="rfqs.html"            class="nav-item" data-page="rfqs">
          <span class="nav-icon">📋</span> RFQs
          <span class="nav-badge" id="rfq-badge">0</span>
        </a>
        <a href="quotations.html"      class="nav-item" data-page="quotations">
          <span class="nav-icon">💬</span> Quotations
        </a>
        <a href="comparison.html"      class="nav-item" data-page="comparison">
          <span class="nav-icon">⚖️</span> Comparison
        </a>

        <div class="nav-section-label">Procurement</div>
        <a href="approvals.html"       class="nav-item" data-page="approvals">
          <span class="nav-icon">✅</span> Approvals
          <span class="nav-badge" id="approval-badge">0</span>
        </a>
        <a href="purchase-orders.html" class="nav-item" data-page="purchase-orders">
          <span class="nav-icon">📦</span> Purchase Orders
        </a>
        <a href="invoices.html"        class="nav-item" data-page="invoices">
          <span class="nav-icon">🧾</span> Invoices
        </a>

        <div class="nav-section-label">Analytics</div>
        <a href="activity.html"        class="nav-item" data-page="activity">
          <span class="nav-icon">📡</span> Activity Logs
        </a>
        <a href="reports.html"         class="nav-item" data-page="reports">
          <span class="nav-icon">📊</span> Reports
        </a>
      </nav>

      <div class="sidebar-footer">
        <div style="position:relative;">
          <!-- Settings flyout -->
          <div class="settings-flyout" id="settings-flyout">
            <div class="flyout-header">Account &amp; Preferences</div>
            <a href="profile.html" class="flyout-item">
              <div class="fi-icon">👤</div> My Profile
            </a>
            <div class="flyout-theme-row">
              <span class="flyout-theme-label">
                <div class="fi-icon" id="theme-flyout-icon">🌙</div>
                Dark Mode
              </span>
              <div class="theme-toggle-pill" id="theme-pill"></div>
            </div>
            <a href="settings.html" class="flyout-item">
              <div class="fi-icon">⚙️</div> Settings
            </a>
            <a href="help.html" class="flyout-item">
              <div class="fi-icon">❓</div> Help &amp; Docs
            </a>
            <div class="flyout-item danger" id="flyout-logout-btn">
              <div class="fi-icon" style="background:rgba(239,68,68,0.1)">⏏️</div> Sign Out
            </div>
          </div>

          <!-- User row -->
          <div class="sidebar-user" id="user-profile-btn">
            <div class="user-avatar" id="user-avatar-initials">PO</div>
            <div class="user-info">
              <div class="user-name" id="sidebar-user-name">Loading…</div>
              <div class="user-role" id="sidebar-user-role">—</div>
            </div>
            <button class="user-settings-btn" id="settings-gear-btn" title="Settings">⚙️</button>
          </div>
        </div>
      </div>
    </aside>

    <div class="sidebar-overlay" id="sidebar-overlay"></div>
  `;

  // ── Mount everything ───────────────────────────────────────
  function mount() {
    // 1. Styles
    if (!document.getElementById("vb-sidebar-styles")) {
      const styleEl = document.createElement("style");
      styleEl.id = "vb-sidebar-styles";
      styleEl.textContent = STYLE;
      document.head.appendChild(styleEl);
    }

    // 2. HTML into #sidebar-root
    const root = document.getElementById("sidebar-root");
    if (!root) {
      console.warn("[VB Sidebar] #sidebar-root not found");
      return;
    }
    root.innerHTML = HTML;

    // 3. Highlight active nav item
    const active =
      window.SIDEBAR_ACTIVE ||
      location.pathname.split("/").pop().replace(".html", "") ||
      "dashboard";
    document.querySelectorAll(".sidebar .nav-item[data-page]").forEach((el) => {
      el.classList.toggle("active", el.dataset.page === active);
    });

    // 4. Load user info
    loadSidebarUser();

    // 5. Wire settings flyout
    wireFlyout();

    // 6. Wire mobile overlay
    wireMobile();
  }

  // ── Load user ──────────────────────────────────────────────
  function vendorInitials(name) {
    return (name || "VB")
      .split(" ")
      .map((w) => w[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
  }

  function applyUserToSidebar(u) {
    const name =
      `${u.first_name || ""} ${u.last_name || ""}`.trim() || u.email || "User";
    const n = document.getElementById("sidebar-user-name");
    const r = document.getElementById("sidebar-user-role");
    const a = document.getElementById("user-avatar-initials");
    if (n) n.textContent = name;
    if (r)
      r.textContent = (u.role || "")
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());
    if (a) a.textContent = vendorInitials(name);
  }

  function loadSidebarUser() {
    const cached = localStorage.getItem("vb_user");
    if (cached) {
      try {
        applyUserToSidebar(JSON.parse(cached));
        return;
      } catch {}
    }
    // Demo fallback
    applyUserToSidebar({
      first_name: "Procurement",
      last_name: "Officer",
      role: "procurement_officer",
    });
  }

  // ── Settings flyout ────────────────────────────────────────
  function wireFlyout() {
    const flyout = document.getElementById("settings-flyout");
    const gearBtn = document.getElementById("settings-gear-btn");
    const pill = document.getElementById("theme-pill");
    const icon = document.getElementById("theme-flyout-icon");

    function closeFlyout() {
      flyout && flyout.classList.remove("open");
    }

    function syncPill() {
      const isDark =
        document.documentElement.getAttribute("data-theme") === "dark";
      pill && pill.classList.toggle("dark-on", isDark);
      if (icon) icon.textContent = isDark ? "🌙" : "☀️";
    }
    syncPill();

    // Gear button opens/closes flyout
    gearBtn &&
      gearBtn.addEventListener("click", function (e) {
        e.stopPropagation();
        flyout && flyout.classList.toggle("open");
      });

    // Clicking user row (not gear) also toggles
    document
      .getElementById("user-profile-btn")
      ?.addEventListener("click", function (e) {
        if (gearBtn && (e.target === gearBtn || gearBtn.contains(e.target)))
          return;
        flyout && flyout.classList.toggle("open");
      });

    // Outside click closes
    document.addEventListener("click", function (e) {
      if (!flyout || !flyout.classList.contains("open")) return;
      if (
        !flyout.contains(e.target) &&
        !(gearBtn && gearBtn.contains(e.target))
      )
        closeFlyout();
    });

    // Theme pill
    pill &&
      pill.addEventListener("click", function () {
        const isDark =
          document.documentElement.getAttribute("data-theme") === "dark";
        const next = isDark ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("vb_theme", next);
        syncPill();
        if (window.ThemeManager) window.ThemeManager.apply(next);
      });

    // Keep pill in sync if theme changes externally
    new MutationObserver(syncPill).observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    // Sign out from flyout
    document
      .getElementById("flyout-logout-btn")
      ?.addEventListener("click", function () {
        closeFlyout();
        window.dispatchEvent(new CustomEvent("vb:logout"));
        document.getElementById("logout-modal")?.classList.add("show");
      });
  }

  // ── Mobile ─────────────────────────────────────────────────
  function wireMobile() {
    document
      .getElementById("sidebar-overlay")
      ?.addEventListener("click", () => {
        document.getElementById("sidebar")?.classList.remove("open");
        document.getElementById("sidebar-overlay")?.classList.remove("show");
      });
    // Also wire the mobile menu button if it already exists in the page
    document
      .getElementById("mobile-menu-btn")
      ?.addEventListener("click", () => {
        document.getElementById("sidebar")?.classList.toggle("open");
        document.getElementById("sidebar-overlay")?.classList.toggle("show");
      });
  }

  // ── Run ────────────────────────────────────────────────────
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
