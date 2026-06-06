/* ============================================
   VENDORBRIDGE - THEME MANAGER
   Dark/Light mode with localStorage
   ============================================ */

const ThemeManager = (() => {
  const STORAGE_KEY = "vb_theme";
  const DEFAULT_THEME = "dark";

  const icons = {
    dark: "☀️", // shown in dark mode (click to go light)
    light: "🌙", // shown in light mode (click to go dark)
  };

  function getStored() {
    return localStorage.getItem(STORAGE_KEY) || DEFAULT_THEME;
  }

  function apply(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(STORAGE_KEY, theme);

    // Update all toggle buttons on page
    document.querySelectorAll(".theme-toggle").forEach((btn) => {
      btn.textContent = icons[theme];
      btn.setAttribute(
        "title",
        theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"
      );
      btn.setAttribute("aria-label", btn.getAttribute("title"));
    });
  }

  function toggle() {
    const current = getStored();
    apply(current === "dark" ? "light" : "dark");
  }

  function init() {
    // Apply saved theme immediately (before paint)
    apply(getStored());

    // Bind all toggle buttons
    document.addEventListener("click", (e) => {
      if (e.target.closest(".theme-toggle")) toggle();
    });
  }

  return { init, toggle, apply, getStored };
})();

// Auto-init on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", ThemeManager.init);
} else {
  ThemeManager.init();
}
