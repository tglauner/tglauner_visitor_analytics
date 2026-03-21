(function registerAppTracking(APP_ID, COLLECTOR_URL, CORE_SCRIPT_URL) {
  if (typeof window === "undefined") return;
  const existing = window.tgAnalyticsConfig || {};
  const nextConfig = Object.assign({}, existing, {
    appId: APP_ID,
    collector: COLLECTOR_URL,
  });
  window.tgAnalyticsConfig = nextConfig;
  window.__tgAnalyticsAppId__ = APP_ID;
  window.__tgAnalyticsCollector__ = COLLECTOR_URL;
  if (window.tgAnalytics) {
    if (typeof window.tgAnalytics.setAppId === "function") {
      window.tgAnalytics.setAppId(APP_ID);
    }
    if (typeof window.tgAnalytics.setCollector === "function") {
      window.tgAnalytics.setCollector(COLLECTOR_URL);
    }
  }
  if (!document.querySelector('script[data-tg-analytics-core]')) {
    const script = document.createElement("script");
    script.src = CORE_SCRIPT_URL;
    script.dataset.tgAnalyticsCore = "1";
    document.head.appendChild(script);
  }
})(
  "openclaw_private_setup",
  "https://tglauner.com/collect",
  "https://tglauner.com/visitor_analytics/tracking/tracking.js",
);
