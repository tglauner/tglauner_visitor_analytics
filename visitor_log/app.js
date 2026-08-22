(async function () {
  const $ = (q) => document.querySelector(q);
  const OPENCLAW_HOST = "openclaw.tglauner.com";
  let adminCredentials = sessionStorage.getItem("visitorAnalyticsAuth") || "";
  let siteWidgetsById = new Map();

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

  function escapeHTML(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function safeLink(value) {
    if (!value) return "";
    try {
      const url = new URL(value, location.origin);
      return ["http:", "https:", "mailto:", "tel:", "sms:"].includes(url.protocol)
        ? url.href
        : "";
    } catch (_error) {
      return "";
    }
  }

  function formatDuration(milliseconds) {
    const seconds = Math.round((Number(milliseconds) || 0) / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ${seconds % 60}s`;
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
    const headers = new Headers(opts.headers || {});
    if (adminCredentials) headers.set("Authorization", `Basic ${adminCredentials}`);
    const r = await fetch(API_BASE + withRange(path, extraParams), { ...opts, headers });
    if (r.status === 401) {
      const status = $("#authStatus");
      if (status) status.textContent = "Sign in with the configured admin credentials.";
    }
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  $("#signIn")?.addEventListener("click", () => {
    const username = $("#adminUser").value;
    const password = $("#adminPassword").value;
    adminCredentials = btoa(`${username}:${password}`);
    sessionStorage.setItem("visitorAnalyticsAuth", adminCredentials);
    $("#adminPassword").value = "";
    $("#authStatus").textContent = "Credentials saved for this browser tab.";
    $("#refresh").click();
  });

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

  async function loadSiteWidgets() {
    const grid = $("#siteWidgetGrid");
    const status = $("#siteWidgetStatus");
    try {
      const data = await fetchJSON("/api/sites");
      const widgets = data.widgets || [];
      siteWidgetsById = new Map(widgets.map((widget) => [widget.id, widget]));
      grid.innerHTML = widgets.length
        ? widgets
            .map(
              (widget) => `
        <button class="site-widget" type="button" data-site-id="${escapeHTML(widget.id)}" aria-label="Open details for ${escapeHTML(widget.label)}">
          <span class="site-widget-top">
            <span>
              <span class="site-widget-title">${escapeHTML(widget.label)}</span>
              <span class="site-widget-url">${escapeHTML(widget.url)}</span>
            </span>
            <span class="visitor-indicator ${widget.visitors ? "" : "is-zero"}" title="${widget.visitors} visitors">${widget.visitors}</span>
          </span>
          <span class="site-widget-metrics">
            <span><strong>${widget.page_views}</strong><br />page views</span>
            <span><strong>${widget.sessions}</strong><br />sessions</span>
            <span><strong>${widget.clicks}</strong><br />clicks</span>
          </span>
        </button>`
            )
            .join("")
        : '<p class="muted">No site widgets are configured.</p>';
      status.textContent = `${widgets.length} configured sites`;
    } catch (error) {
      grid.innerHTML = '<p class="muted">Site widgets could not be loaded.</p>';
      status.textContent = "Site data unavailable";
    }
  }

  function renderDetailRows(selector, rows, columns, emptyMessage) {
    const body = document.querySelector(`${selector} tbody`);
    body.innerHTML = rows.length
      ? rows
          .map(
            (row) =>
              `<tr>${columns.map((column) => `<td>${escapeHTML(column(row))}</td>`).join("")}</tr>`
          )
          .join("")
      : emptyRow(columns.length, emptyMessage);
  }

  async function openSiteWidget(widgetId) {
    const knownWidget = siteWidgetsById.get(widgetId);
    if (!knownWidget) return;
    const modal = $("#siteModal");
    modal.classList.remove("hidden");
    $("#siteModalTitle").textContent = knownWidget.label;
    $("#siteModalSource").textContent = `${knownWidget.source} widget`;
    $("#siteModalUrl").textContent = knownWidget.url;
    $("#siteModalUrl").href = knownWidget.url;
    $("#siteDetailStats").innerHTML = '<div class="detail-stat"><span>Status</span><strong>Loading…</strong></div>';
    try {
      const data = await fetchJSON(`/api/sites/${encodeURIComponent(widgetId)}`);
      const summary = data.summary;
      $("#siteDetailStats").innerHTML = [
        ["Visitors", summary.visitors],
        ["Sessions", summary.sessions],
        ["Page views", summary.page_views],
        ["Avg. time", formatDuration(summary.avg_time_on_page_ms)],
        ["Clicks", summary.clicks],
      ]
        .map(([label, value]) => `<div class="detail-stat"><span>${label}</span><strong>${value}</strong></div>`)
        .join("");
      renderDetailRows("#sitePagesTable", data.pages || [], [
        (row) => row.path,
        (row) => row.visitors,
        (row) => row.page_views,
        (row) => formatDuration(row.avg_time_on_page_ms),
        (row) => row.scroll_actions,
        (row) => row.click_actions,
      ], "No activity recorded for this site in the selected range.");
      renderDetailRows("#siteSourcesTable", data.sources || [], [
        (row) => row.referrer,
        (row) => row.visitors,
        (row) => row.sessions,
      ], "No visitor sources recorded.");
      renderDetailRows("#siteActionsTable", data.actions || [], [
        (row) => row.event_name.replaceAll("_", " "),
        (row) => row.count,
      ], "No actions recorded.");
      renderDetailRows("#siteScrollsTable", data.scrolls || [], [
        (row) => `${row.percent}%`,
        (row) => row.count,
      ], "No scroll activity recorded.");
      renderDetailRows("#siteClicksTable", data.clicks || [], [
        (row) => row.button_id,
        (row) => row.href,
        (row) => row.count,
      ], "No click activity recorded.");
    } catch (error) {
      $("#siteDetailStats").innerHTML = '<div class="detail-stat"><span>Status</span><strong>Unable to load details</strong></div>';
    }
  }

  $("#siteWidgetGrid")?.addEventListener("click", (event) => {
    const widget = event.target.closest("[data-site-id]");
    if (widget) openSiteWidget(widget.dataset.siteId);
  });

  $("#siteModalClose")?.addEventListener("click", () => $("#siteModal").classList.add("hidden"));
  $("#siteModal")?.addEventListener("click", (event) => {
    if (event.target.id === "siteModal") event.currentTarget.classList.add("hidden");
  });

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
        <td>${escapeHTML(r.path || "/")}</td>
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
        <td>${escapeHTML(r.button_id || r.href || "(unlabeled)")}</td>
        <td>${escapeHTML(inferCtaType(r))}</td>
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
      <tr data-host="${escapeHTML(r.host || "")}" data-path="${escapeHTML(r.path || "/")}">
        <td>${escapeHTML(r.display_path || r.path || "/")}</td>
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
        <td>${escapeHTML(r.coupon || "(none)")}</td>
        <td>${escapeHTML(r.course_slug || "(unknown)")}</td>
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
        <td>${escapeHTML(r.country)}</td>
        <td>${escapeHTML(r.region)}</td>
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
        <td>${escapeHTML(r.path || "/")}</td>
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
        <td>${escapeHTML(r.country || "?")}</td>
        <td>${escapeHTML(r.region || "?")}</td>
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
      .map((r) => {
        const pageUrl = safeLink(r.page_url);
        const targetUrl = safeLink(r.href);
        return `
      <tr>
        <td>${escapeHTML(r.ip || "")}</td>
        <td>${escapeHTML(r.referrer || "")}</td>
        <td>${escapeHTML(formatDate(r.ts))}</td>
        <td>${escapeHTML(r.event_name)}</td>
        <td>${escapeHTML(r.app_id || "")}</td>
        <td>${escapeHTML(r.path || "")}</td>
        <td>${
          pageUrl
            ? `<a href="${escapeHTML(pageUrl)}" target="_blank" rel="noopener">${escapeHTML(r.page_url)}</a>`
            : ""
        }</td>
        <td>${escapeHTML(r.button_id || "")}</td>
        <td>${escapeHTML(r.target_domain || "")}</td>
        <td>${
          targetUrl
            ? `<a href="${escapeHTML(targetUrl)}" target="_blank" rel="noopener">${escapeHTML(r.href)}</a>`
            : ""
        }</td>
        <td>${escapeHTML(r.percent ?? "")}</td>
        <td>${escapeHTML(r.geo_country || "")}</td>
        <td>${escapeHTML(r.device || "")}</td>
        <td>${escapeHTML(r.time_on_page_ms ?? "")}</td>
        <td>${escapeHTML(r.uid)}</td>
      </tr>`;
      })
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
      loadSiteWidgets(),
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
      const j = await fetchJSON("/api/import/udemy_csv", {
        method: "POST",
        body: fd,
      });
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
