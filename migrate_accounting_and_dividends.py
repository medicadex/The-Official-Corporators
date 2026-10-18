"""
migrate_accounting_and_dividends.py
===================================
Database Schema Migration for:
- Module 4: Accounting and Financial Control (Chart of Accounts, Journal Entries, Double-Entry General Ledger)
- Module 5: Dividend & Surplus Distribution Engine (Dynamic Parameters, Allocation Denominators, Payout Preferences)
"""

from datetime import datetime, date
from wbmf_db import WealthbridgeDB

def run_migration():
    print("=" * 80)
    print("  WEALTHBRIDGE COOPERATIVE: MIGRATING ACCOUNTING & DIVIDENDS ENGINE")
    print("=" * 80)

    db = WealthbridgeDB()
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # 1. CHART OF ACCOUNTS TABLE
        print("\n[1] Creating chart_of_accounts table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chart_of_accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                account_code VARCHAR(16) UNIQUE NOT NULL,
                account_name VARCHAR(128) NOT NULL,
                account_type ENUM('ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE') NOT NULL,
                description VARCHAR(255) NULL,
                is_active BOOLEAN DEFAULT TRUE,
                is_system_controlled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Seed Standard Statutory Chart of Accounts (COA)
        standard_accounts = [
            # 1000 - ASSETS
            ('1010', 'Polaris Bank Current Escrow Account', 'ASSET', 'Primary commercial banking escrow partner for member deposits & payments', True),
            ('1020', 'Dedicated Virtual Accounts (DVA) Clearing', 'ASSET', 'Paystack automated incoming collection clearing pool', True),
            ('1030', 'Member Loan Facilities Receivable', 'ASSET', 'Outstanding loan principal receivables due from active borrowers', True),
            ('1040', 'Disciplinary Fines Receivable', 'ASSET', 'Outstanding disciplinary fines issued to members', True),

            # 2000 - LIABILITIES
            ('2010', 'Member Regular Savings Deposits', 'LIABILITY', 'Demand savings deposits held in trust for cooperators (2x borrowing collateral)', True),
            ('2020', 'Member Target Savings Deposits', 'LIABILITY', 'Fixed-goal target savings locked until stated maturity date', True),
            ('2030', 'Welfare Solidarity Pool', 'LIABILITY', 'Mutual aid solidarity reserve for medical, bereavement, and critical life events', True),
            ('2040', 'Unallocated Remittance Suspense', 'LIABILITY', 'Incoming payments awaiting reconciliation and waterfall allocation', True),

            # 3000 - EQUITY & CAPITAL
            ('3010', 'Member Paid-Up Share Capital', 'EQUITY', 'Cooperator equity units held at NGN 1,000 per unit (20% anti-monopoly ceiling)', True),
            ('3020', 'Statutory Reserve Fund (Cap C15)', 'EQUITY', 'Mandatory 50% statutory reserve accumulated from annual operational surplus', True),
            ('3030', 'Education & Cooperative Development Reserve', 'EQUITY', 'General and educational reserve allocated under Bye-Laws Article 24', True),
            ('3040', 'Retained Operating Surplus', 'EQUITY', 'Accumulated net surplus from cooperative operations carried forward', True),

            # 4000 - REVENUE / INCOME
            ('4010', 'Loan Administrative Cost-Recovery Fees', 'INCOME', 'Statutory 2.5% administrative cost-recovery fee on loan facilities', True),
            ('4020', 'Member Entrance & Registration Fees', 'INCOME', 'Statutory flat NGN 5,000 entrance fee collected from new members', True),
            ('4030', 'Passbook & Physical ID Card Issuance Fees', 'INCOME', 'Physical passbook and electronic ID card production fees', True),
            ('4040', 'Disciplinary Fines Collected', 'INCOME', 'Fines liquidated from disciplinary infractions under Bye-Laws Article 12', True),
            ('4050', 'Membership Exit Processing Fees', 'INCOME', 'Statutory NGN 5,000 administrative exit fee liquidated upon voluntary withdrawal', True),
            ('4060', 'Sundry & Incidental Income', 'INCOME', 'Miscellaneous operational receipts and donations', True),

            # 5000 - OPERATIONAL EXPENSES
            ('5010', 'Bank & Payment Gateway Processing Charges', 'EXPENSE', 'Polaris Bank and Paystack transaction/settlement fees', True),
            ('5020', 'Bereavement & Welfare Assistance Grants Paid', 'EXPENSE', 'Statutory NGN 100k bereavement grants and medical assistance disbursed', True),
            ('5030', 'Annual General Meeting & Governance Expenses', 'EXPENSE', 'Meeting packs, statutory AGM hosting, and election logistics', True),
            ('5040', 'Secretariat, Legal & Audit Retainer Fees', 'EXPENSE', 'Legal compliance, Lagos State regulatory dues, and external audit', True),
            ('5050', 'Technology Infrastructure & SMS Alerting', 'EXPENSE', 'Hosting, database maintenance, domain, and notification services', True),
        ]

        for acc in standard_accounts:
            cursor.execute("""
                INSERT INTO chart_of_accounts (account_code, account_name, account_type, description, is_system_controlled)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE account_name = VALUES(account_name), description = VALUES(description);
            """, acc)
        print(f"  + Seeded {len(standard_accounts)} Chart of Accounts entries.")

        # 2. JOURNAL ENTRIES & LINES (DOUBLE-ENTRY GENERAL LEDGER)
        print("\n[2] Creating journal_entries and journal_entry_lines tables...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INT AUTO_INCREMENT PRIMARY KEY,
                entry_number VARCHAR(64) UNIQUE NOT NULL,
                entry_date DATE NOT NULL,
                source_module ENUM('REMITTANCE_WATERFALL', 'LOAN_DISBURSEMENT', 'LOAN_REPAYMENT', 'EXIT_SETTLEMENT', 'WELFARE_PAYOUT', 'DIVIDEND_DISTRIBUTION', 'MANUAL_JOURNAL') NOT NULL,
                source_reference VARCHAR(128) NULL,
                narration TEXT NOT NULL,
                total_debit DECIMAL(15,2) NOT NULL,
                total_credit DECIMAL(15,2) NOT NULL,
                is_balanced BOOLEAN DEFAULT TRUE,
                status ENUM('DRAFT', 'POSTED', 'REJECTED') DEFAULT 'POSTED',
                created_by INT NULL,
                approved_by INT NULL,
                approved_at TIMESTAMP NULL,
                supporting_doc_url VARCHAR(255) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX (entry_date),
                INDEX (source_module),
                INDEX (status)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS journal_entry_lines (
                id INT AUTO_INCREMENT PRIMARY KEY,
                journal_entry_id INT NOT NULL,
                account_id INT NOT NULL,
                line_type ENUM('DEBIT', 'CREDIT') NOT NULL,
                amount DECIMAL(15,2) NOT NULL,
                memo VARCHAR(255) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (journal_entry_id) REFERENCES journal_entries(id) ON DELETE CASCADE,
                FOREIGN KEY (account_id) REFERENCES chart_of_accounts(id),
                INDEX (account_id),
                INDEX (line_type)
            );
        """)
        print("  + Created double-entry General Ledger structures.")

        # 3. DIVIDEND PERIODS & ALLOCATIONS ENGINE
        print("\n[3] Creating dividend_periods and dividend_allocations tables...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dividend_periods (
                id INT AUTO_INCREMENT PRIMARY KEY,
                period_name VARCHAR(64) NOT NULL,
                financial_year_start DATE NOT NULL,
                financial_year_end DATE NOT NULL,
                net_surplus_amount DECIMAL(15,2) NOT NULL,
                statutory_reserve_percent DECIMAL(5,2) DEFAULT 50.00,
                statutory_reserve_amount DECIMAL(15,2) NOT NULL,
                distributable_pool_amount DECIMAL(15,2) NOT NULL,
                weight_share_capital_percent DECIMAL(5,2) DEFAULT 60.00,
                weight_savings_volume_percent DECIMAL(5,2) DEFAULT 40.00,
                weight_patronage_percent DECIMAL(5,2) DEFAULT 0.00,
                min_share_units_required INT DEFAULT 5,
                min_active_months_required INT DEFAULT 6,
                disqualify_active_arrears BOOLEAN DEFAULT TRUE,
                total_qualified_members INT DEFAULT 0,
                total_disqualified_members INT DEFAULT 0,
                status ENUM('DRAFT_SIMULATION', 'AUDIT_REVIEW', 'APPROVED_POSTED', 'CANCELLED') DEFAULT 'DRAFT_SIMULATION',
                simulated_by_user_id INT NULL,
                approved_by_president_id INT NULL,
                approved_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dividend_allocations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                dividend_period_id INT NOT NULL,
                member_id INT NOT NULL,
                shares_held INT NOT NULL,
                share_equity_amount DECIMAL(15,2) NOT NULL,
                savings_balance DECIMAL(15,2) NOT NULL,
                loan_patronage_volume DECIMAL(15,2) DEFAULT 0.00,
                is_qualified BOOLEAN NOT NULL,
                disqualification_reason VARCHAR(255) NULL,
                dividend_from_shares DECIMAL(15,2) DEFAULT 0.00,
                dividend_from_savings DECIMAL(15,2) DEFAULT 0.00,
                dividend_from_patronage DECIMAL(15,2) DEFAULT 0.00,
                total_dividend_payable DECIMAL(15,2) NOT NULL,
                payout_preference ENUM('SAVINGS_CREDIT', 'BANK_TRANSFER') DEFAULT 'SAVINGS_CREDIT',
                payout_status ENUM('PENDING', 'CREDITED_TO_SAVINGS', 'DISBURSED_TO_BANK') DEFAULT 'PENDING',
                payout_reference VARCHAR(128) NULL,
                settled_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dividend_period_id) REFERENCES dividend_periods(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES members(id),
                INDEX (member_id),
                INDEX (payout_status)
            );
        """)
        print("  + Created dividend distribution engine tables.")

        # 4. SYSTEM CONFIGURATION ENHANCEMENTS (FINANCIAL YEAR SETTINGS)
        print("\n[4] Configuring dynamic financial year parameters...")
        cursor.execute("""
            INSERT INTO system_config (config_key, config_value, description)
            VALUES 
                ('FINANCIAL_YEAR_CYCLE', 'OCT_TO_SEP', 'Statutory Financial Year cycle (OCT_TO_SEP or JAN_TO_DEC)'),
                ('FINANCIAL_YEAR_START_MONTH', '10', 'Starting month of cooperative financial year (1-12)'),
                ('DEFAULT_DIVIDEND_STATUTORY_RESERVE_PCT', '50.00', 'Mandatory Statutory Reserve percentage from surplus (Min 50% per Lagos State Cap C15 & Article 24)'),
                ('DEFAULT_DIVIDEND_SHARE_WEIGHT_PCT', '60.00', 'Dividend weighting on Paid-Up Share Equity (default 60%)'),
                ('DEFAULT_DIVIDEND_SAVINGS_WEIGHT_PCT', '40.00', 'Dividend weighting on Regular Savings Patronage (default 40%)')
            ON DUPLICATE KEY UPDATE description = VALUES(description);
        """)
        print("  + Seeded financial year and dividend config parameters.")

        conn.commit()
        print("\n" + "=" * 80)
        print("  ACCOUNTING & DIVIDENDS SCHEMA MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 80)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
