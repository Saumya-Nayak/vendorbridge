/* ============================================
   VENDORBRIDGE - API CLIENT
   Base fetch wrapper for all backend calls
   ============================================ */

const API = (() => {
  const BASE_URL = "http://localhost:5000/api";

  function getToken() {
    return localStorage.getItem("vb_token");
  }

  function getHeaders(isFormData = false) {
    const headers = {};
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (!isFormData) headers["Content-Type"] = "application/json";
    return headers;
  }

  async function request(method, endpoint, data = null, isFormData = false) {
    const config = {
      method,
      headers: getHeaders(isFormData),
    };

    if (data) {
      config.body = isFormData ? data : JSON.stringify(data);
    }

    try {
      const res = await fetch(`${BASE_URL}${endpoint}`, config);
      const json = await res.json();

      if (!res.ok) {
        throw {
          status: res.status,
          message: json.message || json.error || "Something went wrong",
        };
      }

      return json;
    } catch (err) {
      if (err.status === 401) {
        // Token expired - redirect to login
        localStorage.removeItem("vb_token");
        localStorage.removeItem("vb_user");
        window.location.href = "/frontend/pages/login.html";
      }
      throw err;
    }
  }

  return {
    get: (endpoint) => request("GET", endpoint),
    post: (endpoint, data) => request("POST", endpoint, data),
    put: (endpoint, data) => request("PUT", endpoint, data),
    patch: (endpoint, data) => request("PATCH", endpoint, data),
    delete: (endpoint) => request("DELETE", endpoint),
    upload: (endpoint, formData) => request("POST", endpoint, formData, true),

    // Auth helpers
    getToken,
    getUser: () => {
      const u = localStorage.getItem("vb_user");
      return u ? JSON.parse(u) : null;
    },
    isLoggedIn: () => !!getToken(),
    logout: () => {
      localStorage.removeItem("vb_token");
      localStorage.removeItem("vb_user");
      window.location.href = "/frontend/pages/login.html";
    },
  };
})();
