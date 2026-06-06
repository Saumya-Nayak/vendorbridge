/* ============================================
   VENDORBRIDGE - UTILITIES
   Toast, Sidebar, Formatters, Validators
   ============================================ */

/* ---- TOAST ---- */
const Toast = (() => {
  function getContainer() {
    let c = document.querySelector(".toast-container");
    if (!c) {
      c = document.createElement("div");
      c.className = "toast-container";
      document.body.appendChild(c);
    }
    return c;
  }

  function show(type, title, message = "", duration = 4000) {
    const icons = { success: "✅", error: "❌", warning: "⚠️", info: "ℹ️" };
    const container = getContainer();

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type] || "ℹ️"}</span>
        <div class="toast-body">
          <div class="toast-title">${title}</div>
          ${message ? `<div class="toast-msg">${message}</div>` : ""}
        </div>
        <button class="toast-close" onclick="this.closest('.toast').remove()">✕</button>
      `;

    container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => {
        toast.style.animation = "slideInRight 0.25s ease reverse";
        setTimeout(() => toast.remove(), 250);
      }, duration);
    }
  }

  return {
    success: (title, msg, dur) => show("success", title, msg, dur),
    error: (title, msg, dur) => show("error", title, msg, dur),
    warning: (title, msg, dur) => show("warning", title, msg, dur),
    info: (title, msg, dur) => show("info", title, msg, dur),
  };
})();

/* ---- SIDEBAR ---- */
const Sidebar = (() => {
  const COLLAPSED_KEY = "vb_sidebar_collapsed";

  function init() {
    const sidebar = document.querySelector(".sidebar");
    const mainContent = document.querySelector(".main-content");
    if (!sidebar) return;

    // Restore collapsed state
    if (localStorage.getItem(COLLAPSED_KEY) === "true") {
      sidebar.classList.add("collapsed");
      mainContent?.classList.add("sidebar-collapsed");
    }

    // Toggle button
    document
      .querySelectorAll(".topbar-toggle, .sidebar-toggle")
      .forEach((btn) => {
        btn.addEventListener("click", () => toggle());
      });

    // Set active nav item based on current page
    setActiveNav();
  }

  function toggle() {
    const sidebar = document.querySelector(".sidebar");
    const mainContent = document.querySelector(".main-content");
    if (!sidebar) return;

    sidebar.classList.toggle("collapsed");
    mainContent?.classList.toggle("sidebar-collapsed");
    localStorage.setItem(
      COLLAPSED_KEY,
      sidebar.classList.contains("collapsed")
    );
  }

  function setActiveNav() {
    const currentPage = window.location.pathname.split("/").pop();
    document.querySelectorAll(".nav-item").forEach((item) => {
      const href = item.getAttribute("href") || "";
      if (href.includes(currentPage) && currentPage !== "") {
        item.classList.add("active");
      }
    });
  }

  return { init, toggle };
})();

/* ---- FORMATTERS ---- */
const Format = {
  currency: (amount, currency = "₹") => {
    if (amount === null || amount === undefined) return "—";
    return `${currency}${Number(amount).toLocaleString("en-IN", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    })}`;
  },

  date: (dateStr) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  },

  dateTime: (dateStr) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  },

  timeAgo: (dateStr) => {
    if (!dateStr) return "—";
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    if (mins < 1) return "Just now";
    if (mins < 60) return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return Format.date(dateStr);
  },

  initials: (name) => {
    if (!name) return "??";
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  },

  truncate: (str, len = 40) => {
    if (!str) return "—";
    return str.length > len ? str.slice(0, len) + "..." : str;
  },

  number: (n) => {
    if (n >= 10000000) return (n / 10000000).toFixed(1) + " Cr";
    if (n >= 100000) return (n / 100000).toFixed(1) + " L";
    if (n >= 1000) return (n / 1000).toFixed(1) + "K";
    return n.toString();
  },

  gst: (amount, rate = 18) => {
    const gst = (amount * rate) / 100;
    return { gst, total: amount + gst };
  },
};

/* ---- VALIDATORS ---- */
const Validate = {
  required: (val) =>
    val !== null && val !== undefined && val.toString().trim() !== "",
  email: (val) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val),
  phone: (val) => /^[6-9]\d{9}$/.test(val.replace(/\s/g, "")),
  gst: (val) =>
    /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(val),
  password: (val) => val && val.length >= 8,
  positive: (val) => !isNaN(val) && Number(val) > 0,
  maxLength: (val, max) => val.length <= max,

  form: (fields) => {
    const errors = {};
    let valid = true;
    fields.forEach(({ name, value, rules }) => {
      for (const rule of rules) {
        if (rule === "required" && !Validate.required(value)) {
          errors[name] = "This field is required";
          valid = false;
          break;
        }
        if (rule === "email" && !Validate.email(value)) {
          errors[name] = "Enter a valid email address";
          valid = false;
          break;
        }
        if (rule === "phone" && !Validate.phone(value)) {
          errors[name] = "Enter a valid 10-digit phone number";
          valid = false;
          break;
        }
        if (rule === "gst" && !Validate.gst(value)) {
          errors[name] = "Enter a valid GST number";
          valid = false;
          break;
        }
        if (rule === "password" && !Validate.password(value)) {
          errors[name] = "Password must be at least 8 characters";
          valid = false;
          break;
        }
        if (rule === "positive" && !Validate.positive(value)) {
          errors[name] = "Enter a valid positive number";
          valid = false;
          break;
        }
      }
    });
    return { valid, errors };
  },

  showError: (inputEl, message) => {
    inputEl.classList.add("error");
    let err = inputEl.parentElement.querySelector(".form-error");
    if (!err) {
      err = document.createElement("div");
      err.className = "form-error";
      inputEl.parentElement.appendChild(err);
    }
    err.innerHTML = `⚠ ${message}`;
  },

  clearError: (inputEl) => {
    inputEl.classList.remove("error");
    const err = inputEl.parentElement.querySelector(".form-error");
    if (err) err.remove();
  },

  clearAllErrors: (formEl) => {
    formEl
      .querySelectorAll(".form-control.error")
      .forEach((el) => Validate.clearError(el));
  },
};

/* ---- MODAL HELPER ---- */
const Modal = {
  open: (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.style.display = "flex";
      document.body.style.overflow = "hidden";
    }
  },
  close: (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.style.display = "none";
      document.body.style.overflow = "";
    }
  },
  closeAll: () => {
    document.querySelectorAll(".modal-overlay").forEach((m) => {
      m.style.display = "none";
    });
    document.body.style.overflow = "";
  },
};

// Close modal on overlay click
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("modal-overlay")) Modal.closeAll();
});

// Close modal on Escape key
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") Modal.closeAll();
});

/* ---- AUTH GUARD ---- */
function requireAuth() {
  if (!API.isLoggedIn()) {
    window.location.href = "/frontend/pages/login.html";
  }
}

function requireRole(...roles) {
  const user = API.getUser();
  if (!user || !roles.includes(user.role)) {
    Toast.error(
      "Access Denied",
      "You do not have permission to view this page."
    );
    setTimeout(
      () => (window.location.href = "/frontend/pages/dashboard.html"),
      1500
    );
  }
}

/* ---- DOM HELPERS ---- */
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);

function createElement(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else el.setAttribute(k, v);
  });
  children.forEach((child) => el.appendChild(child));
  return el;
}

/* ---- INIT ON DOM READY ---- */
document.addEventListener("DOMContentLoaded", () => {
  Sidebar.init();
});
