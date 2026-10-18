import os
import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal
import requests

BASE_URL = "http://127.0.0.1:8088/api"

class TestOperationalPoliciesAndEscalations(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from wbmf_db import WealthbridgeDB
        cls.db = WealthbridgeDB()

        # Login as President
        cls.pres_session = requests.Session()
        res = cls.pres_session.post(f"{BASE_URL}/auth/login", json={
            "identifier": "WMC-2026-001",
            "password": "Wealthbridge@2026"
        })
        assert res.status_code == 200, f"President login failed: {res.text}"
        data = res.json()
        cls.pres_token = data["token"]
        cls.pres_session.headers.update({"Authorization": f"Bearer {cls.pres_token}"})

        # Login as Cooperator Member 2
        cls.mem_session = requests.Session()
        res = cls.mem_session.post(f"{BASE_URL}/auth/login", json={
            "identifier": "WMC-2026-002",
            "password": "Wealthbridge@2026"
        })
        assert res.status_code == 200, f"Member 2 login failed: {res.text}"
        data = res.json()
        cls.mem_token = data["token"]
        cls.mem_session.headers.update({"Authorization": f"Bearer {cls.mem_token}"})

    def test_01_exit_settlement_cooling_off_notification(self):
        """Decision 5: Exit notice computes 30-day cooling off and notifies expected payout date."""
        conn = self.db.get_connection()
        c = conn.cursor(dictionary=True)
        c.execute("DELETE FROM member_exits WHERE member_id = 2;")
        conn.commit()
        c.close()
        conn.close()

        res = self.mem_session.post(f"{BASE_URL}/members/2/exit-request", json={
            "exit_type": "VOLUNTARY_WITHDRAWAL",
            "reason": "Relocation to another municipality for family reasons."
        })
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["cooling_off_days"], 30)
        self.assertIn("expected_payout_date", data)
        self.assertIn("Statutory notice registered", data["message"])
        self.assertIn("expect liquidation payment on", data["message"])
        print(f"\n[PASS] Exit Request Cooling-Off Notification: {data['message']}")

    def test_02_arrears_auto_suspension_and_payment_allowance(self):
        """Decision 2: 3 unpaid advices auto-suspend member, but member can sign in and pay."""
        conn = self.db.get_connection()
        c = conn.cursor(dictionary=True)
        c.execute("DELETE FROM dividend_allocations WHERE member_id IN (SELECT id FROM members WHERE email = 'test_arrears@wealthbridge.ng');")
        c.execute("DELETE FROM payment_advices WHERE member_id IN (SELECT id FROM members WHERE email = 'test_arrears@wealthbridge.ng');")
        c.execute("DELETE FROM members WHERE email = 'test_arrears@wealthbridge.ng';")
        conn.commit()

        from wbmf_db import hash_password
        pwd_hash = hash_password("Wealthbridge@2026")

        c.execute("""
            INSERT INTO members (
                member_code, first_name, last_name, email, phone, gender,
                residential_address, identification_type, identification_number,
                employment_status, contribution_tier, status, kyc_completion_percent,
                admission_date, password_hash, created_at
            ) VALUES (
                'WMC-TEST-ARR', 'Tunde', 'Arrears', 'test_arrears@wealthbridge.ng', '08099887766',
                'MALE', 'Ikorodu Road, Lagos', 'NIN', '12345678901', 'SALARY_EARNER',
                'STANDARD', 'ACTIVE', 100, CURDATE(),
                %s, NOW()
            );
        """, (pwd_hash,))
        m_id = c.lastrowid
        conn.commit()

        # Generate 3 unpaid payment advices for prior months
        c.execute("""
            INSERT INTO payment_advices (advice_reference, member_id, billing_period, issue_date, due_date, tier_at_issuance, total_expected_amount, total_amount_paid, outstanding_balance, status)
            VALUES 
            ('WMC-ADV-TEST-01', %s, '2026-07', '2026-07-01', '2026-07-28', 'STANDARD', 15000.00, 0.00, 15000.00, 'DUE'),
            ('WMC-ADV-TEST-02', %s, '2026-08', '2026-08-01', '2026-08-28', 'STANDARD', 15000.00, 0.00, 15000.00, 'DUE'),
            ('WMC-ADV-TEST-03', %s, '2026-09', '2026-09-01', '2026-09-28', 'STANDARD', 15000.00, 0.00, 15000.00, 'DUE');
        """, (m_id, m_id, m_id))
        conn.commit()

        # Trigger advice generation for current month -> should auto-suspend
        self.db.generate_or_get_monthly_advice(m_id, "2026-10")

        c.execute("SELECT status FROM members WHERE id = %s;", (m_id,))
        updated_m = c.fetchone()
        self.assertEqual(updated_m["status"], "SUSPENDED")
        print(f"[PASS] Member automatically suspended after 3 unpaid billing cycles (Status: {updated_m['status']})")
        c.close()
        conn.close()

        # Verify SUSPENDED member CAN sign in
        res = requests.post(f"{BASE_URL}/auth/login", json={
            "identifier": "test_arrears@wealthbridge.ng",
            "password": "Wealthbridge@2026"
        })
        self.assertEqual(res.status_code, 200, f"Suspended member should still be able to sign in: {res.text}")
        data = res.json()
        self.assertEqual(data["user"]["membership_status"], "SUSPENDED")
        
        # Check login prompt returned for suspension
        prompts = data.get("login_prompts", [])
        susp_prompts = [p for p in prompts if p["type"] == "MEMBERSHIP_SUSPENDED"]
        self.assertTrue(len(susp_prompts) > 0, "Suspended member receives suspension warning prompt on login")
        print(f"[PASS] Suspended member successfully logged in and received notice: {susp_prompts[0]['title']}")

    def test_03_loan_default_escalation_schedule_and_prompts(self):
        """Decision 1: Overdue loans trigger notifications and prompts at 30, 45, and 90 days."""
        conn = self.db.get_connection()
        c = conn.cursor(dictionary=True)

        c.execute("DELETE FROM loan_repayments WHERE loan_id IN (SELECT id FROM loans WHERE member_id = 2 AND status = 'ACTIVE');")
        c.execute("""
            UPDATE loans 
            SET outstanding_balance = 80000.00, status = 'ACTIVE' 
            WHERE member_id = 2 
            ORDER BY id DESC LIMIT 1;
        """)
        c.execute("SELECT id FROM loans WHERE member_id = 2 AND status = 'ACTIVE' ORDER BY id DESC LIMIT 1;")
        l_row = c.fetchone()
        self.assertIsNotNone(l_row, "Active loan needed for test")
        loan_id = l_row["id"]

        # Backdate repayment installment to 50 days ago
        c.execute("""
            INSERT INTO loan_repayments (loan_id, installment_number, due_date, amount_due, amount_paid, status)
            VALUES (%s, 1, DATE_SUB(CURDATE(), INTERVAL 50 DAY), 15000.00, 0.00, 'OVERDUE');
        """, (loan_id,))
        
        # Attach member 1 as guarantor
        c.execute("""
            INSERT INTO loan_guarantors (loan_id, guarantor_member_id, guaranteed_amount, lien_encumbered_amount, status)
            VALUES (%s, 1, 40000.00, 40000.00, 'ACCEPTED')
            ON DUPLICATE KEY UPDATE status = 'ACCEPTED', guaranteed_amount = 40000.00, lien_encumbered_amount = 40000.00;
        """, (loan_id,))
        conn.commit()
        c.close()
        conn.close()

        # Run escalation scanner
        scan_res = self.db.scan_and_process_loan_defaults()
        self.assertEqual(scan_res["status"], "SUCCESS")
        print(f"[PASS] Default scanner processed: {scan_res}")

        # Check borrower login prompts (borrower is member 2)
        b_prompts = self.db.get_login_prompts_for_user(2, "WMC-2026-002", ["MEMBER"])
        default_p = [p for p in b_prompts if p["type"] == "LOAN_DEFAULT_BORROWER"]
        self.assertTrue(len(default_p) > 0, "Borrower receives persistent 45+ day default prompt")
        print(f"[PASS] Borrower Prompt (Day 50): {default_p[0]['title']} -> {default_p[0]['message'][:70]}...")

        # Check guarantor login prompts (guarantor is member 1)
        g_prompts = self.db.get_login_prompts_for_user(1, "WMC-2026-001", ["MEMBER"])
        guar_p = [p for p in g_prompts if p["type"] == "LOAN_DEFAULT_GUARANTOR"]
        self.assertTrue(len(guar_p) > 0, "Guarantor receives persistent 45+ day default alert")
        print(f"[PASS] Guarantor Prompt: {guar_p[0]['title']} -> {guar_p[0]['message'][:70]}...")

    def test_04_day_90_foreclosure_offset_desk(self):
        """Decision 1: Day 90 prompts FinSec & President to execute offset from borrower & guarantor savings."""
        conn = self.db.get_connection()
        c = conn.cursor(dictionary=True)

        c.execute("SELECT id FROM loans WHERE member_id = 2 AND status = 'ACTIVE' ORDER BY id DESC LIMIT 1;")
        loan_id = c.fetchone()["id"]

        # Backdate repayment installment to 95 days ago (Tier 3: >= 90 days default)
        c.execute("""
            UPDATE loan_repayments 
            SET due_date = DATE_SUB(CURDATE(), INTERVAL 95 DAY) 
            WHERE loan_id = %s;
        """, (loan_id,))

        # Attach member 1 as guarantor with 40,000 guaranteed
        c.execute("""
            INSERT INTO loan_guarantors (loan_id, guarantor_member_id, guaranteed_amount, lien_encumbered_amount, status)
            VALUES (%s, 1, 40000.00, 40000.00, 'ACCEPTED')
            ON DUPLICATE KEY UPDATE status = 'ACCEPTED', guaranteed_amount = 40000.00, lien_encumbered_amount = 40000.00;
        """, (loan_id,))

        # Ensure borrower and guarantor have sufficient regular savings
        c.execute("""
            INSERT INTO savings_accounts (member_id, total_balance, encumbered_balance)
            VALUES (2, 50000.00, 0.00)
            ON DUPLICATE KEY UPDATE total_balance = GREATEST(total_balance, 50000.00);
        """)
        c.execute("""
            INSERT INTO savings_accounts (member_id, total_balance, encumbered_balance)
            VALUES (1, 100000.00, 40000.00)
            ON DUPLICATE KEY UPDATE total_balance = GREATEST(total_balance, 100000.00);
        """)
        conn.commit()
        c.close()
        conn.close()

        # Verify President gets 90-day action prompt
        exec_prompts = self.db.get_login_prompts_for_user(1, "WMC-2026-001", ["PRESIDENT", "SUPER_ADMIN"])
        foreclose_p = [p for p in exec_prompts if p["type"] == "LOAN_FORECLOSURE_ACTION_REQUIRED"]
        self.assertTrue(len(foreclose_p) > 0, "President & FinSec receive 90-day foreclosure action prompt")
        print(f"[PASS] Executive Foreclosure Prompt: {foreclose_p[0]['title']}")

        # Execute Foreclosure Offset via API:
        # Offset ₦30,000 from borrower savings + ₦20,000 from guarantor savings = ₦50,000
        res = self.pres_session.post(f"{BASE_URL}/admin/loans/{loan_id}/foreclosure-offset", json={
            "offset_borrower_amount": 30000.0,
            "offset_guarantor_amount": 20000.0,
            "officer_notes": "Statutory 90-day uncured default resolution approved by FinSec & President"
        })
        self.assertEqual(res.status_code, 200, res.text)
        fcl_data = res.json()
        self.assertEqual(fcl_data["status"], "SUCCESS")
        self.assertEqual(fcl_data["total_offset"], 50000.0)
        print(f"[PASS] Foreclosure Offset Executed: {fcl_data['message']}")

        # Verify General Ledger is in balanced equilibrium after foreclosure
        tb = self.db.get_trial_balance()
        self.assertTrue(tb["is_balanced"], f"Trial balance out of balance: {tb}")
        print(f"[PASS] Double-Entry GL remains balanced (Total Debits: NGN {tb['grand_total_debit']:,.2f} == Total Credits: NGN {tb['grand_total_credit']:,.2f})")

    def test_05_dividend_loan_patronage_rebate(self):
        """Decision 3: Dividend engine awards Loan Patronage Rebate to borrowing members."""
        sim = self.db.simulate_dividend_distribution(
            period_name="Test FY2026 Loan Patronage Distribution",
            financial_year_start="2025-10-01",
            financial_year_end="2026-09-30",
            net_surplus=500000.0,
            statutory_reserve_pct=50.0,
            weight_share_pct=50.0,
            weight_savings_pct=40.0,
            weight_patronage_pct=10.0,
            min_shares=5,
            min_months=0,
            disqualify_arrears=False
        )
        self.assertEqual(sim["weight_patronage_percent"], 10.0)
        self.assertGreater(sim["pool_allocations"]["patronage_pool"], 0.0)
        print(f"[PASS] Loan Patronage Rebate Pool: NGN {sim['pool_allocations']['patronage_pool']:,.2f} active and allocated across qualified borrowers!")

if __name__ == "__main__":
    unittest.main()
