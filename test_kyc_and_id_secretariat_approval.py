"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
TEST SUITE: COMPREHENSIVE KYC SCOPE & SECRETARIAT ID CARD APPROVAL
-----------------------------------------------------------------------------
Verifies:
1. Overall KYC Completion % concerns ALL KYC information (Personal, NIN, Contact, Photo, Bank, Next of Kin),
   NOT only compulsory fields. Completing 6 compulsory fields unlocks DVA, but yields ~50-60% total KYC.
2. Official Electronic Membership ID Card is accessible and downloadable ONLY after formal
   Secretariat approval (status in 'ACTIVE', 'SYSTEM_ADMINISTRATOR').
3. Non-approved cooperators (PENDING_KYC) receive 403 Forbidden on ID card endpoints even with 100% KYC.
4. Once General Secretary approves the cooperator, ID card becomes fully visible and downloadable.

Official Email Invariant: wealthbridge.coopsociety@gmail.com
=============================================================================
"""

import sys
import os
import requests
from decimal import Decimal
from datetime import datetime

from wbmf_db import WealthbridgeDB

BASE_URL = "http://127.0.0.1:8088/api"

def assert_true(condition, msg):
    if not condition:
        print(f"[FAIL] {msg}")
        sys.exit(1)
    print(f"[PASS] {msg}")

def main():
    print("=" * 70)
    print("TESTING COMPREHENSIVE KYC SCOPE & SECRETARIAT APPROVAL FOR ID CARDS")
    print("=" * 70)

    db = WealthbridgeDB()
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)

    test_email = "test_applicant_kyc@wealthbridge.ng"
    test_code = "WMC-2026-999"

    try:
        # Cleanup any previous test run
        cursor.execute("SELECT id FROM members WHERE email = %s OR member_code = %s;", (test_email, test_code))
        existing = cursor.fetchone()
        if existing:
            m_id = existing["id"]
            cursor.execute("DELETE FROM next_of_kin WHERE member_id = %s;", (m_id,))
            cursor.execute("DELETE FROM members WHERE id = %s;", (m_id,))
            conn.commit()

        # Step 1: Create an applicant who has completed ONLY the 6 compulsory fields:
        # 1. First Name, 2. Last Name, 3. Phone, 4. Email, 5. Residential Address, 6. NIN
        # (NO passport photo, NO commercial bank account, NO next of kin)
        cursor.execute("""
            INSERT INTO members (
                member_code, first_name, last_name, email, phone, residential_address,
                identification_type, identification_number, password_hash, contribution_tier,
                status, kyc_completion_percent
            ) VALUES (
                %s, 'Olumide', 'Adegbenro', %s, '08012349999', '12 Awolowo Way, Ikeja, Lagos',
                'NIN', '12345678901', 'dummyhash12345678', 'STANDARD',
                'PENDING_KYC', 0
            );
        """, (test_code, test_email))
        conn.commit()
        applicant_id = cursor.lastrowid
        print(f"-> Created test applicant with 6 compulsory fields: ID #{applicant_id} ({test_code})")

        # Step 2: Evaluate Compulsory KYC vs Comprehensive KYC Scope
        kyc_eval = db.evaluate_compulsory_kyc(applicant_id)
        print(f"-> kyc_eval: is_compulsory_complete={kyc_eval['is_compulsory_complete']}, "
              f"compulsory_score_percent={kyc_eval['compulsory_score_percent']}%, "
              f"total_kyc_percent={kyc_eval['kyc_completion_percent']}%")

        assert_true(kyc_eval["is_compulsory_complete"] is True, "Compulsory DVA fields completed (6/6)")
        assert_true(kyc_eval["compulsory_score_percent"] == 100, "Compulsory score is 100% for DVA gating")
        assert_true(kyc_eval["kyc_completion_percent"] < 100, 
                    f"Overall KYC completion ({kyc_eval['kyc_completion_percent']}%) is NOT 100% because Photo, Bank, and NOK are missing")
        assert_true(kyc_eval["kyc_completion_percent"] == 50 or kyc_eval["kyc_completion_percent"] == 60,
                    f"Overall KYC concerns ALL information (~50-60% without Photo/Bank/NOK). Got: {kyc_eval['kyc_completion_percent']}%")

        # Step 3: Check DVA account generation with compulsory KYC passed
        dva_res = db.get_or_create_member_dva(applicant_id, check_compulsory_kyc=True)
        assert_true(dva_res.get("is_locked") is not True, "DVA is unlocked because compulsory fields are satisfied")

        # Step 4: Login as President (Executive) via API
        pres_res = requests.post(f"{BASE_URL}/auth/login", json={"identifier": "WMC-2026-001", "password": "Wealthbridge@2026"})
        assert_true(pres_res.status_code == 200, "President login succeeded")
        exec_token = pres_res.json()["token"]
        exec_headers = {"Authorization": f"Bearer {exec_token}"}

        # Step 5: Test ID card visibility for PENDING_KYC applicant
        # Set a password for the applicant to authenticate them
        from wbmf_db import hash_password
        cursor.execute("UPDATE members SET password_hash = %s WHERE id = %s;", (hash_password("Wealthbridge@2026"), applicant_id))
        conn.commit()

        app_login = requests.post(f"{BASE_URL}/auth/login", json={"identifier": test_email, "password": "Wealthbridge@2026"})
        assert_true(app_login.status_code == 200, "Applicant login succeeded")
        applicant_headers = {"Authorization": f"Bearer {app_login.json()['token']}"}

        # Try to view ID card data as cooperator whose status is PENDING_KYC
        res_view = requests.get(f"{BASE_URL}/members/{applicant_id}/id-card", headers=applicant_headers)
        print(f"-> Unapproved cooperator GET /id-card: Status {res_view.status_code}, Body: {res_view.text}")
        assert_true(res_view.status_code == 403, "Unapproved cooperator cannot view ID card (HTTP 403 Forbidden)")
        assert_true("Secretariat approval" in res_view.text, "Error details mention Secretariat approval")

        # Try to download ID card PDF as unapproved cooperator
        res_pdf = requests.get(f"{BASE_URL}/members/{applicant_id}/id-card/pdf", headers=applicant_headers)
        print(f"-> Unapproved cooperator GET /id-card/pdf: Status {res_pdf.status_code}")
        assert_true(res_pdf.status_code == 403, "Unapproved cooperator cannot download ID card PDF (HTTP 403 Forbidden)")

        # Step 6: Even if applicant completes 100% of ALL KYC fields, ID card remains LOCKED until Secretariat approves
        cursor.execute("""
            UPDATE members SET
                passport_photo = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
                bank_name = 'First Bank of Nigeria',
                bank_account_number = '0123456789',
                bank_account_name = 'Olumide Adegbenro'
            WHERE id = %s;
        """, (applicant_id,))
        cursor.execute("""
            INSERT INTO next_of_kin (member_id, full_name, relationship, phone, residential_address, allocation_percentage)
            VALUES (%s, 'Funke Adegbenro', 'SPOUSE', '08099887766', '12 Awolowo Way, Ikeja', 100.00);
        """, (applicant_id,))
        conn.commit()

        # Re-evaluate KYC: now 100%
        full_eval = db.evaluate_compulsory_kyc(applicant_id)
        print(f"-> After completing all sections, KYC is: {full_eval['kyc_completion_percent']}%")
        assert_true(full_eval["kyc_completion_percent"] == 100, "KYC is now 100% complete across all categories")

        # Status is STILL PENDING_KYC! Check ID card access again:
        res_view_100 = requests.get(f"{BASE_URL}/members/{applicant_id}/id-card", headers=applicant_headers)
        assert_true(res_view_100.status_code == 403, 
                    "ID card is STRICTLY locked even at 100% KYC before Secretariat approval (HTTP 403)")

        # Step 7: Executive (General Secretary / President) approves applicant
        approve_res = db.approve_member_kyc(applicant_id, officer_id=1)
        assert_true(approve_res["status"] == "SUCCESS", "Secretariat successfully approves member")

        # Verify DB status is now ACTIVE
        cursor.execute("SELECT status FROM members WHERE id = %s;", (applicant_id,))
        updated_member = cursor.fetchone()
        assert_true(updated_member["status"] == "ACTIVE", "Member status is now ACTIVE")

        # Step 8: Now cooperator can view and download their official Electronic ID card!
        # Re-authenticate to refresh session / status
        app_login_approved = requests.post(f"{BASE_URL}/auth/login", json={"identifier": test_email, "password": "Wealthbridge@2026"})
        assert_true(app_login_approved.status_code == 200, "Approved applicant login succeeded")
        approved_headers = {"Authorization": f"Bearer {app_login_approved.json()['token']}"}

        res_view_approved = requests.get(f"{BASE_URL}/members/{applicant_id}/id-card", headers=approved_headers)
        assert_true(res_view_approved.status_code == 200, "Approved cooperator can now view ID card (HTTP 200)")
        card_data = res_view_approved.json()
        assert_true(card_data.get("eligible") is True, "ID card eligibility is True after Secretariat approval")
        assert_true(card_data["data"]["secretariat_contact"] == "wealthbridge.coopsociety@gmail.com", 
                    "Official email invariant wealthbridge.coopsociety@gmail.com present")

        res_pdf_approved = requests.get(f"{BASE_URL}/members/{applicant_id}/id-card/pdf", headers=approved_headers)
        assert_true(res_pdf_approved.status_code == 200, "Approved cooperator can download vector PDF ID card (HTTP 200)")
        assert_true(res_pdf_approved.headers.get("content-type") == "application/pdf", "Response is valid application/pdf")
        assert_true(len(res_pdf_approved.content) > 1000, f"PDF file size is healthy ({len(res_pdf_approved.content)} bytes)")

        print("\n" + "=" * 70)
        print("ALL VERIFICATIONS PASSED SUCCESSFULLY (100% GREEN)!")
        print("=" * 70)

    finally:
        # Cleanup test applicant
        try:
            cursor.execute("SELECT id FROM members WHERE email = %s OR member_code = %s;", (test_email, test_code))
            existing = cursor.fetchone()
            if existing:
                m_id = existing["id"]
                cursor.execute("DELETE FROM next_of_kin WHERE member_id = %s;", (m_id,))
                cursor.execute("DELETE FROM members WHERE id = %s;", (m_id,))
                conn.commit()
        except Exception:
            pass
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
