import os, json, sqlite3, threading, datetime
from urllib.parse import urlparse
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from user_agents import parse as ua_parse

from dotenv import load_dotenv
load_dotenv()

from collector.reporting_filters import ReportingFilterLoader

GEO_READER = None
try:
    from geoip2.database import Reader as GeoReader
except Exception:
    GeoReader = None

DB_URL = os.getenv('DATABASE_URL','sqlite:////var/lib/visitor_log/analytics.sqlite3')
DB_PATH = DB_URL.replace('sqlite:////','/') if DB_URL.startswith('sqlite:////') else DB_URL.replace('sqlite:///','/')
ALLOWED_ORIGINS = [h.strip().lower() for h in os.getenv('ALLOWED_ORIGINS','tglauner.com,localhost,127.0.0.1').split(',')]
MAXMIND_DB = os.getenv('MAXMIND_DB','/opt/visitor_log/geo/GeoLite2-City.mmdb')
REPORTING_FILTERS_PATH = os.getenv(
    'REPORTING_FILTERS_PATH',
    os.path.join(os.path.dirname(__file__), 'config', 'reporting_filters.json'),
)


_filters = ReportingFilterLoader(REPORTING_FILTERS_PATH)


def excluded_ips() -> List[str]:
    return _filters.excluded_ips()


def ip_filter_clause(column: str = 'ip'):
    return _filters.sql_fragment(column)
def normalize_domain(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        text = value.strip()
        if not text:
            return None
        parsed = urlparse(text if '://' in text else f'//{text}', allow_fragments=False)
        host = parsed.hostname or parsed.path or ''
        if '/' in host:
            host = host.split('/')[0]
        host = host.strip().lower()
        return host or None
    except Exception:
        return None


def props_host_from_json(props_json: Optional[str]) -> str:
    if not props_json:
        return ''
    try:
        payload = json.loads(props_json)
    except Exception:
        return ''
    domain = payload.get('target_domain')
    if domain:
        normalized = normalize_domain(domain)
        if normalized:
            return normalized
    href = payload.get('href')
    normalized = normalize_domain(href)
    return normalized or ''


XVA_DOMAIN = normalize_domain(os.getenv('XVA_TARGET_DOMAIN', 'course-xva-essentials.tglauner.com'))
if GeoReader and os.path.exists(MAXMIND_DB):
    try: GEO_READER = GeoReader(MAXMIND_DB)
    except Exception: GEO_READER = None

conn = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
conn.row_factory = sqlite3.Row
conn.create_function('props_host', 1, props_host_from_json)
dblock = threading.Lock()
app = FastAPI(title='Visitor Analytics Collector', version='1.0.0')

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5174", "http://127.0.0.1:5174",
        "http://localhost", "http://127.0.0.1"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Event(BaseModel):
    ts: str; uid: str; session_id: str; event_name: str
    path: Optional[str] = None; title: Optional[str] = None; referrer: Optional[str] = None
    href: Optional[str] = None; target_domain: Optional[str] = None; button_id: Optional[str] = None; course_slug: Optional[str] = None; coupon: Optional[str] = None
    utm_source: Optional[str] = None; utm_medium: Optional[str] = None; utm_campaign: Optional[str] = None
    viewport: Optional[Dict[str, Any]] = None; percent: Optional[int] = None
    time_on_page_ms: Optional[int] = None; app_id: Optional[str] = None
class Batch(BaseModel):
    events: List[Event] = Field(default_factory=list)

def allowed_host(url: Optional[str]) -> bool:
    if not url: return False
    try:
        u = urlparse(url); host = (u.hostname or '').lower()
        if host in ('localhost','127.0.0.1'): return True
        for dom in ALLOWED_ORIGINS:
            if dom and (host == dom or host.endswith('.'+dom)):
                return True
    except Exception: pass
    return False

def get_ip(req: Request):
    xff = req.headers.get('x-forwarded-for')
    if xff: return xff.split(',')[0].strip()
    return req.client.host if req.client else None

def ip_to_geo(ip: str):
    if not GEO_READER: return (None,None)
    try:
        r = GEO_READER.city(ip); return (r.country.iso_code, (r.subdivisions.most_specific.name or '')[:48])
    except Exception: return (None,None)

def ua_to_device(ua_str: str):
    try:
        ua = ua_parse(ua_str or ''); device = 'mobile' if ua.is_mobile else 'tablet' if ua.is_tablet else 'pc'
        return device, ua.browser.family, ua.os.family
    except Exception: return None, None, None

def parse_range(start: Optional[str], end: Optional[str]):
    if not start or not end:
        end_dt = datetime.datetime.utcnow(); start_dt = end_dt - datetime.timedelta(days=7)
    else:
        end_dt = datetime.datetime.fromisoformat(end); start_dt = datetime.datetime.fromisoformat(start)
    return start_dt.isoformat(), end_dt.isoformat()

@app.post('/collect')
async def collect(req: Request, batch: Batch):
    origin = req.headers.get('origin',''); referer = req.headers.get('referer','')
    if not (allowed_host(origin) or allowed_host(referer)):
        raise HTTPException(status_code=403, detail='Forbidden origin')
    ip = get_ip(req); ua = req.headers.get('user-agent','')
    country, region = ip_to_geo(ip) if ip else (None,None)
    device, browser, osfam = ua_to_device(ua)
    rows = []
    for e in batch.events:
        rows.append((
            e.uid,
            e.session_id,
            e.ts,
            e.event_name,
            e.path,
            e.title,
            e.referrer,
            e.course_slug,
            e.coupon,
            e.button_id,
            e.utm_source,
            e.utm_medium,
            e.utm_campaign,
            ip,
            country,
            region,
            device,
            browser,
            osfam,
            json.dumps({
                'href': e.href,
                'viewport': e.viewport,
                'percent': e.percent,
                'target_domain': e.target_domain,
                'app_id': e.app_id,
            }),
            e.time_on_page_ms,
        ))
    with dblock:
        conn.executemany(
            'INSERT INTO events_raw (uid, session_id, ts, event_name, path, title, referrer, course_slug, coupon, button_id, utm_source, utm_medium, utm_campaign, ip, geo_country, geo_region, device, browser, os, props_json, time_on_page_ms) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            rows,
        )
    return JSONResponse({'ok': True, 'n': len(rows)})

@app.get('/healthz')
def healthz():
    return {'ok': True}

@app.get('/api/metrics/summary')
def metrics_summary(start: Optional[str] = None, end: Optional[str] = None):
    s, e = parse_range(start, end)
    cur = conn.cursor()
    clause, params = ip_filter_clause()
    cur.execute(
        f'SELECT COUNT(DISTINCT uid) AS v FROM events_raw WHERE ts BETWEEN ? AND ?{clause}',
        (s, e, *params),
    )
    visitors = cur.fetchone()['v'] or 0
    cur.execute(
        f'SELECT COUNT(DISTINCT session_id) AS s FROM events_raw WHERE ts BETWEEN ? AND ?{clause}',
        (s, e, *params),
    )
    sessions = cur.fetchone()['s'] or 0
    cur.execute(
        f"SELECT COUNT(*) AS pv FROM events_raw WHERE event_name='page_view' AND ts BETWEEN ? AND ?{clause}",
        (s, e, *params),
    )
    page_views = cur.fetchone()['pv'] or 0
    cur.execute(
        f"SELECT COUNT(*) AS oc FROM events_raw WHERE event_name='outbound_click' AND ts BETWEEN ? AND ?{clause}",
        (s, e, *params),
    )
    out_clicks = cur.fetchone()['oc'] or 0
    xva_clicks = None
    if XVA_DOMAIN:
        cur.execute(
            f"""
            SELECT COUNT(*) AS xc
            FROM events_raw
            WHERE event_name='outbound_click'
              AND ts BETWEEN ? AND ?
              {clause}
              AND props_host(props_json) = ?
            """,
            (s, e, *params, XVA_DOMAIN),
        )
        row = cur.fetchone()
        xva_clicks = int(row['xc'] or 0) if row else 0
    cur.execute('SELECT COUNT(*) AS orders, COALESCE(SUM(net),0) AS net FROM udemy_orders WHERE order_ts BETWEEN ? AND ?', (s,e)); row = cur.fetchone(); orders=row['orders'] or 0; net=row['net'] or 0.0
    cr = (orders/out_clicks*100.0) if out_clicks else 0.0
    return {'range':{'start':s,'end':e},'visitors':visitors,'sessions':sessions,'page_views':page_views,'outbound_clicks':out_clicks,'xva_clicks':xva_clicks,'xva_domain':XVA_DOMAIN,'orders':orders,'net_revenue':round(net,2),'click_to_order_cr_pct':round(cr,2)}

@app.get('/api/metrics/coupons')
def metrics_coupons(start: Optional[str] = None, end: Optional[str] = None):
    s, e = parse_range(start, end)
    cur = conn.cursor()
    clause, params = ip_filter_clause()
    cur.execute(
        f"SELECT COALESCE(coupon,'') AS coupon, COALESCE(course_slug,'') AS course_slug, COUNT(*) AS clicks FROM events_raw WHERE event_name='outbound_click' AND ts BETWEEN ? AND ?{clause} GROUP BY coupon, course_slug",
        (s, e, *params),
    )
    clicks = {(r['coupon'], r['course_slug']): r['clicks'] for r in cur.fetchall()}
    cur.execute("SELECT COALESCE(coupon,'') AS coupon, COALESCE(course_slug,'') AS course_slug, COUNT(*) AS orders, COALESCE(SUM(net),0) AS net FROM udemy_orders WHERE order_ts BETWEEN ? AND ? GROUP BY coupon, course_slug", (s,e))
    out_rows = []; seen=set()
    for r in cur.fetchall():
        key=(r['coupon'], r['course_slug']); seen.add(key); cks=clicks.get(key,0); cr=(r['orders']/cks*100.0) if cks else 0.0
        out_rows.append({'coupon':r['coupon'],'course_slug':r['course_slug'],'clicks':cks,'orders':r['orders'],'net':round(r['net'] or 0.0,2),'cr_pct':round(cr,2)})
    for key,cks in clicks.items():
        if key not in seen: out_rows.append({'coupon':key[0],'course_slug':key[1],'clicks':cks,'orders':0,'net':0.0,'cr_pct':0.0})
    return {'range':{'start':s,'end':e},'rows':out_rows}

@app.get('/api/metrics/top_pages')
def metrics_top_pages(start: Optional[str] = None, end: Optional[str] = None, limit: int = 50):
    s, e = parse_range(start, end)
    cur = conn.cursor()
    clause, params = ip_filter_clause()
    cur.execute(
        f"SELECT path, COUNT(*) AS views FROM events_raw WHERE event_name='page_view' AND ts BETWEEN ? AND ?{clause} GROUP BY path ORDER BY views DESC LIMIT ?",
        (s, e, *params, limit),
    )
    page_rows = cur.fetchall(); paths = [r['path'] for r in page_rows if r['path'] is not None]
    if not paths: return {'range':{'start':s,'end':e},'rows':[]}
    placeholders = ','.join(['?']*len(paths))
    cur.execute(
        f"SELECT path, COUNT(*) AS clicks FROM events_raw WHERE event_name='outbound_click' AND ts BETWEEN ? AND ?{clause} AND path IN ({placeholders}) GROUP BY path",
        (s, e, *params, *paths),
    )
    clicks_by_path = {r['path']: r['clicks'] for r in cur.fetchall()}
    cur.execute(
        f"SELECT id, ts, path, coupon, course_slug FROM events_raw WHERE event_name='outbound_click' AND ts BETWEEN ? AND ?{clause} ORDER BY coupon, course_slug, ts",
        (s, e, *params),
    )
    clicks = [dict(r) for r in cur.fetchall()]
    from collections import defaultdict; by_key=defaultdict(list)
    for c in clicks: by_key[((c.get('coupon') or ''),(c.get('course_slug') or ''))].append(c)
    cur.execute("SELECT order_id, order_ts, coupon, course_slug, net FROM udemy_orders WHERE order_ts BETWEEN ? AND ? ORDER BY order_ts", (s,e))
    orders=[dict(r) for r in cur.fetchall()]
    def iso(dt):
        try: return datetime.datetime.fromisoformat(dt)
        except: return datetime.datetime.min
    orders_by_path = {}
    import bisect
    for o in orders:
        key=((o.get('coupon') or ''),(o.get('course_slug') or ''))
        seq = by_key.get(key,[])
        if not seq: continue
        times=[iso(c['ts']) for c in seq]; t=iso(o['order_ts']); idx=bisect.bisect_right(times,t)-1
        if idx>=0:
            path=seq[idx]['path']
            if path not in orders_by_path: orders_by_path[path]={'orders':0,'net':0.0}
            orders_by_path[path]['orders']+=1; orders_by_path[path]['net']+=float(o.get('net') or 0.0)
    rows=[]
    for r in page_rows:
        p=r['path'] or '/'; v=r['views']; cks=clicks_by_path.get(p,0); o=orders_by_path.get(p,{'orders':0,'net':0.0}); cr=(o['orders']/cks*100.0) if cks else 0.0
        rows.append({'path':p,'views':v,'udemy_clicks':cks,'orders':o['orders'],'net':round(o['net'],2),'cr_pct':round(cr,2)})
    return {'range':{'start':s,'end':e},'rows':rows}

@app.get('/api/metrics/page_details')
def metrics_page_details(path: str, start: Optional[str] = None, end: Optional[str] = None):
    s, e = parse_range(start, end)
    cur = conn.cursor()
    clause, params = ip_filter_clause()
    cur.execute(
        f"SELECT uid, ip, ts, event_name, path, referrer, button_id, geo_country, device, time_on_page_ms, props_json FROM events_raw WHERE path = ? AND ts BETWEEN ? AND ?{clause} ORDER BY ts DESC",
        (path, s, e, *params),
    )
    rows = []
    for r in cur.fetchall():
        d = dict(r)
        props = json.loads(d.get('props_json') or '{}')
        d['percent'] = props.get('percent')
        d['href'] = props.get('href')
        d['target_domain'] = props.get('target_domain')
        d['app_id'] = props.get('app_id')
        d.pop('props_json', None)
        rows.append(d)
    return {'range': {'start': s, 'end': e}, 'path': path, 'rows': rows}

@app.get('/api/metrics/locations')
def metrics_locations(start: Optional[str] = None, end: Optional[str] = None):
    s, e = parse_range(start, end)
    cur = conn.cursor()
    clause, params = ip_filter_clause()
    cur.execute(
        f"SELECT COALESCE(geo_country,'?') AS country, COALESCE(geo_region,'?') AS region, COUNT(DISTINCT uid) AS visitors, COUNT(DISTINCT session_id) AS sessions, SUM(CASE WHEN event_name='page_view' THEN 1 ELSE 0 END) AS views FROM events_raw WHERE ts BETWEEN ? AND ?{clause} GROUP BY country, region ORDER BY visitors DESC",
        (s, e, *params),
    )
    rows=[dict(r) for r in cur.fetchall()]
    return {'range':{'start':s,'end':e},'rows':rows}

def _domain_click_metrics(domain: str, start: str, end: str):
    cur = conn.cursor()
    clause, ip_params = ip_filter_clause()
    params = (start, end, *ip_params, domain)
    cur.execute(
        f"""
        SELECT COUNT(*) AS clicks, COUNT(DISTINCT uid) AS visitors
        FROM events_raw
        WHERE event_name='outbound_click'
          AND ts BETWEEN ? AND ?{clause}
          AND props_host(props_json) = ?
        """,
        params,
    )
    totals = dict(cur.fetchone() or {})
    cur.execute(
        f"""
        SELECT COALESCE(path,'/') AS path,
               COUNT(*) AS clicks,
               COUNT(DISTINCT uid) AS visitors
        FROM events_raw
        WHERE event_name='outbound_click'
          AND ts BETWEEN ? AND ?{clause}
          AND props_host(props_json) = ?
        GROUP BY path
        ORDER BY clicks DESC
        """,
        params,
    )
    by_page = [dict(r) for r in cur.fetchall()]
    cur.execute(
        f"""
        SELECT COALESCE(geo_country,'?') AS country,
               COALESCE(geo_region,'?') AS region,
               COUNT(*) AS clicks
        FROM events_raw
        WHERE event_name='outbound_click'
          AND ts BETWEEN ? AND ?{clause}
          AND props_host(props_json) = ?
        GROUP BY geo_country, geo_region
        ORDER BY clicks DESC
        """,
        params,
    )
    by_location = [dict(r) for r in cur.fetchall()]
    return {
        'total_clicks': int(totals.get('clicks', 0) or 0),
        'unique_visitors': int(totals.get('visitors', 0) or 0),
        'by_page': by_page,
        'by_location': by_location,
    }


@app.get('/api/metrics/xva_clicks')
def metrics_xva_clicks(start: Optional[str] = None, end: Optional[str] = None, domain: Optional[str] = None):
    s, e = parse_range(start, end)
    target = normalize_domain(domain) if domain is not None else XVA_DOMAIN
    if not target:
        return {
            'range': {'start': s, 'end': e},
            'domain': None,
            'total_clicks': 0,
            'unique_visitors': 0,
            'by_page': [],
            'by_location': [],
        }
    metrics = _domain_click_metrics(target, s, e)
    return {
        'range': {'start': s, 'end': e},
        'domain': target,
        **metrics,
    }

try:
    from collector.importer.udemy_csv_importer import parse_udemy_csv
    _UDEMY_IMPORT_ERROR = None
except Exception as exc:
    parse_udemy_csv = None
    _UDEMY_IMPORT_ERROR = str(exc)
@app.post('/api/import/udemy_csv')
async def import_udemy_csv(file: UploadFile = File(...)):
    if not parse_udemy_csv:
        raise HTTPException(
            status_code=503,
            detail=f'Udemy CSV importer unavailable: {_UDEMY_IMPORT_ERROR or "unknown error"}',
        )
    data = await file.read(); rows = parse_udemy_csv(data); n=0
    with dblock:
        for (order_id, order_ts, course_slug, coupon, currency, gross, net) in rows:
            try:
                conn.execute('INSERT OR IGNORE INTO udemy_orders(order_id, order_ts, course_slug, coupon, currency, gross, net) VALUES (?,?,?,?,?,?,?)',(order_id, order_ts, course_slug, coupon, currency, gross, net)); n+=1
            except Exception: pass
    return {'ok': True, 'inserted': n}
