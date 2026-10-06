(async function () {
  const $ = (q) => document.querySelector(q);
  let adminCredentials = sessionStorage.getItem("visitorAnalyticsAuth") || "";
  let siteWidgetsById = new Map();
  let agentsById = new Map();

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
    if (r.status === 204) return null;
    return r.json();
  }

  function readableError(error) {
    try {
      const parsed = JSON.parse(error.message);
      return parsed.detail || "The request could not be completed.";
    } catch (_parseError) {
      return error.message || "The request could not be completed.";
    }
  }

  function relativeTime(value) {
    if (!value) return "No status received";
    const timestamp = new Date(value);
    if (Number.isNaN(timestamp.getTime())) return "Unknown update time";
    const seconds = Math.max(0, Math.round((Date.now() - timestamp.getTime()) / 1000));
    if (seconds < 60) return "Updated just now";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `Updated ${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `Updated ${hours}h ago`;
    return `Updated ${Math.floor(hours / 24)}d ago`;
  }

  const agentStatusLabels = {
    working: "Working",
    success: "Success",
    failure: "Failure",
    needs_work: "Needs work",
  };

  function renderAgentSummary(counts = {}) {
    $("#agentStatusSummary").innerHTML = ["working", "success", "failure", "needs_work"]
      .map(
        (status) =>
          `<span class="agent-summary-pill status-${status}"><strong>${Number(counts[status] || 0)}</strong> ${agentStatusLabels[status]}</span>`
      )
      .join("");
  }

  function setAgentConnection(state) {
    const status = $("#agentConnectionStatus");
    const labels = {
      checking: "Checking",
      online: "Online",
      offline: "Offline / not set up",
    };
    status.className = `agent-connection-status is-${state}`;
    status.textContent = labels[state];
  }

  function renderAgents(agents) {
    const grid = $("#agentGrid");
    agentsById = new Map(agents.map((agent) => [agent.id, agent]));
    grid.innerHTML = agents.length
      ? agents
          .map((agent) => {
            const status = agent.display_status || "needs_work";
            return `
              <article class="agent-card status-${status}">
                <div class="agent-card-header">
                  <h3 title="${escapeHTML(agent.name)}">${escapeHTML(agent.name)}</h3>
                  <span class="agent-status-pill status-${status}">${agentStatusLabels[status]}</span>
                </div>
                <p class="agent-project-path" title="${escapeHTML(agent.project_path)}">${escapeHTML(agent.project_path)}</p>
                <p class="agent-message">${escapeHTML(agent.message || (status === "needs_work" ? "Ready for the next assignment." : "No status message provided."))}</p>
                <div class="agent-card-footer">
                  <span>${escapeHTML(relativeTime(agent.updated_at))}</span>
                  <span class="agent-card-actions">
                    <button class="agent-action edit" type="button" data-agent-action="edit" data-agent-id="${escapeHTML(agent.id)}" aria-label="Edit ${escapeHTML(agent.name)}">Edit</button>
                    <button class="agent-action delete" type="button" data-agent-action="delete" data-agent-id="${escapeHTML(agent.id)}" aria-label="Delete ${escapeHTML(agent.name)}">Delete</button>
                  </span>
                </div>
              </article>`;
          })
          .join("")
      : '<div class="agent-placeholder">No agents are registered. Use Add agent to create one.</div>';
  }

  async function loadAgents({ quiet = false } = {}) {
    const hadError = $("#agentFeedback").classList.contains("is-error");
    if (!quiet) {
      setAgentConnection("checking");
      $("#agentFeedback").classList.remove("is-error");
      $("#agentFeedback").textContent = "Refreshing agent status…";
    }
    try {
      const data = await fetchJSON("/api/agents");
      setAgentConnection("online");
      $("#agentFeedback").classList.remove("is-error");
      renderAgentSummary(data.counts);
      renderAgents(data.agents || []);
      if (!quiet || hadError) $("#agentFeedback").textContent = `Watching ${data.agents.length} registered agents · refreshes every 15 seconds`;
    } catch (error) {
      setAgentConnection("offline");
      if (!agentsById.size) {
        $("#agentGrid").innerHTML = '<div class="agent-placeholder">Start local collector.</div>';
        renderAgentSummary();
      }
      $("#agentFeedback").classList.add("is-error");
      $("#agentFeedback").textContent = "Agent API unavailable";
    }
  }

  function openAgentForm(agent = null) {
    $("#agentModalTitle").textContent = agent ? "Edit agent" : "Add agent";
    $("#agentId").value = agent?.id || "";
    $("#agentName").value = agent?.name || "";
    $("#agentProjectPath").value = agent?.project_path || "";
    $("#agentFormError").textContent = "";
    $("#agentModal").classList.remove("hidden");
    $("#agentName").focus();
  }

  function closeAgentForm() {
    $("#agentModal").classList.add("hidden");
    $("#agentForm").reset();
    $("#agentId").value = "";
  }

  $("#agentAddButton").addEventListener("click", () => openAgentForm());
  $("#agentModalClose").addEventListener("click", closeAgentForm);
  $("#agentModal").addEventListener("click", (event) => {
    if (event.target.id === "agentModal") closeAgentForm();
  });

  $("#agentForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const agentId = $("#agentId").value;
    const saveButton = $("#agentSaveButton");
    const payload = {
      name: $("#agentName").value.trim(),
      project_path: $("#agentProjectPath").value.trim(),
    };
    saveButton.disabled = true;
    saveButton.textContent = "Saving…";
    $("#agentFormError").textContent = "";
    try {
      await fetchJSON(agentId ? `/api/agents/${encodeURIComponent(agentId)}` : "/api/agents", {
        method: agentId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      closeAgentForm();
      $("#agentFeedback").textContent = agentId ? "Agent updated." : "Agent added.";
      await loadAgents({ quiet: true });
    } catch (error) {
      $("#agentFormError").textContent = readableError(error);
    } finally {
      saveButton.disabled = false;
      saveButton.textContent = "Save agent";
    }
  });

  $("#agentGrid").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-agent-action]");
    if (!button) return;
    const agent = agentsById.get(button.dataset.agentId);
    if (!agent) return;
    if (button.dataset.agentAction === "edit") {
      openAgentForm(agent);
      return;
    }
    if (!window.confirm(`Delete ${agent.name}? Its stored status will also be removed.`)) return;
    button.disabled = true;
    try {
      await fetchJSON(`/api/agents/${encodeURIComponent(agent.id)}`, { method: "DELETE" });
      $("#agentFeedback").textContent = `${agent.name} deleted.`;
      await loadAgents({ quiet: true });
    } catch (error) {
      button.disabled = false;
      $("#agentFeedback").classList.add("is-error");
      $("#agentFeedback").textContent = readableError(error);
    }
  });

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
      loadAgents(),
      loadSiteWidgets(),
      loadSummary(),
      loadPages(),
    ]);
  }

  document.getElementById("refresh").addEventListener("click", refreshAll);

  const end = new Date();
  const start = new Date(end.getTime() - 7 * 24 * 3600 * 1000);
  document.getElementById("end").value = isoLocal(end);
  document.getElementById("start").value = isoLocal(start);

  refreshAll();
  window.setInterval(() => {
    if (!document.hidden) loadAgents({ quiet: true });
  }, 15000);
})();
