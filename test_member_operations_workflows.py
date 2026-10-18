"""
test_member_operations_workflows.py
====================================
End-to-End Automated Verification for Member Operations:
1. Peer Loan Guarantor Digital Consent State Machine (Module 3 & 6)
2. Cooperator Exit, Financial Clearance & Statutory Liquidation Settlement (Bye-Laws Articles 9 & 11)
3. Bulk Cooperator CSV Importer & Directory Exporter (Module 1)
"""

import sys
import os
import json
import io
import csv
from decimal import Decimal
from fastapi.testclient import TestClient

# Ensure current working directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wbmf_api import app, db

client = TestClient(app)

def get_auth_token(identifier, password="Wealthbridge@2026"):
    resp = client.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert resp.status_code == 200, f"Login failed for {identifier}: {resp.text}"
    return resp.json()["token"]

def test_member_operations_suite():
    print("\n" + "=" * 80)
    print("  RUNNING COMPREHENSIVE MEMBER OPERATIONS VERIFICATION SUITE")
    print("=" * 80)

    # 1. Authenticate Actors
    print("\n[Step 1] Authenticating Actors...")
    pres_token = get_auth_token("WMC-2026-001")
    pres_headers = {"Authorization": f"Bearer {pres_token}"}
    print("  + Authenticated President (WMC-2026-001)")

    member2_token = get_auth_token("WMC-2026-002")
    m2_headers = {"Authorization": f"Bearer {member2_token}"}
    print("  + Authenticated Borrower (WMC-2026-002)")

    # 2. Test Guarantor Candidate Discovery
    print("\n[Step 2] Testing Guarantor Candidates Discovery...")
    res = client.get("/api/members/guarantor-candidates", headers=m2_headers)
    assert res.status_code == 200, res.text
    candidates = res.json()["data"]
    print(f"  + Retrieved {len(candidates)} eligible guarantor candidates")
    assert any(c["id"] == 1 for c in candidates), "President (Member ID 1) should be eligible candidate"

    # Ensure President has sufficient savings balance for test guarantee
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("UPDATE savings_accounts SET total_balance = 500000.00, encumbered_balance = 0.00 WHERE member_id = 1;")
    conn.commit()
    cursor.close()
    conn.close()

    # 3. Apply for Loan with Nominated Guarantor
    print("\n[Step 3] Submitting Loan with Nominated Guarantor...")
    loan_payload = {
        "principal_amount": 50000.0,
        "tenure_months": 3,
        "purpose_narration": "Working capital facility testing guarantor workflow",
        "product_id": 1,
        "guarantors": [
            {
                "guarantor_member_id": 1,
                "guaranteed_amount": 50000.0
            }
        ]
    }
    res = client.post("/api/members/2/loans", json=loan_payload, headers=m2_headers)
    assert res.status_code == 200, res.text
    loan_data = res.json()["data"]
    loan_id = loan_data["id"]
    loan_ref = loan_data["loan_reference"]
    print(f"  + Created Loan #{loan_id} ({loan_ref})")
    assert loan_data["current_approval_stage"] == "GUARANTOR_CONSENT", f"Expected GUARANTOR_CONSENT, got {loan_data['current_approval_stage']}"

    # 4. Guarantor Views Incoming Guarantee Requests
    print("\n[Step 4] Guarantor Inspects Pending Guarantee Requests...")
    res = client.get("/api/members/1/guarantor-requests", headers=pres_headers)
    assert res.status_code == 200, res.text
    requests_list = res.json()["data"]
    target_req = next((r for r in requests_list if r["loan_id"] == loan_id), None)
    assert target_req is not None, "Target loan guarantee request not found for Guarantor 1"
    print(f"  + Found guarantee request ID #{target_req['id']} for Loan {loan_ref} (Status: {target_req['status']})")
    assert target_req["status"] == "PENDING_CONSENT"

    # 5. Guarantor Digitally Signs Consent
    print("\n[Step 5] Guarantor Digitally Signs Consent...")
    res = client.post(
        f"/api/members/1/guarantor-requests/{target_req['id']}/respond",
        json={"decision": "ACCEPT", "comments": "Approved as peer cooperator."},
        headers=pres_headers
    )
    assert res.status_code == 200, res.text
    consent_res = res.json()
    print(f"  + Consent recorded: {consent_res['message']}")
    assert consent_res["decision"] == "ACCEPTED"
    assert consent_res["all_guarantors_consented"] is True

    # Verify loan transitioned to CREDIT_COMMITTEE
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT current_approval_stage, status FROM loans WHERE id = %s;", (loan_id,))
    loan_row = cursor.fetchone()
    print(f"  + Loan approval stage is now: {loan_row['current_approval_stage']}")
    assert loan_row["current_approval_stage"] == "CREDIT_COMMITTEE"

    # Verify savings encumbrance
    cursor.execute("SELECT total_balance, encumbered_balance, available_balance FROM savings_accounts WHERE member_id = 1;")
    sav_row = cursor.fetchone()
    print(f"  + Guarantor Savings: Total={sav_row['total_balance']}, Encumbered={sav_row['encumbered_balance']}, Avail={sav_row['available_balance']}")
    assert Decimal(str(sav_row["encumbered_balance"])) >= Decimal("50000.00")

    # Clean up test loan so member 1 isn't blocked by guarantee on exit test
    cursor.execute("UPDATE loan_guarantors SET status = 'RELEASED' WHERE id = %s;", (target_req["id"],))
    cursor.execute("UPDATE savings_accounts SET encumbered_balance = 0.00 WHERE member_id = 1;")
    cursor.execute("UPDATE loans SET status = 'CANCELLED' WHERE id = %s;", (loan_id,))
    conn.commit()
    cursor.close()
    conn.close()

    # 6. Test Cooperator Exit & Liquidation Settlement Workflow
    print("\n[Step 6] Testing Cooperator Exit & Liquidation Settlement...")
    # Create a dummy cooperator specifically for exit test
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM member_exits WHERE member_id = 9999;")
    cursor.execute("DELETE FROM transactions WHERE member_id = 9999;")
    cursor.execute("DELETE FROM savings_accounts WHERE member_id = 9999;")
    cursor.execute("DELETE FROM share_accounts WHERE member_id = 9999;")
    cursor.execute("DELETE FROM welfare_accounts WHERE member_id = 9999;")
    cursor.execute("DELETE FROM members WHERE id = 9999;")
    cursor.execute("""
        INSERT INTO members (
            id, member_code, first_name, last_name, email, phone, gender,
            residential_address, identification_type, identification_number,
            status, kyc_completion_percent, admission_date
        ) VALUES (
            9999, 'WMC-TEST-999', 'TestExit', 'Cooperator', 'testexit@example.com',
            '08099999999', 'MALE', 'Ikeja, Lagos', 'NIN', '12345678999',
            'ACTIVE', 100, CURDATE()
        );
    """)
    cursor.execute("""
        INSERT INTO savings_accounts (member_id, total_balance, encumbered_balance)
        VALUES (9999, 150000.00, 0.00);
    """)
    cursor.execute("""
        INSERT INTO share_accounts (member_id, paid_up_amount, units_held, benefits_qualified)
        VALUES (9999, 25000.00, 25, 1);
    """)
    cursor.execute("""
        INSERT INTO welfare_accounts (member_id, cumulative_contributions)
        VALUES (9999, 5000.00);
    """)
    conn.commit()
    cursor.close()
    conn.close()

    # Submit Exit Notice for Voluntary Withdrawal
    exit_payload = {
        "exit_type": "VOLUNTARY_WITHDRAWAL",
        "reason": "Relocating abroad after 3 years of active membership."
    }
    # Test through President token (authorized admin for member 9999)
    res = client.post("/api/members/9999/exit-request", json=exit_payload, headers=pres_headers)
    assert res.status_code == 200, res.text
    exit_data = res.json()
    exit_id = exit_data["exit_id"]
    print(f"  + Exit Request #{exit_id} lodged:")
    print(f"    - Total Savings: NGN {exit_data['total_savings']:,.2f}")
    print(f"    - Total Shares:  NGN {exit_data['total_shares']:,.2f}")
    print(f"    - Exit Fee:      NGN {exit_data['exit_processing_fee']:,.2f}")
    print(f"    - Net Refund:    NGN {exit_data['net_refund_amount']:,.2f}")
    # Expected: 150000 + 25000 - 5000 = 170000 (Welfare is non-refundable per Art 23.4)
    assert exit_data["net_refund_amount"] == 170000.0, f"Expected 170000.0, got {exit_data['net_refund_amount']}"

    # Verify pending exit appears in executive review list
    res = client.get("/api/admin/exits/pending", headers=pres_headers)
    assert res.status_code == 200, res.text
    pending_list = res.json()["data"]
    found_exit = next((e for e in pending_list if e["id"] == exit_id), None)
    assert found_exit is not None, "Pending exit not found in executive queue"
    print(f"  + Exit #{exit_id} confirmed in executive queue ({found_exit['member_code']})")

    # Executive Signs Off Settlement
    print("\n[Step 7] Executive Finalizes Exit Settlement...")
    res = client.post(
        f"/api/admin/exits/{exit_id}/approve",
        json={"refund_payment_ref": "EXIT-TEST-SETTLE-001"},
        headers=pres_headers
    )
    assert res.status_code == 200, res.text
    approve_data = res.json()
    print(f"  + Settlement finalized: {approve_data['message']}")
    assert approve_data["new_membership_status"] == "EXITED"

    # Verify balances zeroed out and member marked EXITED
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT status FROM members WHERE id = 9999;")
    m_check = cursor.fetchone()
    assert m_check["status"] == "EXITED", f"Expected EXITED, got {m_check['status']}"

    cursor.execute("SELECT total_balance FROM savings_accounts WHERE member_id = 9999;")
    s_check = cursor.fetchone()
    assert Decimal(str(s_check["total_balance"])) == Decimal("0.00")

    # Clean up test member 9999
    cursor.execute("DELETE FROM member_exits WHERE member_id = 9999;")
    cursor.execute("DELETE FROM transactions WHERE member_id = 9999;")
    cursor.execute("DELETE FROM savings_accounts WHERE member_id = 9999;")
    cursor.execute("DELETE FROM share_accounts WHERE member_id = 9999;")
    cursor.execute("DELETE FROM welfare_accounts WHERE member_id = 9999;")
    cursor.execute("DELETE FROM members WHERE id = 9999;")
    conn.commit()
    cursor.close()
    conn.close()

    # 8. Test Bulk CSV Importer & Exporter
    print("\n[Step 8] Testing Bulk CSV Template & Directory Export...")
    res = client.get("/api/admin/members/template-csv", headers=pres_headers)
    assert res.status_code == 200, f"template-csv failed ({res.status_code}): {res.text}"
    assert "attachment; filename=\"Wealthbridge_Member_Import_Template.csv\"" in res.headers["content-disposition"]
    template_text = res.text
    assert "first_name,last_name,email" in template_text
    print("  + Template CSV generated and verified")

    res = client.get("/api/admin/members/export-csv", headers=pres_headers)
    assert res.status_code == 200, f"export-csv failed ({res.status_code}): {res.text}"
    assert "text/csv" in res.headers["content-type"]
    export_text = res.text
    assert "Member Code,Full Name,Email" in export_text
    assert "WMC-2026-001" in export_text
    print("  + Cooperator Directory CSV exported and verified")

    # Test Bulk CSV Upload with 2 new cooperators
    print("\n[Step 9] Testing Bulk CSV Import Execution...")
    csv_stream = io.StringIO()
    writer = csv.writer(csv_stream)
    writer.writerow([
        "first_name", "last_name", "email", "phone", "gender",
        "marital_status", "residential_address", "identification_number",
        "contribution_tier", "opening_savings", "opening_shares", "opening_welfare"
    ])
    writer.writerow([
        "Chukwuma", "Nnamdi", "chukwuma.test@wealthbridge.ng", "08011223344", "MALE",
        "MARRIED", "10 Marina Street, Lagos Island", "99887766554",
        "PLUS", "200000.00", "50000.00", "5000.00"
    ])
    csv_bytes = csv_stream.getvalue().encode("utf-8")

    files = {"file": ("test_import.csv", io.BytesIO(csv_bytes), "text/csv")}
    res = client.post("/api/admin/members/bulk-import", files=files, headers=pres_headers)
    assert res.status_code == 200, res.text
    import_res = res.json()
    print(f"  + Bulk import result: Imported {import_res['imported_count']}, Skipped {import_res['skipped_count']}")
    assert import_res["imported_count"] == 1
    new_member = import_res["imported_members"][0]
    print(f"    - Assigned Code: {new_member['member_code']} to {new_member['full_name']}")

    # Clean up imported test cooperator
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("DELETE FROM transactions WHERE member_id = %s;", (new_member["id"],))
    cursor.execute("DELETE FROM savings_accounts WHERE member_id = %s;", (new_member["id"],))
    cursor.execute("DELETE FROM share_accounts WHERE member_id = %s;", (new_member["id"],))
    cursor.execute("DELETE FROM welfare_accounts WHERE member_id = %s;", (new_member["id"],))
    cursor.execute("DELETE FROM members WHERE id = %s;", (new_member["id"],))
    conn.commit()
    cursor.close()
    conn.close()

    print("\n" + "=" * 80)
    print("  ALL MEMBER OPERATIONS TESTS PASSED (100% SUCCESS)!")
    print("=" * 80)

if __name__ == "__main__":
    test_member_operations_suite()
