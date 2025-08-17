import csv, io, re, datetime

def _norm(s):
    return (s or '').strip().lower()

def parse_udemy_csv(bytes_data):
    text = bytes_data.decode('utf-8', errors='ignore')
    reader = csv.DictReader(io.StringIO(text))
    out = []
    for r in reader:
        keys = { _norm(k): k for k in r.keys() }
        def get(*names):
            for n in names:
                if _norm(n) in keys: return r[keys[_norm(n)]].strip()
            for k in r.keys():
                if _norm(n) in _norm(k): return r[k].strip()
            return ''
        order_id = get('Order ID','Order','ID')
        dt_raw   = get('Purchase Date','Time','Order Date','Date')
        course   = get('Course','Course Title','Course Name')
        coupon   = get('Coupon Code','Coupon','Promotion Code')
        currency = get('Currency')
        gross    = get('Gross Amount','Gross','Amount')
        net      = get('Net Amount (Instructor Share)','Instructor Share','Net')
        iso = None
        for fmt in ('%Y-%m-%d %H:%M:%S','%Y-%m-%dT%H:%M:%S','%Y-%m-%d','%m/%d/%Y %H:%M','%m/%d/%Y'):
            try:
                iso = datetime.datetime.strptime(dt_raw, fmt).isoformat(); break
            except Exception: pass
        if not iso: iso = datetime.datetime.utcnow().isoformat()
        s = (course or '').lower().strip()
        s = re.sub(r'[^a-z0-9]+','-', s).strip('-')
        def f(x):
            x = (x or '').replace(',','').replace('$','').strip()
            try: return float(x)
            except: return 0.0
        out.append((order_id, iso, s, coupon or '', currency or '', f(gross), f(net)))
    return out
