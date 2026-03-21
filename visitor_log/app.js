(async function () {
  const $ = (q) => document.querySelector(q);
  const OPENCLAW_HOST = "openclaw.tglauner.com";

  // Use the local API when serving the dashboard on port 5174
  const API_BASE =
    (location.hostname === "localhost" || location.hostname === "127.0.0.1") &&
    location.port === "5174"
      ? "http://127.0.0.1:9000"
      : "";

  function isoLocal(dt) {
    if (!dt) return null;
    const d = new Date(dt);
    const pad = (n) => String(n).padStart(2, "0");
    return (
      `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
      `T${pad(d.getHours())}:${pad(d.getMinutes())}`
    );
  }

  function formatDate(dt) {
    if (!dt) return "";
    const d = new Date(dt);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function rangeParams() {
    const p = new URLSearchParams();
    const start = $("#start").value
      ? new Date($("#start").value).toISOString()
      : "";
    const end = $("#end").value ? new Date($("#end").value).toISOString() : "";
    if (start) p.set("start", start);
    if (end) p.set("end", end);
    return p;
  }

  function withRange(path, extraParams = {}) {
    const url = new URL(path, location.origin);
    const params = new URLSearchParams(url.search);
    for (const [key, value] of rangeParams().entries()) {
      params.set(key, value);
    }
    Object.entries(extraParams).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== "") {
        params.set(key, value);
      }
    });
    const query = params.toString();
    return `${url.pathname}${query ? `?${query}` : ""}`;
  }

  async function fetchJSON(path, opts = {}, extraParams = {}) {
    const r = await fetch(API_BASE + withRange(path, extraParams), opts);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  function emptyRow(colspan, message = "No data yet") {
    return `<tr><td colspan="${colspan}" class="empty">${message}</td></tr>`;
  }

  function renderTiles(container, tiles) {
    container.innerHTML = tiles
      .map(
        ([label, value]) =>
          `<div class="tile"><div class="label">${label}</div><div class="value">${value}</div></div>`
      )
      .join("");
  }

  function inferCtaType(row) {
    if (row.target_type) return row.target_type;
    const href = row.href || "";
    if (href.startsWith("mailto:")) return "email";
    if (href.startsWith("tel:")) return "phone";
    if (href.startsWith("sms:")) return "sms";
    return row.target_domain || "external";
  }

  async function loadOpenClawSnapshot() {
    const d = await fetchJSON("/api/metrics/site_snapshot", {}, { host: OPENCLAW_HOST });
    renderTiles(document.getElementById("openclawTiles"), [
      ["Visitors", d.visitors || 0],
      ["Sessions", d.sessions || 0],
      ["Page Views", d.page_views || 0],
      ["CTA Clicks", d.outbound_clicks || 0],
      ["Email Clicks", d.email_clicks || 0],
      ["Phone Clicks", d.phone_clicks || 0],
    ]);

    const pageRows = d.top_paths || [];
    document.querySelector("#openclawPages tbody").innerHTML = pageRows.length
      ? pageRows
          .map(
            (r) => `
      <tr>
        <td>${r.path || "/"}</td>
        <td>${r.views || 0}</td>
        <td>${r.visitors || 0}</td>
        <td>${r.outbound_clicks || 0}</td>
      </tr>`
          )
          .join("")
      : emptyRow(4, "No OpenClaw traffic in this range yet");

    const ctaRows = d.ctas || [];
    document.querySelector("#openclawCtas tbody").innerHTML = ctaRows.length
      ? ctaRows
          .map(
            (r) => `
      <tr>
        <td>${r.button_id || r.href || "(unlabeled)"}</td>
        <td>${inferCtaType(r)}</td>
        <td>${r.clicks || 0}</td>
        <td>${r.visitors || 0}</td>
      </tr>`
          )
          .join("")
      : emptyRow(4, "No OpenClaw CTA clicks in this range yet");
  }

  async function loadSummary() {
    const s = await fetchJSON("/api/metrics/summary");
    const tiles = [
      ["Visitors", s.visitors],
      ["Sessions", s.sessions],
      ["Page Views", s.page_views],
      ["Udemy Clicks", s.outbound_clicks],
    ];
    if (s.xva_domain) {
      tiles.push(["XVA Clicks", s.xva_clicks ?? 0]);
    }
    tiles.push(
      ["Orders", s.orders],
      ["Net Revenue", `$${(+s.net_revenue).toFixed(2)}`],
      ["CR %", `${(+s.click_to_order_cr_pct).toFixed(2)}%`],
    );
    renderTiles($("#tiles"), tiles);
  }

  async function loadPages() {
    const d = await fetchJSON("/api/metrics/top_pages");
    const rows = d.rows || [];
    document.querySelector("#pages tbody").innerHTML = rows
      .map(
        (r) => `
      <tr data-host="${r.host || ""}" data-path="${r.path || "/"}">
        <td>${r.display_path || r.path || "/"}</td>
        <td>${r.views}</td>
        <td>${r.udemy_clicks}</td>
        <td>${r.orders}</td>
        <td>$${(+r.net).toFixed(2)}</td>
        <td>${(+r.cr_pct).toFixed(2)}%</td>
      </tr>`
      )
      .join("");
  }

  async function loadCoupons() {
    const d = await fetchJSON("/api/metrics/coupons");
    const rows = d.rows || [];
    document.querySelector("#coupons tbody").innerHTML = rows
      .map(
        (r) => `
      <tr>
        <td>${r.coupon || "(none)"}</td>
        <td>${r.course_slug || "(unknown)"}</td>
        <td>${r.clicks}</td>
        <td>${r.orders}</td>
        <td>$${(+r.net).toFixed(2)}</td>
        <td>${(+r.cr_pct).toFixed(2)}%</td>
      </tr>`
      )
      .join("");
  }

  async function loadLocations() {
    const d = await fetchJSON("/api/metrics/locations");
    const rows = d.rows || [];
    document.querySelector("#locations tbody").innerHTML = rows
      .map(
        (r) => `
      <tr>
        <td>${r.country}</td>
        <td>${r.region}</td>
        <td>${r.visitors}</td>
        <td>${r.sessions}</td>
        <td>${r.views}</td>
      </tr>`
      )
      .join("");
  }

  async function loadXvaClicks() {
    const section = document.getElementById("xva");
    if (!section) return;
    let d;
    try {
      d = await fetchJSON("/api/metrics/xva_clicks");
    } catch (err) {
      section.style.display = "none";
      return;
    }
    const domain = d.domain || null;
    const summary = document.getElementById("xvaSummary");
    if (!domain) {
      section.style.display = "none";
      if (summary) summary.textContent = "";
      return;
    }
    section.style.display = "";
    const total = d.total_clicks || 0;
    const visitors = d.unique_visitors || 0;
    if (summary) {
      summary.textContent = total
        ? `${total} clicks to ${domain} from ${visitors} unique visitor${
            visitors === 1 ? "" : "s"
          }`
        : `No clicks to ${domain} in this range yet.`;
    }
    const pageRows = d.by_page || [];
    const pageBody = document.querySelector("#xvaByPage tbody");
    if (pageBody) {
      pageBody.innerHTML = pageRows.length
        ? pageRows
            .map(
              (r) => `
      <tr>
        <td>${r.path || "/"}</td>
        <td>${r.clicks}</td>
        <td>${r.visitors}</td>
      </tr>`
            )
            .join("")
        : emptyRow(3, "No tracked clicks yet");
    }
    const locRows = d.by_location || [];
    const locBody = document.querySelector("#xvaByLocation tbody");
    if (locBody) {
      locBody.innerHTML = locRows.length
        ? locRows
            .map(
              (r) => `
      <tr>
        <td>${r.country || "?"}</td>
        <td>${r.region || "?"}</td>
        <td>${r.clicks}</td>
      </tr>`
            )
            .join("")
        : emptyRow(3, "No location data yet");
    }
  }

  async function loadPageDetails(path, host) {
    let d;
    try {
      d = await fetchJSON("/api/metrics/page_details", {}, { path, host });
    } catch (err) {
      return;
    }
    const rows = d.rows || [];
    document.querySelector("#detailPath").textContent = host
      ? `https://${host}${path}`
      : path;
    document.querySelector("#detailTable tbody").innerHTML = rows
      .map(
        (r) => `
      <tr>
        <td>${r.ip || ""}</td>
        <td>${r.referrer || ""}</td>
        <td>${formatDate(r.ts)}</td>
        <td>${r.event_name}</td>
        <td>${r.app_id || ""}</td>
        <td>${r.path || ""}</td>
        <td>${
          r.page_url
            ? `<a href="${r.page_url}" target="_blank" rel="noopener">${r.page_url}</a>`
            : ""
        }</td>
        <td>${r.button_id || ""}</td>
        <td>${r.target_domain || ""}</td>
        <td>${
          r.href
            ? `<a href="${r.href}" target="_blank" rel="noopener">${r.href}</a>`
            : ""
        }</td>
        <td>${r.percent ?? ""}</td>
        <td>${r.geo_country || ""}</td>
        <td>${r.device || ""}</td>
        <td>${r.time_on_page_ms ?? ""}</td>
        <td>${r.uid}</td>
      </tr>`
      )
      .join("");
    document.getElementById("detailModal").classList.remove("hidden");
  }

  document.getElementById("detailClose").addEventListener("click", () => {
    document.getElementById("detailModal").classList.add("hidden");
  });

  document.getElementById("detailModal").addEventListener("click", (e) => {
    if (e.target.id === "detailModal") document.getElementById("detailModal").classList.add("hidden");
  });

  document.querySelector("#pages tbody").addEventListener("dblclick", (e) => {
    const tr = e.target.closest("tr");
    if (!tr) return;
    const path = tr.dataset.path || "/";
    const host = tr.dataset.host || "";
    loadPageDetails(path, host);
  });

  async function refreshAll() {
    await Promise.all([
      loadOpenClawSnapshot(),
      loadSummary(),
      loadPages(),
      loadCoupons(),
      loadLocations(),
      loadXvaClicks(),
    ]);
  }

  document.getElementById("refresh").addEventListener("click", refreshAll);

  const end = new Date();
  const start = new Date(end.getTime() - 7 * 24 * 3600 * 1000);
  document.getElementById("end").value = isoLocal(end);
  document.getElementById("start").value = isoLocal(start);

  document.getElementById("csv").addEventListener("change", async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    document.getElementById("importStatus").textContent = "Uploading...";
    const fd = new FormData();
    fd.append("file", f);
    try {
      const r = await fetch(API_BASE + "/api/import/udemy_csv", {
        method: "POST",
        body: fd,
      });
      const j = await r.json();
      document.getElementById("importStatus").textContent = `Imported ${j.inserted} rows`;
      await refreshAll();
    } catch (err) {
      document.getElementById("importStatus").textContent = "Import failed";
    } finally {
      document.getElementById("csv").value = "";
    }
  });

  refreshAll();
})();
