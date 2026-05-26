// Kiirus KPI grid custom component.
// Receives {rows: [{cols: 3, cards: [...]}, ...], theme, density} from Python.
// Every postMessage MUST include isStreamlitMessage:true (Streamlit filter).

(function () {
  const html = document.documentElement;
  const root = document.getElementById("kpi-root");

  function post(type, data) {
    parent.postMessage(
      Object.assign({ isStreamlitMessage: true, type: type }, data || {}),
      "*"
    );
  }

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v == null || v === false) continue;
        if (k === "class") node.className = v;
        else if (k === "style") node.setAttribute("style", v);
        else if (k === "html") node.innerHTML = v;
        else node.setAttribute(k, v);
      }
    }
    for (const c of children) {
      if (c == null) continue;
      if (typeof c === "string") node.appendChild(document.createTextNode(c));
      else node.appendChild(c);
    }
    return node;
  }

  function svgNS(tag, attrs, ...children) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    if (attrs) for (const [k, v] of Object.entries(attrs)) {
      if (v == null) continue;
      node.setAttribute(k, v);
    }
    for (const c of children) {
      if (c == null) continue;
      if (typeof c === "string") node.appendChild(document.createTextNode(c));
      else node.appendChild(c);
    }
    return node;
  }

  function sparkline(data, color) {
    if (!data || data.length < 2) return null;
    const w = 56, h = 22;
    const max = Math.max(...data), min = Math.min(...data);
    const step = w / (data.length - 1);
    const pts = data.map((v, i) => `${i * step},${h - ((v - min) / (max - min || 1)) * h}`).join(" ");
    const svg = svgNS("svg", { class: "kpi-spark", viewBox: `0 0 ${w} ${h}`, preserveAspectRatio: "none" });
    svg.appendChild(svgNS("polyline", {
      points: pts, fill: "none", stroke: color || "var(--accent)",
      "stroke-width": "1.3", "stroke-linejoin": "round", "stroke-linecap": "round",
    }));
    return svg;
  }

  function valueNode(card) {
    if (card.date_range && card.date_from && card.date_to) {
      const span = el("span", null);
      span.appendChild(el("span", { class: "mono" }, card.date_from));
      span.appendChild(el("span", { class: "kpi-daterange-arrow mono" }, " → "));
      span.appendChild(el("span", { class: "mono" }, card.date_to));
      return span;
    }
    const v = el("span", null, String(card.value ?? ""));
    if (card.unit) {
      const sp = el("span", { class: "kpi-value-unit" }, " " + card.unit);
      const wrap = el("span", null);
      wrap.appendChild(v);
      wrap.appendChild(sp);
      return wrap;
    }
    return v;
  }

  function renderCard(card) {
    const classes = ["kpi"];
    if (card.accent) classes.push("kpi-accent");
    if (card.date_range) classes.push("kpi-daterange");

    const labelChildren = [el("span", null, card.label || "")];
    if (card.icon) labelChildren.push(el("span", { class: "kpi-label-ic", html: card.icon }));
    const label = el("div", { class: "kpi-label" }, ...labelChildren);

    const valueColor = card.value_color || "accent";
    const valueClass = "kpi-value text-" + valueColor;
    const value = el("div", { class: valueClass });
    value.appendChild(valueNode(card));

    const card_el = el("div", { class: classes.join(" ") });
    card_el.appendChild(label);

    if (card.spark && card.spark.length) {
      const sparkColor = valueColor === "ok" ? "var(--ok)"
        : valueColor === "bad" ? "var(--bad)"
        : valueColor === "info" ? "var(--info)"
        : valueColor === "warn" ? "var(--warn)"
        : "var(--accent)";
      const s = sparkline(card.spark, sparkColor);
      if (s) card_el.appendChild(s);
    }

    card_el.appendChild(value);

    if (card.progress != null) {
      const pct = Math.max(0, Math.min(100, Number(card.progress.value || 0)));
      const fill = el("div", {
        class: "kpi-progress-fill " + (card.progress.kind || ""),
        style: `width: ${pct}%`,
      });
      card_el.appendChild(el("div", { class: "kpi-progress" }, fill));
    }

    if (card.meta || card.delta) {
      const meta = el("div", { class: "kpi-meta" });
      if (card.delta) {
        meta.appendChild(el("span", {
          class: "kpi-delta " + (card.delta_kind || "flat"),
        }, card.delta));
      }
      if (card.meta) meta.appendChild(el("span", null, card.meta));
      card_el.appendChild(meta);
    }

    return card_el;
  }

  function renderGrid(args) {
    const { rows = [], theme, density } = args || {};
    if (theme) html.dataset.theme = theme;
    if (density) html.dataset.density = density;

    root.innerHTML = "";
    for (const row of rows) {
      const cols = row.cols || (row.cards || []).length || 1;
      const grid = el("div", { class: `kpi-grid kpi-row-${cols}` });
      for (const card of (row.cards || [])) {
        grid.appendChild(renderCard(card));
      }
      root.appendChild(grid);
    }

    postHeight();
  }

  function postHeight() {
    requestAnimationFrame(() => {
      const h = Math.max(40, document.body.scrollHeight + 4);
      post("streamlit:setFrameHeight", { height: h });
    });
  }

  window.addEventListener("message", (e) => {
    if (!e.data || typeof e.data !== "object") return;
    if (e.data.type === "streamlit:render") renderGrid(e.data.args || {});
  });

  post("streamlit:componentReady", { apiVersion: 1 });
  postHeight();
  window.addEventListener("resize", postHeight);
})();
