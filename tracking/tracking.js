(function () {
  if (typeof window === "undefined") return;
  if (navigator.doNotTrack === "1") return;
  if (window.__tg_analytics_loaded__) return;
  window.__tg_analytics_loaded__ = true;
  const C = {
    collector:
      location.hostname === "localhost" || location.hostname.startsWith("127.")
        ? "http://127.0.0.1:9000/collect"
        : "/collect",
    batchSize: 20,
    flushMs: 5000,
    sessionTimeout: 1800000,
    sampleRate: 1.0,
    appId: null,
  };
  function u() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
      /[xy]/g,
      function (c) {
        const r = (Math.random() * 16) | 0,
          v = c === "x" ? r : (r & 0x3) | 0x8;
        return v.toString(16);
      },
    );
  }
  function rc(n) {
    const m = document.cookie.match(new RegExp("(^| )" + n + "=([^;]+)"));
    return m ? decodeURIComponent(m[2]) : null;
  }
  function sc(n, v, d) {
    const e = new Date(Date.now() + d * 864e5).toUTCString();
    document.cookie = `${n}=${encodeURIComponent(v)}; Expires=${e}; Path=/; SameSite=Lax`;
  }
  function uid() {
    let x = rc("tg_uid");
    if (!x) {
      x = u();
      sc("tg_uid", x, 365);
    }
    return x;
  }
  let last = Date.now();
  let pageStart = Date.now();
  function sid() {
    let s = rc("tg_sid");
    const n = Date.now();
    if (!s || n - last > C.sessionTimeout) {
      s = u();
      sc("tg_sid", s, 1);
    }
    last = n;
    return s;
  }
  function utms(url) {
    try {
      const uo = new URL(url, location.origin),
        p = uo.searchParams;
      return {
        utm_source: p.get("utm_source"),
        utm_medium: p.get("utm_medium"),
        utm_campaign: p.get("utm_campaign"),
      };
    } catch (e) {
      return {};
    }
  }
  function normalizeDomain(value) {
    if (!value) return null;
    try {
      const text = value.toString().trim();
      if (!text) return null;
      const url = new URL(text.includes("://") ? text : `https://${text}`);
      return (url.hostname || "").replace(/^www\./, "").toLowerCase();
    } catch (e) {
      return value.toString().trim().replace(/^www\./, "").toLowerCase();
    }
  }

  function cleanAppId(value) {
    if (value === null || typeof value === "undefined") return null;
    try {
      const text = String(value).trim();
      return text ? text : null;
    } catch (err) {
      return null;
    }
  }

  let rawXva;
  if (typeof window.__tgXvaDomain__ !== "undefined") {
    rawXva = window.__tgXvaDomain__;
  } else if (
    window.tgAnalyticsConfig &&
    Object.prototype.hasOwnProperty.call(window.tgAnalyticsConfig, "xvaDomain")
  ) {
    rawXva = window.tgAnalyticsConfig.xvaDomain;
  }
  const DEFAULT_XVA = "course-xva-essentials.tglauner.com";
  const XVA_DOMAIN = normalizeDomain(
    rawXva === undefined ? DEFAULT_XVA : rawXva,
  );

  let rawAppId = null;
  if (typeof window.__tgAnalyticsAppId__ !== "undefined") {
    rawAppId = window.__tgAnalyticsAppId__;
  } else if (
    window.tgAnalyticsConfig &&
    Object.prototype.hasOwnProperty.call(window.tgAnalyticsConfig, "appId")
  ) {
    rawAppId = window.tgAnalyticsConfig.appId;
  }
  C.appId = cleanAppId(rawAppId);

  function parseTrackedLink(h) {
    try {
      const uo = new URL(h, location.origin);
      const host = (uo.hostname || "").toLowerCase();
      const normalized = host.replace(/^www\./, "");
      if (/udemy\.com$/.test(normalized)) {
        const m = uo.pathname.match(/\/course\/([^\/]+)\//);
        const cs = m ? m[1] : null;
        const cpn =
          uo.searchParams.get("couponCode") ||
          uo.searchParams.get("coupon") ||
          null;
        return { course_slug: cs, coupon: cpn, target_domain: normalized };
      }
      if (XVA_DOMAIN && normalized === XVA_DOMAIN) {
        return { target_domain: normalized };
      }
    } catch (e) {}
    return null;
  }
  const Q = [];
  function en(ev) {
    if (Math.random() > C.sampleRate) return;
    ev.ts = new Date().toISOString();
    ev.uid = uid();
    ev.session_id = sid();
    ev.viewport = { w: innerWidth, h: innerHeight, dpr: devicePixelRatio || 1 };
    if (C.appId) {
      ev.app_id = C.appId;
    }
    Q.push(ev);
    if (Q.length >= C.batchSize) fl();
  }
  async function fl() {
    if (!Q.length) return;
    const b = Q.splice(0, Q.length);
    try {
      if (navigator.sendBeacon) {
        const blob = new Blob([JSON.stringify({ events: b })], {
          type: "application/json",
        });
        navigator.sendBeacon(C.collector, blob);
      } else {
        await fetch(C.collector, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ events: b }),
          keepalive: true,
        });
      }
    } catch (e) {}
  }
  setInterval(fl, C.flushMs);
  addEventListener("beforeunload", fl);
  function pg() {
    pageStart = Date.now();
    en({
      event_name: "page_view",
      path: location.pathname,
      title: document.title,
      referrer: document.referrer || null,
      ...utms(location.href),
    });
  }
  pg();
  const _ps = history.pushState;
  history.pushState = function () {
    _ps.apply(this, arguments);
    setTimeout(pg, 0);
  };
  addEventListener("popstate", pg);
  let maxPct = 0;
  addEventListener(
    "scroll",
    () => {
      const st = scrollY || document.documentElement.scrollTop;
      const dh = Math.max(
        document.body.scrollHeight,
        document.documentElement.scrollHeight,
      );
      const pct = Math.round(((st + innerHeight) / dh) * 100);
      if (pct > maxPct) {
        [25, 50, 75, 100].forEach((t) => {
          if (maxPct < t && pct >= t)
            en({ event_name: "scroll", path: location.pathname, percent: t });
        });
        maxPct = pct;
      }
    },
    { passive: true },
  );
  addEventListener(
    "click",
    (e) => {
      const a = e.target.closest && e.target.closest("a[href]");
      if (!a) return;
      const out = parseTrackedLink(a.href);
      if (!out) return;
      const id =
        a.getAttribute("data-button-id") ||
        a.id ||
        a.textContent.trim().slice(0, 40);
      en({
        event_name: "outbound_click",
        path: location.pathname,
        href: a.href,
        target_domain: out.target_domain || null,
        button_id: id,
        course_slug: out.course_slug,
        coupon: out.coupon,
        ...utms(a.href),
      });
    },
    true,
  );
  addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      en({
        event_name: "page_unload",
        path: location.pathname,
        time_on_page_ms: Date.now() - pageStart,
      });
      fl();
    }
  });
  window.tgAnalytics = {
    page: pg,
    setSampleRate: (p) => (C.sampleRate = p),
    setAppId: (id) => {
      C.appId = cleanAppId(id);
    },
  };
})();
