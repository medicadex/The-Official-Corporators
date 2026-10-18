"""
test_accounting_and_dividends_engine.py
======================================
Automated Verification Suite for:
- Module 4: Accounting & Financial Control (Double-Entry General Ledger, Chart of Accounts, Trial Balance, Income & Expenditure, Balance Sheet, Maker-Checker Manual Journals)
- Module 5: Dividend & Surplus Annual Distribution Engine (Dynamic Parameters, Qualified Denominators, Payout Preferences, General Ledger Posting)
"""

import sys
import unittest
from decimal import Decimal
from datetime import date, datetime
from wbmf_db import WealthbridgeDB

class TestAccountingAndDividendsEngine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = WealthbridgeDB()
        # Ensure historical sync has run
        sync_res = cls.db.sync_transactions_to_general_ledger()
        print(f"\n[SETUP] Synced {sync_res.get('synced_transactions_count', 0)} historical transactions to General Ledger.")

    def test_01_chart_of_accounts_structure_and_balances(self):
        """Validates that standard Chart of Accounts contains all statutory categories with live balances."""
        accounts = self.db.get_chart_of_accounts()
        self.assertGreaterEqual(len(accounts), 20, "Should have at least 20 statutory accounts in COA")
        
        account_types = {a["account_type"] for a in accounts}
        self.assertIn("ASSET", account_types)
        self.assertIn("LIABILITY", account_types)
        self.assertIn("EQUITY", account_types)
        self.assertIn("INCOME", account_types)
        self.assertIn("EXPENSE", account_types)

        # Check Polaris Escrow (1010) and Savings (2010) exist
        acc_1010 = next((a for a in accounts if a["account_code"] == "1010"), None)
        self.assertIsNotNone(acc_1010, "Account 1010 (Polaris Escrow) must exist")
        self.assertEqual(acc_1010["account_type"], "ASSET")

        acc_2010 = next((a for a in accounts if a["account_code"] == "2010"), None)
        self.assertIsNotNone(acc_2010, "Account 2010 (Regular Savings) must exist")
        self.assertEqual(acc_2010["account_type"], "LIABILITY")

    def test_02_double_entry_balance_enforcement(self):
        """Verifies that unbalanced journal entries are strictly rejected while balanced entries post cleanly."""
        # 1. Unbalanced entry test (Dr 50,000, Cr 40,000 -> Should raise ValueError)
        unbalanced_lines = [
            {"account_code": "1010", "line_type": "DEBIT", "amount": 50000.00, "memo": "Escrow debit"},
            {"account_code": "2010", "line_type": "CREDIT", "amount": 40000.00, "memo": "Savings credit unbalanced"}
        ]
        with self.assertRaises(ValueError) as ctx:
            self.db.post_journal_entry(
                entry_date=date.today(),
                source_module="MANUAL_JOURNAL",
                source_reference="TEST-UNBALANCED",
                narration="Unbalanced test entry",
                lines=unbalanced_lines,
                created_by=1,
                status="POSTED"
            )
        self.assertIn("not balanced", str(ctx.exception))

        # 2. Balanced entry test (Dr 25,000, Cr 25,000 -> Should succeed)
        balanced_lines = [
            {"account_code": "1010", "line_type": "DEBIT", "amount": 25000.00, "memo": "Polaris Escrow deposit"},
            {"account_code": "4060", "line_type": "CREDIT", "amount": 25000.00, "memo": "Sundry operational donation"}
        ]
        res = self.db.post_journal_entry(
            entry_date=date.today(),
            source_module="MANUAL_JOURNAL",
            source_reference=f"TEST-BAL-{int(datetime.now().timestamp())}",
            narration="Balanced test journal entry",
            lines=balanced_lines,
            created_by=1,
            status="POSTED"
        )
        self.assertEqual(res["status"], "POSTED")
        self.assertTrue(res["is_balanced"])
        self.assertEqual(res["total_debit"], 25000.00)
        self.assertEqual(res["total_credit"], 25000.00)

    def test_03_trial_balance_equality(self):
        """Verifies that the cooperative Trial Balance adheres strictly to Debits == Credits."""
        tb = self.db.get_trial_balance()
        self.assertTrue(tb["is_balanced"], f"Trial Balance must be balanced. Dr: {tb['grand_total_debit']}, Cr: {tb['grand_total_credit']}")
        self.assertAlmostEqual(tb["grand_total_debit"], tb["grand_total_credit"], delta=0.01)
        self.assertGreater(len(tb["accounts"]), 0, "Trial balance should contain active accounts")

    def test_04_income_and_expenditure_and_statutory_reserve(self):
        """Verifies Statement of Comprehensive Income and mandatory 50% statutory reserve calculation."""
        ie = self.db.get_income_and_expenditure()
        self.assertIn("total_income", ie)
        self.assertIn("total_expenditure", ie)
        self.assertIn("net_surplus", ie)
        self.assertIn("statutory_reserve_50pct", ie)
        
        # Verify 50% statutory reserve deduction (Cap C15 & Article 24)
        expected_reserve = round(max(0.0, ie["net_surplus"] * 0.50), 2)
        self.assertEqual(ie["statutory_reserve_50pct"], expected_reserve)
        self.assertEqual(ie["distributable_surplus_max"], round(max(0.0, ie["net_surplus"] - expected_reserve), 2))

    def test_05_balance_sheet_accounting_equation(self):
        """Verifies Statement of Financial Position satisfies Assets == Liabilities + Equity."""
        bs = self.db.get_balance_sheet()
        self.assertTrue(bs["is_balanced"], f"Balance sheet equation failed: Total Assets ({bs['total_assets']}) != Liab + Eq ({bs['total_liabilities_and_equity']})")
        self.assertAlmostEqual(bs["total_assets"], bs["total_liabilities_and_equity"], delta=0.01)

    def test_06_maker_checker_manual_journal_workflow(self):
        """Verifies dual-control Maker-Checker workflow: FinSec drafts (DRAFT), self-approval blocked, President approves (POSTED)."""
        draft_lines = [
            {"account_code": "5050", "line_type": "DEBIT", "amount": 15000.00, "memo": "Cloud Server maintenance fee"},
            {"account_code": "1010", "line_type": "CREDIT", "amount": 15000.00, "memo": "Payment from Polaris Bank Escrow"}
        ]
        
        # 1. Maker drafts entry (status: DRAFT)
        draft = self.db.submit_manual_journal_entry(
            entry_date=date.today(),
            narration="Monthly Cloud Database Hosting & Maintenance Invoice",
            lines=draft_lines,
            created_by=2, # FinSec user id 2
            supporting_doc_url="https://wmc-storage/vouchers/inv-hosting-2026.pdf"
        )
        self.assertEqual(draft["status"], "DRAFT")
        entry_id = draft["id"]

        # 2. Dual control violation: Creator cannot approve own draft (unless SUPER_ADMIN)
        with self.assertRaises(ValueError) as ctx:
            self.db.approve_manual_journal_entry(
                entry_id=entry_id,
                officer_id=2, # Same user as creator
                officer_role="FINANCIAL_SECRETARY",
                action="APPROVE"
            )
        self.assertIn("Dual-control governance violation", str(ctx.exception))

        # 3. Independent Checker approves (President / Super Admin)
        approved = self.db.approve_manual_journal_entry(
            entry_id=entry_id,
            officer_id=1, # President
            officer_role="PRESIDENT",
            action="APPROVE"
        )
        self.assertEqual(approved["status"], "SUCCESS")
        self.assertEqual(approved["new_status"], "POSTED")

        # Verify entry is now POSTED in General Ledger
        entries = self.db.get_journal_entries(status="POSTED", limit=10)
        found = next((e for e in entries if e["id"] == entry_id), None)
        self.assertIsNotNone(found)
        self.assertEqual(found["status"], "POSTED")
        self.assertEqual(found["approved_by"], 1)

    def test_07_dynamic_dividend_simulation_and_qualification_filtering(self):
        """Verifies dynamic dividend distribution engine: weights, qualification thresholds, denominator exclusions, and pro-rata member allocations."""
        sim = self.db.simulate_dividend_distribution(
            period_name="FY2026 Audit Distribution Simulation",
            financial_year_start="2025-10-01",
            financial_year_end="2026-09-30",
            net_surplus=2000000.00, # 2M surplus
            statutory_reserve_pct=50.00,
            weight_share_pct=60.00,
            weight_savings_pct=40.00,
            weight_patronage_pct=0.00,
            min_shares=5,
            min_months=0, # allow newly admitted test members
            disqualify_arrears=True
        )

        self.assertEqual(sim["net_surplus_amount"], 2000000.00)
        self.assertEqual(sim["statutory_reserve_amount"], 1000000.00)
        self.assertEqual(sim["distributable_pool_amount"], 1000000.00)
        self.assertEqual(sim["pool_allocations"]["shares_pool"] + sim["pool_allocations"]["savings_pool"], 1000000.00)

        # Check member allocations
        allocations = sim["allocations"]
        self.assertGreater(len(allocations), 0)

        qualified = [a for a in allocations if a["is_qualified"]]
        disqualified = [a for a in allocations if not a["is_qualified"]]
        
        self.assertGreater(len(qualified), 0, "Should have qualified members")
        for q in qualified:
            self.assertGreaterEqual(q["shares_held"], 5)
            self.assertGreater(q["total_dividend_payable"], 0.0)

        for dq in disqualified:
            self.assertEqual(dq["total_dividend_payable"], 0.0)
            self.assertIsNotNone(dq["disqualification_reason"])

        # Verify sum of member allocations equals total allocated pool (within 1 Naira rounding tolerance)
        total_member_dividends = sum(a["total_dividend_payable"] for a in allocations)
        self.assertAlmostEqual(total_member_dividends, sim["distributable_pool_amount"], delta=1.0)

    def test_08_dividend_period_save_and_presidential_signoff_posting(self):
        """Verifies saving dividend period to AUDIT_REVIEW and Presidential signoff posting to savings and double-entry General Ledger."""
        # 1. Run simulation
        sim = self.db.simulate_dividend_distribution(
            period_name="FY2026 Official Dividend Run",
            financial_year_start="2025-10-01",
            financial_year_end="2026-09-30",
            net_surplus=500000.00,
            statutory_reserve_pct=50.00,
            weight_share_pct=50.00,
            weight_savings_pct=50.00,
            weight_patronage_pct=0.00,
            min_shares=5,
            min_months=0,
            disqualify_arrears=True
        )

        # 2. Save dividend period
        save_res = self.db.save_dividend_period(sim, officer_id=1)
        self.assertEqual(save_res["status"], "SUCCESS")
        period_id = save_res["period_id"]

        # Verify period details retrieved
        details = self.db.get_dividend_period_details(period_id)
        self.assertEqual(details["status"], "AUDIT_REVIEW")
        self.assertEqual(len(details["allocations"]), len(sim["allocations"]))

        # 3. Check cooperator savings balance before approval
        m1_details = next((a for a in details["allocations"] if a["member_id"] == 1), None)
        conn = self.db.get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT total_balance FROM savings_accounts WHERE member_id = 1;")
        sav_before = float(cur.fetchone()["total_balance"])
        cur.close()
        conn.close()

        # 4. President approves and posts dividend
        post_res = self.db.approve_and_post_dividend(
            period_id=period_id,
            officer_id=1,
            officer_role="PRESIDENT"
        )
        self.assertEqual(post_res["status"], "SUCCESS")

        # 5. Verify savings account was credited
        conn = self.db.get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT total_balance FROM savings_accounts WHERE member_id = 1;")
        sav_after = float(cur.fetchone()["total_balance"])
        cur.close()
        conn.close()

        if m1_details and m1_details["is_qualified"]:
            expected_credit = m1_details["total_dividend_payable"]
            self.assertAlmostEqual(sav_after - sav_before, expected_credit, delta=0.01)

        # 6. Verify General Ledger journal entry was posted and is balanced
        entries = self.db.get_journal_entries(status="POSTED", limit=5)
        div_je = next((e for e in entries if e["source_module"] == "DIVIDEND_DISTRIBUTION" and str(period_id) in e["source_reference"]), None)
        self.assertIsNotNone(div_je, "Double-entry General Ledger entry must be posted for dividend distribution")
        self.assertTrue(div_je["is_balanced"], "Dividend GL journal entry must be balanced")

    def test_09_member_dividend_preference(self):
        """Verifies cooperator can update their dividend payout choice in their portal."""
        # Member 2 changes preference to BANK_TRANSFER
        upd = self.db.update_member_dividend_payout_preference(member_id=2, payout_preference="BANK_TRANSFER")
        self.assertEqual(upd["status"], "SUCCESS")
        self.assertEqual(upd["dividend_payout_preference"], "BANK_TRANSFER")

        # Reset to SAVINGS_CREDIT
        upd2 = self.db.update_member_dividend_payout_preference(member_id=2, payout_preference="SAVINGS_CREDIT")
        self.assertEqual(upd2["status"], "SUCCESS")
        self.assertEqual(upd2["dividend_payout_preference"], "SAVINGS_CREDIT")


if __name__ == "__main__":
    unittest.main()
