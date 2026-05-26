// Kiirus sidebar custom component — Streamlit handshake
// Posts {type, section?} events back to Python on click.
// IMPORTANT: every message MUST include isStreamlitMessage:true, otherwise
// Streamlit's frontend silently drops it (see streamlit/static/js/src.*.js
// onMessageEvent — checks Object.hasOwn(e.data, 'isStreamlitMessage')).

(function () {
  const html = document.documentElement;

  function post(type, data) {
    parent.postMessage(
      Object.assign({ isStreamlitMessage: true, type: type }, data || {}),
      "*"
    );
  }

  function sendValue(value) {
    post("streamlit:setComponentValue", { value: value, dataType: "json" });
  }

  function applyArgs(args) {
    const { active, theme, density, sidebar_width, badges, db_meta, version } = args || {};

    if (theme) html.dataset.theme = theme;
    if (density) html.dataset.density = density;
    if (sidebar_width) html.dataset.sidebar = sidebar_width;

    document.querySelectorAll(".nav-row").forEach((row) => {
      row.setAttribute(
        "aria-current",
        row.dataset.section === active ? "true" : "false"
      );
    });

    if (badges && typeof badges === "object") {
      document.querySelectorAll("[data-badge]").forEach((el) => {
        const k = el.dataset.badge;
        const v = badges[k];
        if (v !== undefined && v !== null && v !== "") {
          el.textContent = v;
          el.style.display = "";
        } else {
          el.style.display = "none";
        }
      });
    }

    document.querySelectorAll(".theme-toggle-btn").forEach((btn) => {
      btn.setAttribute(
        "aria-pressed",
        btn.dataset.themeValue === (theme || "dark") ? "true" : "false"
      );
    });

    const dbEl = document.querySelector('[data-slot="db-meta"]');
    if (dbEl && db_meta) dbEl.textContent = db_meta;
    const verEl = document.querySelector('[data-slot="version"]');
    if (verEl && version) verEl.textContent = version;
  }

  function postHeight() {
    post("streamlit:setFrameHeight", { height: Math.max(720, window.innerHeight) });
  }

  window.addEventListener("message", (e) => {
    if (!e.data || typeof e.data !== "object") return;
    if (e.data.type === "streamlit:render") {
      applyArgs(e.data.args || {});
      postHeight();
    }
  });

  document.querySelectorAll(".nav-row").forEach((row) => {
    row.addEventListener("click", () => {
      sendValue({ type: "navigate", section: row.dataset.section, _ts: Date.now() });
    });
  });

  document.querySelectorAll('[data-action="theme"]').forEach((btn) => {
    btn.addEventListener("click", () => {
      sendValue({ type: "set_theme", theme: btn.dataset.themeValue, _ts: Date.now() });
    });
  });

  document.querySelectorAll('[data-action="toggle_collapse"]').forEach((btn) => {
    btn.addEventListener("click", () => {
      sendValue({ type: "toggle_collapse", _ts: Date.now() });
    });
  });

  post("streamlit:componentReady", { apiVersion: 1 });
  postHeight();
  window.addEventListener("resize", postHeight);
})();
