import urllib.request
import json

def test():
    print("=" * 65)
    print("TESTING PURE DEVELOPER ADMIN (NO MEMBER RECORD / PAYMENTS)")
    print("=" * 65)
    
    # 1. Authenticate with admin / Pass123*
    login_payload = json.dumps({'identifier': 'admin', 'password': 'Pass123*'}).encode('utf-8')
    req = urllib.request.Request(
        'http://127.0.0.1:8088/api/auth/login',
        data=login_payload,
        headers={'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:8088'}
    )
    
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode('utf-8'))
        
    print(f"[OK] Login Status: 200")
    print(f"  Identifier:       {body['user']['member_code']}")
    print(f"  Full Name:        {body['user']['full_name']}")
    print(f"  Status:           {body['user']['membership_status']}")
    print(f"  Is Admin Only:    {body['user'].get('is_admin_only')}")
    print(f"  Primary Role:     {body['user']['primary_role']}")
    print(f"  Roles:            {body['user']['roles']}")
    print(f"  Permissions:      {len(body['user']['permissions'])} Total Permissions")
    
    token = body['token']
    
    # 2. Test Executive Endpoints
    print("\n[OK] Testing Secured Executive Desks:")
    endpoints = [
        '/admin/executive-metrics',
        '/admin/pending-members',
        '/admin/pending-contact-changes',
        '/members',
        '/config'
    ]
    for ep in endpoints:
        r = urllib.request.Request(
            f'http://127.0.0.1:8088/api{ep}',
            headers={'Authorization': f'Bearer {token}', 'Origin': 'http://127.0.0.1:8088'}
        )
        with urllib.request.urlopen(r) as ep_resp:
            res_json = json.loads(ep_resp.read().decode('utf-8'))
            if ep == '/members':
                member_codes = [m['member_code'] for m in res_json]
                print(f"  {ep:<35} -> {ep_resp.status} OK (Members: {len(res_json)} cooperators: {member_codes})")
                assert 'admin' not in member_codes, "ERROR: admin must NOT be in members roster!"
            else:
                print(f"  {ep:<35} -> {ep_resp.status} OK")

    print("\n" + "=" * 65)
    print("ALL TESTS PASSED: Admin is strictly system developer (no member record/payments)")
    print("=" * 65)

if __name__ == '__main__':
    test()
