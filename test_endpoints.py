import sys
from app import app

client = app.test_client()

routes_to_test = [
    ('GET', '/', None),
    ('GET', '/dashboard', None),
    ('GET', '/brand-generator', None),
    ('GET', '/login', None),
    ('POST', '/api/brand-generate', {'keyword': 'Fintech'}),
    ('POST', '/api/chat', {'prompt': 'How do I validate my startup idea?'}),
    ('GET', '/api/conversations', None),
    ('POST', '/api/conversations', {'title': 'Test Chat'}),
    ('GET', '/api/images', None),
    ('POST', '/api/images/enhance-prompt', {'prompt': 'SaaS Dashboard', 'style': '3d-render'}),
    ('POST', '/api/search', {'query': 'venture capital funding trends'}),
    ('POST', '/api/social/generate', {'platform': 'linkedin', 'topic': 'Product Launch'}),
    ('GET', '/api/social/accounts', None),
    ('POST', '/api/startup/financials', {'sub_price': 49, 'target_users': 500}),
    ('GET', '/api/user/memories', None),
    ('GET', '/api/usage', None),
]

all_passed = True
for method, route, payload in routes_to_test:
    if method == 'GET':
        r = client.get(route)
    else:
        r = client.post(route, json=payload)
    status_ok = r.status_code in [200, 302]
    symbol = "PASS" if status_ok else "FAIL"
    print(f"[{method}] {route} -> Status: {r.status_code} [{symbol}]")
    if not status_ok:
        all_passed = False

# Test form submission to /generate
r_gen = client.post('/generate', data={'startup_name': 'CloudSync AI', 'idea_description': 'Autonomous multi-cloud cost optimizer'})
symbol_gen = "PASS" if r_gen.status_code == 200 else "FAIL"
print(f"[POST] /generate (Form) -> Status: {r_gen.status_code} [{symbol_gen}]")
if r_gen.status_code != 200:
    all_passed = False

if all_passed:
    print("\n>>> ALL FLASK ENDPOINTS VERIFIED & PASSING 100%! <<<")
else:
    sys.exit(1)
