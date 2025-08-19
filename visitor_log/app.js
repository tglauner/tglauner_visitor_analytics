(async function () {
  const $ = (q) => document.querySelector(q);

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

  function qs() {
    const start = $("#start").value
      ? new Date($("#start").value).toISOString()
      : "";
    const end = $("#end").value ? new Date($("#end").value).toISOString() : "";
    const p = new URLSearchParams();
    if (start) p.set("start", start);
    if (end) p.set("end", end);
    return p.toString() ? "?" + p.toString() : "";
  }

  async function fetchJSON(path, opts = {}) {
    const r = await fetch(API_BASE + path + qs(), opts);
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  }

  async function loadSummary() {
    const s = await fetchJSON("/api/metrics/summary");
    const tiles = [
      ["Visitors", s.visitors],
      ["Sessions", s.sessions],
      ["Page Views", s.page_views],
      ["Udemy Clicks", s.outbound_clicks],
      ["Orders", s.orders],
      ["Net Revenue", `$${(+s.net_revenue).toFixed(2)}`],
      ["CR %", `${(+s.click_to_order_cr_pct).toFixed(2)}%`],
    ];
    $("#tiles").innerHTML = tiles
      .map(
        ([l, v]) =>
          `<div class="tile"><div class="label">${l}</div><div class="value">${v}</div></div>`
      )
      .join("");
  }

  async function loadPages() {
    const d = await fetchJSON("/api/metrics/top_pages");
    const rows = d.rows || [];
    document.querySelector("#pages tbody").innerHTML = rows
      .map(
        (r) => `
      <tr>
        <td>${r.path || "/"}</td>
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

  async function loadPageDetails(path) {
    const q = qs();
    const url = `/api/metrics/page_details?path=${encodeURIComponent(path)}${q ? "&" + q.slice(1) : ""}`;
    const r = await fetch(API_BASE + url);
    if (!r.ok) return;
    const d = await r.json();
    const rows = d.rows || [];
    document.querySelector("#detailPath").textContent = path;
    document.querySelector("#detailTable tbody").innerHTML = rows
      .map(
        (r) => `
      <tr>
        <td>${r.uid}</td>
        <td>${r.ip || ""}</td>
        <td>${r.ts}</td>
        <td>${r.event_name}</td>
        <td>${r.path || ""}</td>
        <td>${r.referrer || ""}</td>
        <td>${r.button_id || ""}</td>
        <td>${r.percent ?? ""}</td>
        <td>${r.geo_country || ""}</td>
        <td>${r.device || ""}</td>
        <td>${r.time_on_page_ms ?? ""}</td>
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
    const path = tr.children[0].textContent;
    loadPageDetails(path);
  });

  async function refreshAll() {
    await Promise.all([loadSummary(), loadPages(), loadCoupons(), loadLocations()]);
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
