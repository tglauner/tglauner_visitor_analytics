const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../tracking/tracking.js'), 'utf8');

function browser(config = {}, host = '127.0.0.1') {
  const events = new Map();
  const sends = [];
  const cookies = [];
  const timers = [];
  const document = {
    title: 'Course', referrer: '',
    addEventListener: (name, handler) => events.set(name, handler),
    documentElement: { scrollHeight: 1000 }, body: { scrollHeight: 1000 },
  };
  Object.defineProperty(document, 'cookie', { get: () => '', set: value => cookies.push(value) });
  const context = {
    document, location: { hostname: host, origin: `http://${host}`, href: `http://${host}/course/`, pathname: '/course/', hash: '' },
    navigator: { doNotTrack: '0', sendBeacon: (url, payload) => { sends.push({url, payload: JSON.parse(payload)}); return true; } },
    history: { pushState() {} }, innerWidth: 800, innerHeight: 600, devicePixelRatio: 1,
    URL, Math, Date, JSON, console,
    addEventListener: (name, handler) => events.set(name, handler),
    setInterval: handler => timers.push(handler), setTimeout: handler => handler(),
    tgAnalyticsConfig: config,
  };
  context.window = context;
  vm.runInNewContext(source, context);
  return { context, sends, cookies, flush: () => timers.forEach(fn => fn()), consent: analytics => events.get('tg:analytics-consent')({detail: {analytics}}) };
}

const gated = browser({appId: 'frtb', requireConsent: true});
gated.flush();
assert.equal(gated.sends.length, 0);
assert.equal(gated.cookies.length, 0);
gated.consent(true);
gated.flush();
assert.equal(gated.sends.length, 1);
assert.equal(gated.sends[0].url, 'http://127.0.0.1:9000/collect');
assert.equal(gated.sends[0].payload.events[0].event_name, 'page_view');
assert.equal(gated.sends[0].payload.events[0].app_id, 'frtb');
gated.consent(true);
gated.flush();
assert.equal(gated.sends.length, 1, 'Repeated consent must not duplicate a page view');
gated.context.tgAnalytics.page();
gated.consent(false);
gated.flush();
assert.equal(gated.sends.length, 1, 'Revocation must discard queued events');
assert.ok(gated.cookies.some(c => c.startsWith('tg_uid=;')));
for (const value of [false, 'false', '0', 0]) {
  const disabled = browser({enabled: value, requireConsent: true});
  disabled.consent(true);
  disabled.flush();
  assert.equal(disabled.sends.length, 0);
}
const existing = browser({}, 'tglauner.com');
existing.flush();
assert.equal(existing.sends[0].url, '/collect');
vm.runInNewContext(source, existing.context);
existing.flush();
assert.equal(existing.sends.length, 1, 'Duplicate installation must not send twice');
console.log('Consent, revocation, boolean flags, collector routing, and duplicate installation passed.');
