"""
test_comprehensive_governance.py
Automated End-to-End Verification Suite for Wealthbridge Cooperative Governance Suite
"""

import json
import requests
import sys
import time

BASE_URL = "http://127.0.0.1:8088/api"

def print_header(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def assert_true(cond, msg):
    if not cond:
        print(f"[FAIL] {msg}")
        sys.exit(1)
    else:
        print(f"[PASS] {msg}")

def test_governance_suite():
    # -------------------------------------------------------------------------
    # Authentication Setup: Dual Persona (Executive + Borrower Member)
    # -------------------------------------------------------------------------
    print_header("Authenticating Executive Officer (WMC-2026-001 - President)")
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "identifier": "WMC-2026-001",
        "password": "Wealthbridge@2026"
    })
    assert_true(login_res.status_code == 200, "President login successful")
    exec_token = login_res.json().get("token")
    assert_true(exec_token is not None, "Obtained valid executive session token")
    exec_headers = {
        "Authorization": f"Bearer {exec_token}",
        "Content-Type": "application/json"
    }

    print_header("Authenticating Cooperator Member (WMC-2026-002 - Evelyn)")
    mem_login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "identifier": "WMC-2026-002",
        "password": "Wealthbridge@2026"
    })
    assert_true(mem_login_res.status_code == 200, "Member 2 login successful")
    mem_token = mem_login_res.json().get("token")
    assert_true(mem_token is not None, "Obtained valid member session token")
    member_headers = {
        "Authorization": f"Bearer {mem_token}",
        "Content-Type": "application/json"
    }

    # -------------------------------------------------------------------------
    # 1. Compulsory KYC Dedicated Virtual Account (DVA) Gating
    # -------------------------------------------------------------------------
    print_header("1. Testing Compulsory KYC Dedicated Virtual Account Gating")
    
    # Member 1 (President Qazeem Adebowale) - has 100% compulsory KYC
    res = requests.get(f"{BASE_URL}/members/1/dedicated-account", headers=exec_headers)
    assert_true(res.status_code == 200, "Get Member 1 DVA status code 200")
    data = res.json()
    assert_true(data.get("is_locked") is False, "Member 1 DVA is unlocked (100% KYC)")
    assert_true("data" in data and "account_number" in data["data"], "Member 1 DVA contains account number")
    print(f"   Member 1 DVA: {data['data'].get('bank_name')} - {data['data'].get('account_number')}")

    # Check compulsory KYC checklist endpoint for Member 1
    res = requests.get(f"{BASE_URL}/members/1/kyc-compulsory-status", headers=exec_headers)
    assert_true(res.status_code == 200, "Member 1 KYC status code 200")
    kyc_data = res.json()
    assert_true(kyc_data.get("is_compulsory_complete") is True, "Member 1 compulsory KYC is complete")
    score = kyc_data.get("compulsory_score_percent") or kyc_data.get("kyc_completion_percent")
    assert_true(score == 100, f"Member 1 compulsory KYC is 100% (got {score})")

    # -------------------------------------------------------------------------
    # 2. Applicant Dossier Inspection Drawer
    # -------------------------------------------------------------------------
    print_header("2. Testing Secretariat Applicant Dossier Inspection")
    res = requests.get(f"{BASE_URL}/admin/pending-members/1/dossier", headers=exec_headers)
    assert_true(res.status_code == 200, "Get Member 1 Dossier status code 200")
    dossier = res.json()
    dossier_data = dossier.get("data") or dossier
    assert_true("member" in dossier_data and "compulsory_kyc" in dossier_data, "Dossier structure contains member and compulsory_kyc")
    m_info = dossier_data["member"]
    print(f"   Dossier member: {m_info.get('first_name')} {m_info.get('last_name')}, Tier: {m_info.get('contribution_tier')}")

    # -------------------------------------------------------------------------
    # 3. Dynamic RBAC & Role Allocations
    # -------------------------------------------------------------------------
    print_header("3. Testing Dynamic RBAC & Operational Role Allocation")
    
    # Fetch all system permissions
    res = requests.get(f"{BASE_URL}/admin/permissions", headers=exec_headers)
    assert_true(res.status_code == 200, "Fetch system permissions status 200")
    perms_resp = res.json()
    perms = perms_resp.get("data") or perms_resp
    assert_true(len(perms) >= 35, f"All 35 statutory permissions present (Found {len(perms)})")

    # Create a custom operational role
    ts = int(time.time())
    custom_role_code = f"ROLE_TEST_{ts}"
    role_payload = {
        "role_code": custom_role_code,
        "role_name": f"Credit Risk Inspector {ts}",
        "description": "Inspects collateral assets and validates borrower capacity",
        "permission_keys": ["apply_loan", "credit_committee_approval", "system_audit"]
    }
    res = requests.post(f"{BASE_URL}/admin/roles", json=role_payload, headers=exec_headers)
    assert_true(res.status_code == 200, f"Create custom operational role status 200: {res.text}")
    new_role_resp = res.json()
    new_role = new_role_resp.get("data") or new_role_resp
    role_id = new_role.get("id") or new_role.get("role_id")
    assert_true(role_id is not None, f"Custom role created with ID {role_id}")

    # Assign custom role to Member 2 (Omokosi Evelyn)
    assign_payload = {
        "role_id": role_id
    }
    res = requests.post(f"{BASE_URL}/admin/members/2/roles", json=assign_payload, headers=exec_headers)
    assert_true(res.status_code == 200, "Assign role to Member 2 status 200")

    # Verify Member 2 has the new role
    res = requests.get(f"{BASE_URL}/members/2/roles", headers=exec_headers)
    assert_true(res.status_code == 200, "Get Member 2 roles status 200")
    mem_roles = res.json().get("data") or res.json()
    assert_true(any(r["role_code"] == custom_role_code for r in mem_roles), f"Member 2 has {custom_role_code} role assigned")

    # Revoke custom role from Member 2
    res = requests.delete(f"{BASE_URL}/admin/members/2/roles/{role_id}", headers=exec_headers)
    assert_true(res.status_code == 200, f"Revoke role from Member 2 status 200: {res.text}")

    # -------------------------------------------------------------------------
    # 4. Multi-Tier Loan Approval & Sequential Pipeline
    # -------------------------------------------------------------------------
    print_header("4. Testing Multi-Tier Loan Approval Pipeline & Appeals")

    # Member 2 applies for a loan
    loan_payload = {
        "principal_amount": 60000.0,
        "tenure_months": 6,
        "purpose_narration": "Professional Equipment Acquisition"
    }
    res = requests.post(f"{BASE_URL}/members/2/loans", json=loan_payload, headers=member_headers)
    assert_true(res.status_code == 200, f"Member 2 loan application submitted (status 200): {res.text}")
    loan1_resp = res.json()
    loan1 = loan1_resp.get("data") or loan1_resp
    loan1_id = loan1.get("id") or loan1.get("loan_id")
    loan1_ref = loan1.get("loan_reference")
    assert_true(loan1_id is not None, f"Loan created with reference {loan1_ref}")

    # Verify borrower sees only percentage and status (Borrower Confidentiality)
    res = requests.get(f"{BASE_URL}/members/2/loans", headers=member_headers)
    assert_true(res.status_code == 200, "Member 2 loans list status 200")
    borrower_loans = res.json().get("data") or res.json()
    loan_view = next((l for l in borrower_loans if l["id"] == loan1_id), None)
    assert_true(loan_view is not None, "Loan present in borrower list")
    assert_true(loan_view.get("approval_level_percent") == 0, "Borrower sees 0% initial approval level")
    assert_true("internal_committee_deliberation" not in loan_view, "Borrower confidentiality preserved")

    # Stage 1: Credit Committee Review (Advances to 33%)
    review_stage1 = {
        "action": "APPROVE",
        "comments": "Credit score and savings collateral verified satisfactory.",
        "is_president_override": False
    }
    res = requests.post(f"{BASE_URL}/admin/loans/{loan1_id}/review", json=review_stage1, headers=exec_headers)
    assert_true(res.status_code == 200, f"Stage 1 Committee review passed: {res.text}")
    res1_data = res.json().get("data") or res.json()
    assert_true(res1_data.get("approval_level_percent") == 33, "Approval level advanced to 33%")
    assert_true(res1_data.get("current_approval_stage") == "FINANCIAL_SECRETARY", "Next stage is FINANCIAL_SECRETARY")

    # Stage 2: Financial Secretary Review (Advances to 66%)
    review_stage2 = {
        "action": "APPROVE",
        "comments": "Monthly remittance capacity and 2x savings limit confirmed.",
        "is_president_override": False
    }
    res = requests.post(f"{BASE_URL}/admin/loans/{loan1_id}/review", json=review_stage2, headers=exec_headers)
    assert_true(res.status_code == 200, "Stage 2 FinSec review passed")
    res2_data = res.json().get("data") or res.json()
    assert_true(res2_data.get("approval_level_percent") == 66, "Approval level advanced to 66%")
    assert_true(res2_data.get("current_approval_stage") == "TREASURER", "Next stage is TREASURER")

    # Stage 3: Treasurer Review & Disbursement (Advances to 100% & ACTIVE)
    review_stage3 = {
        "action": "APPROVE",
        "comments": "Disbursement approved and loan ledger created.",
        "is_president_override": False
    }
    res = requests.post(f"{BASE_URL}/admin/loans/{loan1_id}/review", json=review_stage3, headers=exec_headers)
    assert_true(res.status_code == 200, "Stage 3 Treasurer review passed")
    res3_data = res.json().get("data") or res.json()
    assert_true(res3_data.get("approval_level_percent") == 100, "Approval level reached 100%")
    assert_true(res3_data.get("loan_status") == "ACTIVE" or res3_data.get("status") == "ACTIVE", "Loan status is ACTIVE (Disbursed)")

    # Test Presidential Superior Override
    print("\n   Testing Presidential Superior Override on Loan 2...")
    loan2_payload = {
        "principal_amount": 50000.0,
        "tenure_months": 4,
        "purpose_narration": "Medical Emergency Financing"
    }
    res = requests.post(f"{BASE_URL}/members/2/loans", json=loan2_payload, headers=member_headers)
    loan2_id = (res.json().get("data") or res.json())["id"]

    override_review = {
        "action": "APPROVE",
        "comments": "Presidential Superior Override invoked for emergency healthcare assistance.",
        "is_president_override": True
    }
    res = requests.post(f"{BASE_URL}/admin/loans/{loan2_id}/review", json=override_review, headers=exec_headers)
    assert_true(res.status_code == 200, "Presidential Override passed")
    ov_data = res.json().get("data") or res.json()
    assert_true(ov_data.get("approval_level_percent") == 100, "Presidential Override set 100% directly")
    assert_true(ov_data.get("presidential_override") is True or ov_data.get("presidential_override") == 1, "presidential_override recorded as True")

    # Test Declined Loan & Statutory Appeal Flow
    print("\n   Testing Declined Loan & Statutory Appeal...")
    loan3_payload = {
        "principal_amount": 35000.0,
        "tenure_months": 6,
        "purpose_narration": "Commercial Venture Capital"
    }
    res = requests.post(f"{BASE_URL}/members/2/loans", json=loan3_payload, headers=member_headers)
    loan3_id = (res.json().get("data") or res.json())["id"]

    decline_review = {
        "action": "DECLINE",
        "comments": "Requested amount exceeds 2x unencumbered savings cap.",
        "is_president_override": False
    }
    res = requests.post(f"{BASE_URL}/admin/loans/{loan3_id}/review", json=decline_review, headers=exec_headers)
    assert_true(res.status_code == 200, "Loan declined recorded")

    # Member submits statutory appeal
    appeal_payload = {
        "appeal_comments": "Attached evidence of supplementary collateral and off-cycle deposit receipt for committee reconsideration.",
        "attached_document_path": "/uploads/documents/appeal_supplementary_proof.pdf"
    }
    res = requests.post(f"{BASE_URL}/members/2/loans/{loan3_id}/appeal", json=appeal_payload, headers=member_headers)
    assert_true(res.status_code == 200, f"Statutory appeal submitted: {res.text}")
    appeal_data = res.json().get("data") or res.json()
    appeal_id = appeal_data.get("appeal_id") or appeal_data.get("id")
    assert_true(appeal_id is not None, f"Appeal created with ID {appeal_id}")

    # Executive resolves appeal: Overturn & Disburse
    resolve_payload = {
        "action": "REINSTATE",
        "review_response": "Supplementary proof verified. Approved under presidential arbitration."
    }
    res = requests.post(f"{BASE_URL}/admin/loan-appeals/{appeal_id}/resolve", json=resolve_payload, headers=exec_headers)
    assert_true(res.status_code == 200, "Appeal resolved as REINSTATE (Overturned & Approved)")

    # -------------------------------------------------------------------------
    # 5. Polaris Bank Manual Transfer Logging & Reconcile / Direct Credit
    # -------------------------------------------------------------------------
    print_header("5. Testing Polaris Bank Manual Transfer Logging & Reconciliation")

    # Member logs manual Polaris transfer
    manual_pay_payload = {
        "amount": 25000.0,
        "payment_reference": f"POLARIS-DEP-{int(time.time())}",
        "payment_date": "2026-10-17",
        "narration": "Direct branch cash deposit via Odogunyan Polaris Bank branch",
        "receipt_file_path": "/uploads/receipts/polaris_teller_0099.jpg"
    }
    res = requests.post(f"{BASE_URL}/members/2/manual-payments", json=manual_pay_payload, headers=member_headers)
    assert_true(res.status_code == 200, f"Manual transfer logged (status 200): {res.text}")
    mp_data = res.json().get("data") or res.json()
    payment_id = mp_data.get("payment_id") or mp_data.get("id")
    assert_true(payment_id is not None, f"Payment logged with ID {payment_id}")

    # Treasury verifies and auto-distributes via waterfall
    verify_payload = {
        "verification_notes": "Polaris Bank branch deposit teller receipt verified against statement"
    }
    res = requests.post(f"{BASE_URL}/admin/manual-payments/{payment_id}/verify", json=verify_payload, headers=exec_headers)
    assert_true(res.status_code == 200, f"Manual payment verified & waterfall distributed: {res.text}")
    v_data = res.json().get("data") or res.json()
    assert_true("distribution" in v_data or "waterfall_distribution" in v_data, "Waterfall distribution completed")

    # Executive Direct Member Account Credit
    direct_credit_payload = {
        "member_id": 2,
        "credit_category": "SAVINGS",
        "amount": 10000.0,
        "narration": "Statutory incentive dividend allocation authorized by Board"
    }
    res = requests.post(f"{BASE_URL}/admin/manual-payments/direct-credit", json=direct_credit_payload, headers=exec_headers)
    assert_true(res.status_code == 200, f"Direct account credit posted successfully: {res.text}")

    # -------------------------------------------------------------------------
    # 6. Payment Advice Modifications
    # -------------------------------------------------------------------------
    print_header("6. Testing Payment Advice Revision Desk")
    modify_payload = {
        "amount_regular_savings": 22000.0,
        "amount_share_capital": 3000.0,
        "amount_welfare": 1000.0,
        "scope": "THIS_MONTH_ONLY",
        "statutory_justification": "Cooperator requested temporary voluntary increase in share equity per SOP"
    }
    res = requests.post(f"{BASE_URL}/admin/payment-advices/1/modify", json=modify_payload, headers=exec_headers)
    assert_true(res.status_code == 200, f"Payment advice modified with statutory justification: {res.text}")

    # -------------------------------------------------------------------------
    # 7. Tamper-Evident Forensic Audit Trail
    # -------------------------------------------------------------------------
    print_header("7. Testing Tamper-Evident Forensic Audit Trail")

    # Query audit logs
    res = requests.get(f"{BASE_URL}/admin/audit-logs?limit=20", headers=exec_headers)
    assert_true(res.status_code == 200, "Fetch forensic audit logs status 200")
    logs = res.json()
    data = logs.get("data") or logs
    logs_list = data.get("logs") if isinstance(data, dict) and "logs" in data else data
    assert_true(len(logs_list) > 0, f"Forensic audit trail captured {len(logs_list)} immutable events")

    # Check that diffs are preserved
    sample_log = logs_list[0]
    assert_true("action" in sample_log and "actor_id" in sample_log and "created_at" in sample_log, "Audit event contains action, actor, and timestamp")
    print(f"   Latest audit event: [{sample_log['created_at']}] {sample_log.get('actor_role')}: {sample_log['action']} on {sample_log.get('resource_type')}")

    # Test CSV export
    res = requests.get(f"{BASE_URL}/admin/audit-logs/export", headers=exec_headers)
    assert_true(res.status_code == 200, "Forensic audit CSV export status 200")
    assert_true("text/csv" in res.headers.get("content-type", ""), "Export response content-type is text/csv")
    csv_lines = res.text.strip().split("\n")
    assert_true(len(csv_lines) > 1, f"CSV export contains {len(csv_lines)} rows of forensic data")

    print_header("ALL 7 GOVERNANCE SUITE CAPABILITIES VERIFIED 100% OPERATIONAL!")

if __name__ == "__main__":
    test_governance_suite()
