import httpx, json, sys

base = 'backend/data/demo'
files = [
    ('files', ('demo_app.log',       open(f'{base}/demo_app.log',       'rb'), 'text/plain')),
    ('files', ('demo_metrics.json',  open(f'{base}/demo_metrics.json',  'rb'), 'application/json')),
    ('files', ('demo_dashboard.png', open(f'{base}/demo_dashboard.png', 'rb'), 'image/png')),
]
r = httpx.post('http://localhost:8000/api/ingest', files=files, timeout=60)
print('Status:', r.status_code)
data = r.json()
print(json.dumps(data, indent=2))

errors = data.get('errors', [])
if errors:
    print('ERRORS:', errors)
    sys.exit(1)

assert r.status_code == 200
assert data['files_processed'] == 3
assert data['graph_nodes'] > 0
print()
print('PHASE 1 INGEST TEST: PASSED')
