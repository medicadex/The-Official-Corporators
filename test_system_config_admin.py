import urllib.request
import urllib.error
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8088/api"

def make_request(endpoint, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json", "Origin": "http://127.0.0.1:8088"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(f"{BASE_URL}{endpoint}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except Exception:
            return e.code, {"detail": err_body}

def test_system_config_admin():
    print("=" * 70)
    print("TESTING DYNAMIC SYSTEM CONSTANTS & STATUTORY CONFIG EDITING")
    print("=" * 70)

    # 1. Fetch config with format=full
    status, config_full = make_request("/config?format=full")
    assert status == 200, f"Expected 200 for full config, got {status}"
    items = config_full if isinstance(config_full, list) else config_full.get("data", [])
    print(f"✓ GET /api/config?format=full succeeded! Found {len(items)} statutory parameters:")
    for item in items:
        print(f"   - {item['config_key']:<24}: {item['config_value']} ({item.get('description', '')[:45]}...)")
    
    assert len(items) >= 10, "Expected at least 10 config parameters"

    # 2. Authenticate as Developer Super Admin
    status, login_res = make_request("/auth/login", method="POST", data={"identifier": "admin", "password": "Pass123*"})
    assert status == 200, f"Admin login failed: {login_res}"
    admin_token = login_res["token"]
    print(f"\n✓ Admin authenticated successfully. Permissions count: {len(login_res['user']['permissions'])}")

    # 3. Test Unauthorized Access (No Token)
    status, unauth_res = make_request("/admin/config/MONTHLY_DUE_DAY", method="PUT", data={"config_value": "28"})
    assert status == 401, f"Expected 401 for unauthenticated edit, got {status}: {unauth_res}"
    print(f"✓ Protected endpoint rejects unauthenticated requests (HTTP 401)")

    # 4. Test Valid Update of MONTHLY_DUE_DAY to 28
    status, update_res = make_request("/admin/config/MONTHLY_DUE_DAY", method="PUT", data={"config_value": "28"}, token=admin_token)
    assert status == 200, f"Expected 200 for updating MONTHLY_DUE_DAY, got {status}: {update_res}"
    print(f"✓ Successfully updated MONTHLY_DUE_DAY to 28. Status: {update_res['status']}")
    assert update_res["data"]["config_value"] == "28"

    # 5. Test Validation: Invalid MONTHLY_DUE_DAY (out of range: 45)
    status, invalid_day_res = make_request("/admin/config/MONTHLY_DUE_DAY", method="PUT", data={"config_value": "45"}, token=admin_token)
    assert status == 400, f"Expected 400 for invalid due day 45, got {status}: {invalid_day_res}"
    print(f"✓ Rejection verified for invalid due day 45 (HTTP 400): {invalid_day_res.get('detail')}")

    # 6. Test Invariant Protection: Attempting to change OFFICIAL_EMAIL to unauthorized email
    status, invalid_email_res = make_request("/admin/config/OFFICIAL_EMAIL", method="PUT", data={"config_value": "custom@example.com"}, token=admin_token)
    assert status == 400, f"Expected 400 for invariant violation, got {status}: {invalid_email_res}"
    print(f"✓ Invariant protected! Attempt to alter OFFICIAL_EMAIL was rejected (HTTP 400): {invalid_email_res.get('detail')}")

    # 7. Test Updating OFFICIAL_EMAIL with canonical address (wealthbridge.coopsociety@gmail.com)
    status, valid_email_res = make_request("/admin/config/OFFICIAL_EMAIL", method="PUT", data={"config_value": "wealthbridge.coopsociety@gmail.com"}, token=admin_token)
    assert status == 200, f"Expected 200 for canonical email, got {status}: {valid_email_res}"
    print(f"✓ Canonical email verification succeeded (HTTP 200)")

    # 8. Reset MONTHLY_DUE_DAY back to 28
    status, reset_res = make_request("/admin/config/MONTHLY_DUE_DAY", method="PUT", data={"config_value": "28"}, token=admin_token)
    assert status == 200, f"Failed to reset MONTHLY_DUE_DAY: {reset_res}"
    print(f"✓ Reset MONTHLY_DUE_DAY confirmed. Status: {reset_res['status']}")

    # 9. Verify format=full reflects updated state
    status, config_check = make_request("/config?format=full")
    check_items = config_check if isinstance(config_check, list) else config_check.get("data", [])
    day_item = next((i for i in check_items if i["config_key"] == "MONTHLY_DUE_DAY"), None)
    assert day_item and day_item["config_value"] == "28"
    print(f"✓ Verification confirmed via GET /api/config?format=full: MONTHLY_DUE_DAY = {day_item['config_value']}")

    print("\n" + "=" * 70)
    print("ALL SYSTEM CONFIG ADMIN TESTS PASSED PERFECTLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_system_config_admin()
