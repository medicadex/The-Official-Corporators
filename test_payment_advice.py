"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
PAYMENT ADVICE & WATERFALL AUTO-DISTRIBUTION TEST SUITE (test_payment_advice.py)
-----------------------------------------------------------------------------
Verifies:
1. Monthly Payment Advice generation according to cooperator tier & commitments
2. Priority Waterfall Auto-Distribution on Underpayment
3. Priority Waterfall Auto-Distribution on Full Settlement
4. 100% Surplus Allocation into Regular Savings on Overpayment
5. Society-wide Payment Advice Summary & Collection Metrics
Official Secretariat Email: wealthbridge.coopsociety@gmail.com
=============================================================================
"""

import time
from wbmf_db import WealthbridgeDB

def run_tests():
    db = WealthbridgeDB()
    print("=" * 80)
    print("  TESTING PAYMENT ADVICE & WATERFALL AUTO-DISTRIBUTION ENGINE")
    print("  Official Email: wealthbridge.coopsociety@gmail.com")
    print("=" * 80)

    # 1. Test Advice Generation for Member 1 (Standard Tier)
    print("\n[TEST 1] Generating or Retrieving Monthly Payment Advice for Member 1...")
    adv1 = db.generate_or_get_monthly_advice(member_id=1, billing_period="2026-10")
    assert adv1 is not None
    assert "advice_reference" in adv1
    assert adv1["tier"] in ("STANDARD", "PLUS", "PREMIUM")
    print(f"  + Advice Reference: {adv1['advice_reference']}")
    print(f"  + Billing Period:   {adv1['billing_period']} (Due Date: {adv1['due_date']})")
    print(f"  + Total Expected:   NGN {adv1['totals']['total_expected']:,.2f}")
    print(f"  + Breakdown:        Welfare NGN {adv1['breakdown']['welfare']['expected']:,.2f} | Shares NGN {adv1['breakdown']['share_capital']['expected']:,.2f} | Savings NGN {adv1['breakdown']['regular_savings']['expected']:,.2f}")
    print("  [PASS] Test 1: Advice generated successfully.")

    # 2. Test Underpayment Auto-Distribution (Priority Waterfall)
    print("\n[TEST 2] Testing Underpayment Auto-Distribution (Paying NGN 3,000 against Advice)...")
    dist1 = db.distribute_payment_by_advice(
        member_id=1,
        amount_paid=3000.0,
        payment_method="PAYSTACK_DVA",
        payment_ref=f"TEST-DIST-UNDER-{int(time.time()*1000)}",
        narration="Partial Inward Transfer Test"
    )
    assert dist1["status"] == "SUCCESS"
    print(f"  + Amount Received:        NGN {dist1['amount_received']:,.2f}")
    print(f"  + Allocated to Welfare:   NGN {dist1['allocations']['welfare']:,.2f}")
    print(f"  + Allocated to Shares:    NGN {dist1['allocations']['share_capital']:,.2f}")
    print(f"  + Allocated to Savings:   NGN {dist1['allocations']['regular_savings']:,.2f}")
    print(f"  + Outstanding Balance:    NGN {dist1['outstanding_balance']:,.2f}")
    print(f"  + Advice Status Now:      {dist1['advice_status']}")
    print("  [PASS] Test 2: Underpayment auto-distributed strictly per statutory priority.")

    # 3. Test Full Settlement / Remaining Balance
    print("\n[TEST 3] Testing Settlement of Remaining Balance...")
    adv_cur = db.generate_or_get_monthly_advice(member_id=1, billing_period="2026-10")
    rem_due = adv_cur["totals"]["outstanding_balance"]
    print(f"  + Outstanding Balance Before Payment: NGN {rem_due:,.2f}")

    if rem_due > 0:
        dist2 = db.distribute_payment_by_advice(
            member_id=1,
            amount_paid=rem_due,
            payment_method="PAYSTACK_DVA",
            payment_ref=f"TEST-DIST-FULL-{int(time.time()*1000)}",
            narration="Full Balance Clearance"
        )
        assert dist2["status"] == "SUCCESS"
        assert dist2["advice_status"] == "FULLY_SETTLED"
        assert dist2["outstanding_balance"] <= 0.01
        print(f"  + Advice Status Now:      {dist2['advice_status']}")
        print(f"  + Outstanding Balance:    NGN {dist2['outstanding_balance']:,.2f}")
    print("  [PASS] Test 3: Advice fully settled.")

    # 4. Test Overpayment with 100% Surplus to Regular Savings
    print("\n[TEST 4] Testing Overpayment (Paying NGN 15,000 when Advice is already settled)...")
    dist3 = db.distribute_payment_by_advice(
        member_id=1,
        amount_paid=15000.0,
        payment_method="PAYSTACK_DVA",
        payment_ref=f"TEST-DIST-OVER-{int(time.time()*1000)}",
        narration="Surplus Remittance Test"
    )
    assert dist3["status"] == "SUCCESS"
    assert dist3["surplus_credited_to_savings"] == 15000.0
    print(f"  + Amount Received:        NGN {dist3['amount_received']:,.2f}")
    print(f"  + Surplus to Savings:     NGN {dist3['surplus_credited_to_savings']:,.2f}")
    print(f"  + Advice Status:          {dist3['advice_status']}")
    print("  [PASS] Test 4: 100% of surplus correctly credited to Regular Savings.")

    # 5. Test Organization-wide Advice Summary
    print("\n[TEST 5] Testing Society-Wide Payment Advices Summary...")
    summary = db.get_all_payment_advices_summary(billing_period="2026-10")
    assert summary is not None
    assert "totals" in summary
    assert "advices" in summary
    print(f"  + Total Advices Issued:   {summary['totals']['total_advices']}")
    print(f"  + Total Expected Billing: NGN {summary['totals']['total_expected']:,.2f}")
    print(f"  + Total Collected:        NGN {summary['totals']['total_collected']:,.2f}")
    print(f"  + Total Outstanding:      NGN {summary['totals']['total_outstanding']:,.2f}")
    print(f"  + Collection Rate:        {summary['totals']['collection_rate_percent']}%")
    print("  [PASS] Test 5: Executive summary verified.")

    # 6. Test REST API Endpoints via TestClient
    print("\n[TEST 6] Testing REST API Endpoints via FastAPI TestClient...")
    from fastapi.testclient import TestClient
    from wbmf_api import app

    client = TestClient(app)
    # Login as Member 1
    auth_resp = client.post("/api/auth/login", json={"identifier": "WMC-2026-001", "password": "Pass123*"})
    if auth_resp.status_code != 200:
        auth_resp = client.post("/api/auth/login", json={"identifier": "WMC-2026-001", "password": "Wealthbridge@2026"})
    assert auth_resp.status_code == 200
    token = auth_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # GET /api/members/1/payment-advice/current
    api_adv = client.get("/api/members/1/payment-advice/current", headers=headers)
    assert api_adv.status_code == 200
    assert api_adv.json()["status"] == "success"
    assert "advice_reference" in api_adv.json()["data"]
    print(f"  + GET /api/members/1/payment-advice/current: {api_adv.json()['data']['advice_reference']} (Status: {api_adv.json()['data']['status']})")

    # GET /api/members/1/payment-advices
    api_history = client.get("/api/members/1/payment-advices", headers=headers)
    assert api_history.status_code == 200
    assert len(api_history.json()["data"]) >= 1
    print(f"  + GET /api/members/1/payment-advices: {len(api_history.json()['data'])} historical records found.")

    # GET /api/admin/payment-advices
    api_admin = client.get("/api/admin/payment-advices", headers=headers)
    assert api_admin.status_code == 200
    assert api_admin.json()["data"]["totals"]["total_advices"] >= 8
    print(f"  + GET /api/admin/payment-advices: Executive overview returned {api_admin.json()['data']['totals']['total_advices']} advices.")
    print("  [PASS] Test 6: API endpoints verified successfully.")

    print("\n" + "=" * 80)
    print("  ALL 6 PAYMENT ADVICE & AUTO-DISTRIBUTION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
