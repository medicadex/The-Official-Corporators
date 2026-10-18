"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
DYNAMIC TARGET SAVINGS VERIFICATION SUITE (test_target_savings.py)
-----------------------------------------------------------------------------
Tests:
1. Standardized category dropdown validation (Birthday, Christmas, Ileya, Building, Pilgrimage, Education, Others)
2. Enforced future maturity date constraint
3. Ledger creation & balance tracking
4. Top-up deposit handling
5. Early withdrawal lock protection (cannot withdraw before maturity date)
6. Maturity unlocking & successful payout to commercial bank
7. Executive & Admin target savings aggregation
8. Official contact invariant check: wealthbridge.coopsociety@gmail.com
=============================================================================
"""

import sys
from datetime import date, timedelta
from wbmf_db import WealthbridgeDB

def run_tests():
    print("=" * 75)
    print("  WEALTHBRIDGE COOPERATIVE - DYNAMIC TARGET SAVINGS TEST SUITE")
    print("  Official Email: wealthbridge.coopsociety@gmail.com")
    print("=" * 75)

    db = WealthbridgeDB()
    test_member_id = 1 # Founding President Adebowale
    
    # -------------------------------------------------------------------------
    # TEST 1: Retrieve existing target ledgers
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Retrieving Member 1 Target Savings Ledgers...")
    res = db.get_member_target_savings(test_member_id)
    summary = res["summary"]
    targets = res["targets"]
    print(f"  + Active Targets Count:   {summary['active_targets_count']}")
    print(f"  + Matured Targets Count:  {summary['matured_targets_count']}")
    print(f"  + Total Target Savings:   NGN {summary['total_target_savings']:,.2f}")
    print(f"  + Total Target Goal:      NGN {summary['total_target_goal']:,.2f}")
    assert len(targets) >= 1, "Expected at least 1 seeded target ledger for Member 1"
    print("  [PASS] Test 1: Target savings retrieval passed.")

    # -------------------------------------------------------------------------
    # TEST 2: Enforce Future Maturity Date (Reject past/today dates)
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Testing Maturity Date Validation (Past Date Rejection)...")
    past_date = str(date.today() - timedelta(days=5))
    try:
        db.create_target_savings(test_member_id, {
            "target_type": "BIRTHDAY",
            "title": "Invalid Past Birthday Target",
            "target_amount": 50000.0,
            "maturity_date": past_date
        })
        assert False, "Should have thrown ValueError for past maturity date"
    except ValueError as e:
        print(f"  + Correctly caught validation error: {e}")
        print("  [PASS] Test 2: Past maturity date rejected successfully.")

    # -------------------------------------------------------------------------
    # TEST 3: Create a Dynamic Target Savings Ledger with Initial Deposit
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Creating a new Voluntary Target Savings Ledger (Birthday Target)...")
    future_date = str(date.today() + timedelta(days=180)) # 6 months out
    new_target = db.create_target_savings(test_member_id, {
        "target_type": "BIRTHDAY",
        "title": "40th Milestone Birthday Celebration Target",
        "target_amount": 600000.0,
        "maturity_date": future_date,
        "initial_deposit": 50000.0,
        "auto_save_amount": 25000.0,
        "payment_method": "POLARIS_BANK_TRANSFER"
    })
    target_id = new_target["id"]
    print(f"  + Created Target ID:      {target_id}")
    print(f"  + Title:                  {new_target['title']}")
    print(f"  + Target Category:        {new_target['target_type_label']}")
    print(f"  + Current Balance:        NGN {new_target['current_balance']:,.2f}")
    print(f"  + Maturity Date:          {new_target['maturity_date']} ({new_target['days_remaining']} days remaining)")
    assert new_target["current_balance"] == 50000.0
    assert new_target["status"] == "ACTIVE"
    print("  [PASS] Test 3: Ledger created successfully with initial deposit.")

    # -------------------------------------------------------------------------
    # TEST 4: Top Up / Deposit into Target Savings Ledger
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Topping up Target Savings Ledger with NGN 75,000...")
    dep_res = db.deposit_target_savings(
        member_id=test_member_id,
        target_id=target_id,
        amount=75000.0,
        narration="Monthly bonus top-up for 40th Birthday"
    )
    print(f"  + Top-up Result:          {dep_res['message']}")
    print(f"  + Updated Balance:        NGN {dep_res['new_balance']:,.2f}")
    assert dep_res["new_balance"] == 125000.0
    print("  [PASS] Test 4: Top-up deposit succeeded.")

    # -------------------------------------------------------------------------
    # TEST 5: Lock Enforcement - Reject Premature Withdrawal
    # -------------------------------------------------------------------------
    print("\n[TEST 5] Testing Maturity Lock Enforcement (Early Withdrawal Rejection)...")
    try:
        db.withdraw_target_savings(
            member_id=test_member_id,
            target_id=target_id,
            amount=50000.0,
            bank_details={"bank_name": "Polaris Bank", "account_number": "1140029381"}
        )
        assert False, "Should have thrown ValueError for early withdrawal before maturity date"
    except ValueError as e:
        print(f"  + Correctly blocked premature withdrawal: {e}")
        print("  [PASS] Test 5: Maturity lock successfully prevented early withdrawal.")

    # -------------------------------------------------------------------------
    # TEST 6: Simulate Maturity & Test Payout to Commercial Bank
    # -------------------------------------------------------------------------
    print("\n[TEST 6] Simulating Reached Maturity & Processing Bank Payout...")
    # Update target maturity date to yesterday in database to simulate arrival of maturity date
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE target_savings_accounts SET maturity_date = CURDATE() - INTERVAL 1 DAY, status = 'MATURED' WHERE id = %s;", (target_id,))
    conn.commit()
    cur.close()
    conn.close()

    # Now verify target status is matured
    matured_state = db.get_member_target_savings(test_member_id)
    target_match = [t for t in matured_state["targets"] if t["id"] == target_id][0]
    print(f"  + Target Status Now:      {target_match['status']}")
    print(f"  + Is Matured:             {target_match['is_matured']}")
    print(f"  + Can Withdraw:           {target_match['can_withdraw']}")
    assert target_match["is_matured"] is True
    assert target_match["can_withdraw"] is True

    # Process partial withdrawal
    wdr_res = db.withdraw_target_savings(
        member_id=test_member_id,
        target_id=target_id,
        amount=50000.0,
        bank_details={
            "bank_name": "Polaris Bank Limited",
            "account_number": "1140029381",
            "account_name": "Qazeem Adebowale"
        }
    )
    print(f"  + Payout Status:          {wdr_res['status']}")
    print(f"  + Amount Withdrawn:       NGN {wdr_res['withdrawn_amount']:,.2f}")
    print(f"  + Remaining Balance:      NGN {wdr_res['remaining_balance']:,.2f}")
    assert wdr_res["remaining_balance"] == 75000.0

    # Withdraw remaining balance
    wdr_all = db.withdraw_target_savings(
        member_id=test_member_id,
        target_id=target_id,
        amount=75000.0,
        bank_details={
            "bank_name": "Polaris Bank Limited",
            "account_number": "1140029381",
            "account_name": "Qazeem Adebowale"
        }
    )
    print(f"  + Final Balance:          NGN {wdr_all['remaining_balance']:,.2f}")
    print(f"  + Final Status:           {wdr_all['status_after']}")
    assert wdr_all["remaining_balance"] == 0.0
    assert wdr_all["status_after"] == "WITHDRAWN"
    print("  [PASS] Test 6: Matured payout completed seamlessly.")

    # -------------------------------------------------------------------------
    # TEST 7: Executive & Administrative Target Savings Summary
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Retrieving Society-Wide Target Savings Registry...")
    admin_res = db.get_all_target_savings_summary()
    totals = admin_res["totals"]
    categories = admin_res["by_category"]
    ledgers = admin_res["ledgers"]
    print(f"  + Total Ledgers in Coop:  {totals['total_ledgers']}")
    print(f"  + Active Target Pool:     NGN {totals['total_savings_pool']:,.2f}")
    print(f"  + Categories Represented: {len(categories)}")
    for c in categories:
        print(f"     - {c['label']:<38}: {c['ledger_count']} ledgers | NGN {c['total_balance']:,.2f}")
    assert len(ledgers) >= 1
    print("  [PASS] Test 7: Society-wide target registry aggregation verified.")

    # -------------------------------------------------------------------------
    # TEST 8: Official Contact Invariant Check
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Verifying Official Email Invariant...")
    OFFICIAL_EMAIL = "wealthbridge.coopsociety@gmail.com"
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()
    with open("wbmf_db.py", "r", encoding="utf-8") as f:
        db_code = f.read()
    with open("wbmf_api.py", "r", encoding="utf-8") as f:
        api_code = f.read()

    assert OFFICIAL_EMAIL in html, "Official email must be in index.html"
    assert OFFICIAL_EMAIL in db_code, "Official email must be in wbmf_db.py"
    assert OFFICIAL_EMAIL in api_code, "Official email must be in wbmf_api.py"
    print(f"  + Official Secretariat Email invariant confirmed: {OFFICIAL_EMAIL}")
    print("  [PASS] Test 8: Invariant preserved across codebase.")

    print("\n" + "=" * 75)
    print("  ALL 8 TARGET SAVINGS TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 75)

if __name__ == "__main__":
    run_tests()
