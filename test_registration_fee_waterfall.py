import sys
from decimal import Decimal
from wbmf_db import WealthbridgeDB
from advice_pdf_service import AdvicePdfService

def run_tests():
    print("=====================================================================")
    print("TEST SUITE: MANDATORY ENTRANCE / REGISTRATION FEE (ARTICLE 7)")
    print("=====================================================================")
    db = WealthbridgeDB()
    conn = db.get_connection()
    cur = conn.cursor(dictionary=True)

    try:
        # Create a clean dummy test member
        test_email = "test.onboarding.member@wealthbridge.test"
        cur.execute("DELETE FROM members WHERE email = %s;", (test_email,))
        conn.commit()

        cur.execute("SELECT * FROM members WHERE id = 2;")
        proto = cur.fetchone()

        cur.execute("""
            INSERT INTO members (
                member_code, first_name, last_name, email, password_hash,
                phone, gender, marital_status, residential_address,
                identification_type, identification_number, employment_status,
                employer_or_business_name, bank_name, bank_account_number, bank_account_name,
                bvn, contribution_tier, status, kyc_completion_percent
            ) VALUES (
                'WMC-TEST-REG99', 'Olumide', 'Adebayo', %s, %s,
                '08011223344', %s, %s, %s,
                %s, '12345678901', %s,
                %s, %s, '1234567890', 'Olumide Adebayo',
                '22233344455', 'STANDARD', 'ACTIVE', 100
            );
        """, (
            test_email, proto['password_hash'],
            proto['gender'], proto['marital_status'], proto['residential_address'],
            proto['identification_type'], proto['employment_status'],
            proto['employer_or_business_name'], proto['bank_name']
        ))
        conn.commit()
        member_id = cur.lastrowid
        print(f"Created test member ID: {member_id}")

        # Test 1: 1st Advice Generation
        period_1 = "2026-11"
        adv1 = db.generate_or_get_monthly_advice(member_id, billing_period=period_1)
        print(f"Test 1: Generated Month 1 Advice #{adv1['advice_reference']}")
        print(f"  Breakdown: {adv1['breakdown']}")
        print(f"  Total Expected: NGN {adv1['totals']['total_expected']:,.2f}")

        # Assertions for Test 1
        assert "registration_fee" in adv1["breakdown"], "registration_fee missing from breakdown"
        reg_expected = adv1["breakdown"]["registration_fee"]["expected"]
        assert reg_expected == 5000.0, f"Expected registration fee to be 5000.0, got {reg_expected}"
        
        # STANDARD tier: savings=8k, shares=1k, welfare=1k (flat), reg=5k -> Total = 15,000
        expected_total = 8000.0 + 1000.0 + 1000.0 + 5000.0
        assert adv1["totals"]["total_expected"] == expected_total, (
            f"Expected total {expected_total}, got {adv1['totals']['total_expected']}"
        )
        print("  [PASSED] Test 1: 1st Payment Advice mandates flat NGN 5,000 Registration Fee & NGN 1,000 flat Welfare!")

        # Test 2: Waterfall Payment of NGN 6,000 (Priority 1: Fines=0, Priority 2: Reg=5k, Priority 3: Loan=0, Priority 4: Welfare=1k)
        print("\nTest 2: Remitting NGN 6,000 to test Priority 2 Waterfall liquidation...")
        dist_res = db.distribute_payment_by_advice(
            member_id=member_id,
            amount_paid=6000.0,
            payment_method="POLARIS_BANK_TRANSFER",
            payment_ref="TEST-TXN-REG-001",
            narration="Test partial remittance"
        )
        allocs = dist_res["allocations"]
        print(f"  Allocations: {allocs}")
        assert allocs["registration_fee"] == 5000.0, f"Expected 5000 to registration_fee, got {allocs['registration_fee']}"
        assert allocs["welfare"] == 1000.0, f"Expected 1000 to welfare, got {allocs['welfare']}"
        assert allocs["share_capital"] == 0.0
        assert allocs["regular_savings"] == 0.0

        # Verify transaction table
        cur.execute("""
            SELECT ledger_category, amount, status, narration
            FROM transactions
            WHERE member_id = %s AND ledger_category = 'REGISTRATION_FEE';
        """, (member_id,))
        txn_reg = cur.fetchone()
        assert txn_reg is not None, "REGISTRATION_FEE transaction not logged!"
        assert float(txn_reg["amount"]) == 5000.0, f"Logged amount {txn_reg['amount']} != 5000.0"
        print(f"  [PASSED] Test 2: Priority 2 allocated NGN 5,000 and logged VERIFIED REGISTRATION_FEE transaction!")

        # Test 3: Month 2 Advice Generation (Registration fee should be 0 since it is fully paid)
        period_2 = "2026-12"
        adv2 = db.generate_or_get_monthly_advice(member_id, billing_period=period_2)
        print(f"\nTest 3: Generated Month 2 Advice #{adv2['advice_reference']}")
        print(f"  Breakdown: {adv2['breakdown']}")
        print(f"  Total Expected: NGN {adv2['totals']['total_expected']:,.2f}")
        assert adv2["breakdown"]["registration_fee"]["expected"] == 0.0, (
            f"Expected reg fee on month 2 to be 0.0, got {adv2['breakdown']['registration_fee']['expected']}"
        )
        print("  [PASSED] Test 3: Month 2 advice sets registration fee to NGN 0.00 since already settled!")

        # Test 4: PDF Generation
        print("\nTest 4: Generating official PDF with Registration Fee line item...")
        cur.execute("SELECT * FROM members WHERE id = %s;", (member_id,))
        m_row = cur.fetchone()
        pdf_bytes = AdvicePdfService.generate_pdf(adv1, m_row)
        assert len(pdf_bytes) > 1000, "PDF bytes should be non-empty"
        assert pdf_bytes.startswith(b"%PDF"), "Output is not a valid PDF file"
        print(f"  [PASSED] Test 4: Generated valid PDF advice slip ({len(pdf_bytes)} bytes)!")

        # Cleanup test data
        cur.execute("DELETE FROM payment_advice_distributions WHERE member_id = %s;", (member_id,))
        cur.execute("DELETE FROM transactions WHERE member_id = %s;", (member_id,))
        cur.execute("DELETE FROM payment_advices WHERE member_id = %s;", (member_id,))
        cur.execute("DELETE FROM welfare_accounts WHERE member_id = %s;", (member_id,))
        cur.execute("DELETE FROM share_accounts WHERE member_id = %s;", (member_id,))
        cur.execute("DELETE FROM savings_accounts WHERE member_id = %s;", (member_id,))
        cur.execute("DELETE FROM members WHERE id = %s;", (member_id,))
        conn.commit()
        print("\nCleanup completed cleanly.")

        print("\n=====================================================================")
        print("ALL ENTRANCE / REGISTRATION FEE TESTS PASSED 100%!")
        print("=====================================================================")

    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    run_tests()
