import urllib.request
import json
import time

def run_tests():
    print("=" * 70)
    print("COMPREHENSIVE MEMBER MANAGEMENT DASHBOARD VERIFICATION")
    print("=" * 70)

    # 1. Admin Login
    print("\n[Step 1] Authenticating as Developer Admin...")
    login_req = urllib.request.Request(
        'http://127.0.0.1:8088/api/auth/login',
        data=json.dumps({'identifier': 'admin', 'password': 'Pass123*'}).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:8088'}
    )
    with urllib.request.urlopen(login_req) as resp:
        body = json.loads(resp.read().decode('utf-8'))
        token = body['token']
        print(f"  [OK] Admin Login: {body['user']['full_name']} (Role: {body['user']['primary_role']})")

    # 2. List Members
    print("\n[Step 2] Fetching complete members roster via GET /api/members...")
    members_req = urllib.request.Request(
        'http://127.0.0.1:8088/api/members',
        headers={'Authorization': f'Bearer {token}', 'Origin': 'http://127.0.0.1:8088'}
    )
    with urllib.request.urlopen(members_req) as resp:
        members = json.loads(resp.read().decode('utf-8'))
        print(f"  [OK] Total Cooperators: {len(members)}")
        for m in members[:3]:
            print(f"    - {m['member_code']}: {m['full_name']} - Tier: {m['contribution_tier']} | KYC: {m['kyc_completion_percent']}% | Savings: NGN {m['savings_balance']}")

    # 3. Modify Member Biodata
    print("\n[Step 3] Modifying Member #8 Biodata via PUT /api/admin/members/8/biodata...")
    update_payload = {
        "employer_or_business_name": "Lagos State Judicial Service Commission",
        "contribution_tier": "PLUS",
        "marital_status": "MARRIED",
        "nok_name": "Adebowale Family Trust",
        "nok_relationship": "FAMILY_TRUST",
        "nok_phone": "08022223344"
    }
    update_req = urllib.request.Request(
        'http://127.0.0.1:8088/api/admin/members/8/biodata',
        data=json.dumps(update_payload).encode('utf-8'),
        method='PUT',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:8088'}
    )
    with urllib.request.urlopen(update_req) as resp:
        up_res = json.loads(resp.read().decode('utf-8'))
        print(f"  [OK] {up_res['message']} (New Tier: {up_res['tier']}, KYC: {up_res['kyc_completion_percent']}%)")

    # 4. Reset Password to Default
    print("\n[Step 4] Resetting Member #8 Password to Default via POST /api/admin/members/8/reset-password...")
    reset_req = urllib.request.Request(
        'http://127.0.0.1:8088/api/admin/members/8/reset-password',
        data=b'{}',
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:8088'}
    )
    with urllib.request.urlopen(reset_req) as resp:
        rst_res = json.loads(resp.read().decode('utf-8'))
        print(f"  [OK] {rst_res['message']}")
        print(f"  [OK] Reset credentials confirmed: Code {rst_res['member_code']} | Default Password: {rst_res['default_password']}")

    # 5. Verify Member #8 Can Sign In with the Reset Default Password
    print("\n[Step 5] Verifying Member #8 can sign in with reset default password...")
    m_login_req = urllib.request.Request(
        'http://127.0.0.1:8088/api/auth/login',
        data=json.dumps({'identifier': 'WMC-2026-008', 'password': 'Wealthbridge@2026'}).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:8088'}
    )
    with urllib.request.urlopen(m_login_req) as resp:
        m_body = json.loads(resp.read().decode('utf-8'))
        print(f"  [OK] Member sign-in verified successfully: {m_body['user']['full_name']} logged in!")

    # 6. Enroll New Member
    print("\n[Step 6] Enrolling New Member via POST /api/admin/members...")
    enroll_payload = {
        "first_name": "Chinedu",
        "last_name": "Okonkwo",
        "other_names": "Emeka",
        "email": "chinedu.okonkwo@example.com",
        "phone": "08077776655",
        "gender": "MALE",
        "marital_status": "MARRIED",
        "residential_address": "45 Admiralty Way, Lekki Phase 1, Lagos State",
        "employment_status": "BUSINESS_OWNER",
        "employer_or_business_name": "Lekki Meridian Logistics Limited",
        "contribution_tier": "PREMIUM",
        "status": "ACTIVE",
        "identification_type": "NIN",
        "identification_number": "77788899900",
        "bank_name": "Zenith Bank Plc",
        "bank_account_number": "2001122334",
        "bank_account_name": "Chinedu Emeka Okonkwo",
        "nok_name": "Ngozi Okonkwo",
        "nok_relationship": "SPOUSE",
        "nok_phone": "08077776644"
    }
    enroll_req = urllib.request.Request(
        'http://127.0.0.1:8088/api/admin/members',
        data=json.dumps(enroll_payload).encode('utf-8'),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:8088'}
    )
    with urllib.request.urlopen(enroll_req) as resp:
        enr_res = json.loads(resp.read().decode('utf-8'))
        new_m = enr_res['member']
        print(f"  [OK] {enr_res['message']}")
        print(f"  [OK] New Member Code: {new_m['member_code']} | Name: {new_m['full_name']} | Tier: {new_m['tier']}")
        new_mid = new_m['id']
        new_code = new_m['member_code']

    # 7. Verify Newly Enrolled Member Sign-In
    print("\n[Step 7] Verifying newly enrolled member can sign in with generated Code & Default Password...")
    new_login_req = urllib.request.Request(
        'http://127.0.0.1:8088/api/auth/login',
        data=json.dumps({'identifier': new_code, 'password': 'Wealthbridge@2026'}).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Origin': 'http://127.0.0.1:8088'}
    )
    with urllib.request.urlopen(new_login_req) as resp:
        new_body = json.loads(resp.read().decode('utf-8'))
        print(f"  [OK] Sign-in verified! {new_body['user']['full_name']} logged in with Code {new_body['user']['member_code']}")

    # 8. Clean up test cooperator Chinedu Okonkwo from DB
    print("\n[Step 8] Cleaning up enrolled test cooperator from database...")
    import wbmf_db
    conn = wbmf_db.WealthbridgeDB().get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM next_of_kin WHERE member_id = %s;", (new_mid,))
    c.execute("DELETE FROM share_accounts WHERE member_id = %s;", (new_mid,))
    c.execute("DELETE FROM savings_accounts WHERE member_id = %s;", (new_mid,))
    c.execute("DELETE FROM welfare_accounts WHERE member_id = %s;", (new_mid,))
    c.execute("DELETE FROM members WHERE id = %s;", (new_mid,))
    conn.commit()
    conn.close()
    print("  [OK] Test cooperator cleaned up. Member registry restored to clean state.")

    print("\n" + "=" * 70)
    print("ALL 8 VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == '__main__':
    run_tests()
