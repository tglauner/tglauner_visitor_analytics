(function registerAppTracking(APP_ID) {
  if (typeof window === "undefined") return;
  const existing = window.tgAnalyticsConfig || {};
  const nextConfig = Object.assign({}, existing, { appId: APP_ID });
  window.tgAnalyticsConfig = nextConfig;
  window.__tgAnalyticsAppId__ = APP_ID;
  if (window.tgAnalytics && typeof window.tgAnalytics.setAppId === "function") {
    window.tgAnalytics.setAppId(APP_ID);
  }
  if (!document.querySelector('script[data-tg-analytics-core]')) {
    const script = document.createElement("script");
    script.src = "/visitor_analytics/tracking/tracking.js";
    script.dataset.tgAnalyticsCore = "1";
    document.head.appendChild(script);
  }
})("ai_value_advisor");
