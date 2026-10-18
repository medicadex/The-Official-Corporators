"""
test_guarantors_and_statutory_loans.py
End-to-End Verification for Loan Guarantor Selection, Savings Hover Data,
and 4 Statutory Bye-Law Loan Products.
"""

import sys
import requests

BASE_URL = "http://127.0.0.1:8088/api"

def print_step(msg):
    print(f"\n[STEP] {msg}")

def assert_true(cond, msg):
    if not cond:
        print(f"[FAIL] {msg}")
        sys.exit(1)
    else:
        print(f"[PASS] {msg}")

def run_tests():
    print("=" * 70)
    print(" WEALTHBRIDGE COOPERATIVE: GUARANTOR & STATUTORY LOANS VERIFICATION")
    print("=" * 70)

    # 1. Authenticate Executive / President
    print_step("1. Authenticating President (WMC-2026-001)")
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "identifier": "WMC-2026-001",
        "password": "Wealthbridge@2026"
    })
    assert_true(res.status_code == 200, "President login successful")
    pres_token = res.json()["token"]
    pres_headers = {"Authorization": f"Bearer {pres_token}"}

    # 2. Authenticate Borrower Cooperator (WMC-2026-002)
    print_step("2. Authenticating Cooperator Borrower (WMC-2026-002)")
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "identifier": "WMC-2026-002",
        "password": "Wealthbridge@2026"
    })
    assert_true(res.status_code == 200, "Borrower login successful")
    borrower_data = res.json()["user"]
    borrower_id = borrower_data["id"]
    borrower_token = res.json()["token"]
    borrower_headers = {"Authorization": f"Bearer {borrower_token}"}

    # 3. Verify Statutory Loan Products
    print_step("3. Verifying GET /api/loan-products")
    res = requests.get(f"{BASE_URL}/loan-products")
    assert_true(res.status_code == 200, "Fetched loan products successfully")
    products = res.json().get("data", [])
    assert_true(len(products) == 4, f"Found exactly 4 statutory loan products (got {len(products)})")

    product_codes = [p["product_code"] for p in products]
    product_names = [p["product_name"] for p in products]
    print(f"Loaded Products: {product_names}")
    assert_true("ORDINARY_LOAN" in product_codes, "Ordinary loan (*2 of savings) present")
    assert_true("INVESTMENT_LOAN" in product_codes, "Investment Loan present")
    assert_true("SALARY_ADVANCE" in product_codes, "Salary Advance Loan present")
    assert_true("GENERAL_PURCHASE_LOAN" in product_codes, "General Purchase Loan present")

    # 4. Verify Guarantor Candidates Endpoint
    print_step("4. Verifying GET /api/members/guarantor-candidates")
    res = requests.get(f"{BASE_URL}/members/guarantor-candidates", headers=borrower_headers)
    assert_true(res.status_code == 200, "Fetched guarantor candidates successfully")
    candidates = res.json().get("data", [])
    assert_true(len(candidates) > 0, "Guarantor candidates list is not empty")
    
    # Ensure current borrower is excluded from candidates list
    candidate_ids = [c["id"] for c in candidates]
    assert_true(borrower_id not in candidate_ids, "Borrower cannot be a candidate guarantor for themselves")
    
    # Ensure candidates have total_savings field populated
    first_cand = candidates[0]
    assert_true("total_savings" in first_cand, "Guarantor candidate includes total_savings field")
    print(f"Sample Candidate: {first_cand['member_code']} - {first_cand['full_name']} (Total Savings: NGN {first_cand['total_savings']:,.2f})")

    # Pick 2 guarantors for the loan application
    guarantor_1 = candidates[0]
    guarantor_2 = candidates[1] if len(candidates) > 1 else candidates[0]

    # 5. Test Loan Application with Multiple Guarantors
    print_step("5. Submitting Loan Application with Multiple Guarantors")
    loan_payload = {
        "principal_amount": 50000.0,
        "tenure_months": 6,
        "purpose_narration": "Working capital financing with peer co-signers",
        "product_id": 1, # Ordinary Loan (*2 of savings)
        "guarantors": [
            {
                "guarantor_member_id": guarantor_1["id"],
                "guaranteed_amount": 25000.0
            },
            {
                "guarantor_member_id": guarantor_2["id"],
                "guaranteed_amount": 25000.0
            }
        ]
    }
    res = requests.post(
        f"{BASE_URL}/members/{borrower_id}/loans",
        json=loan_payload,
        headers=borrower_headers
    )
    assert_true(res.status_code == 200, f"Loan submitted successfully (status: {res.status_code}, {res.text})")
    loan_data = res.json().get("data", {})
    loan_id = loan_data["id"]
    loan_ref = loan_data["loan_reference"]
    print(f"Created Loan: ID {loan_id}, Ref: {loan_ref}, Attached Guarantors: {len(loan_data.get('guarantors', []))}")
    assert_true(len(loan_data.get("guarantors", [])) >= 1, "Guarantors attached to created loan")

    # 6. Test Self-Guarantor Validation
    print_step("6. Verifying Self-Guarantor Validation Fails Cleanly")
    invalid_payload = {
        "principal_amount": 30000.0,
        "tenure_months": 6,
        "purpose_narration": "Invalid self-guaranteed loan",
        "product_id": 1,
        "guarantors": [
            {
                "guarantor_member_id": borrower_id, # Self guarantor!
                "guaranteed_amount": 30000.0
            }
        ]
    }
    res = requests.post(
        f"{BASE_URL}/members/{borrower_id}/loans",
        json=invalid_payload,
        headers=borrower_headers
    )
    assert_true(res.status_code == 400, "Self-guarantor loan submission rejected with 400 Bad Request")
    print(f"Expected Error Message Received: {res.json().get('detail')}")

    # 7. Verify Executive Review Pipeline with Attached Guarantor Savings Details
    print_step("7. Verifying Executive Review Queue (GET /api/admin/loans/pending-review)")
    res = requests.get(f"{BASE_URL}/admin/loans/pending-review", headers=pres_headers)
    assert_true(res.status_code == 200, "Executive pending loans fetched successfully")
    exec_loans = res.json().get("data", [])
    
    target_loan = next((l for l in exec_loans if l["id"] == loan_id), None)
    assert_true(target_loan is not None, f"Submitted loan {loan_ref} found in executive review queue")
    assert_true("guarantors" in target_loan, "Loan includes attached guarantors list")
    
    attached_guars = target_loan["guarantors"]
    assert_true(len(attached_guars) >= 1, f"Found {len(attached_guars)} guarantors for loan {loan_ref}")
    
    for g in attached_guars:
        assert_true("total_savings" in g, f"Guarantor {g['first_name']} {g['last_name']} has total_savings field")
        assert_true("guaranteed_amount" in g, f"Guarantor {g['first_name']} {g['last_name']} has guaranteed_amount field")
        assert_true("is_adequate" in g, f"Guarantor {g['first_name']} {g['last_name']} has adequacy calculation")
        print(f" -> Guarantor {g['first_name']} {g['last_name']} ({g['member_code']}): "
              f"Total Savings: NGN {g['total_savings']:,.2f}, Guaranteed: NGN {g['guaranteed_amount']:,.2f}, Adequate: {g['is_adequate']}")

    # 8. Verify Presidential Superior Override to 100% Direct Disbursement
    print_step("8. Executing Presidential Superior Override Review")
    rev_res = requests.post(f"{BASE_URL}/admin/loans/{loan_id}/review", json={
        "action": "APPROVE",
        "comments": "Approved with verified peer co-signers per Article 14 Bye-Laws.",
        "is_president_override": True
    }, headers=pres_headers)
    assert_true(rev_res.status_code == 200, f"Presidential override executed: {rev_res.text}")

    # 9. Verify Borrower View
    print_step("9. Verifying Borrower View (GET /api/members/{borrower_id}/loans)")
    res = requests.get(f"{BASE_URL}/members/{borrower_id}/loans", headers=borrower_headers)
    assert_true(res.status_code == 200, "Borrower loans statement retrieved")
    b_loans = res.json().get("data", [])
    updated_loan = next((l for l in b_loans if l["id"] == loan_id), None)
    assert_true(updated_loan is not None, "Updated loan present in borrower view")
    assert_true(updated_loan["approval_level_percent"] == 100, f"Approval level is 100% (got {updated_loan['approval_level_percent']}%)")
    assert_true(updated_loan["status"] == "ACTIVE", f"Status is ACTIVE (got {updated_loan['status']})")
    assert_true("guarantors" in updated_loan, "Borrower view contains guarantor reference")

    print("\n" + "=" * 70)
    print(" ALL GUARANTOR & STATUTORY LOAN PRODUCT VERIFICATIONS PASSED 100%!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
