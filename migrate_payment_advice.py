"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
PAYMENT ADVICE & AUTO-DISTRIBUTION SCHEMA MIGRATION (migrate_payment_advice.py)
-----------------------------------------------------------------------------
Creates:
1. `payment_advices`: Monthly itemized expected obligations per cooperator
2. `payment_advice_distributions`: Audit trail for auto-distributed inward remittances
Official Secretariat Email: wealthbridge.coopsociety@gmail.com
=============================================================================
"""

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv(override=True)

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Pass123*")
DB_NAME = os.getenv("DB_NAME", "wbmf")

def run_migration():
    print(f"Connecting to MySQL database '{DB_NAME}' on {DB_HOST}:{DB_PORT}...")
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()

    try:
        print("[1] Creating 'payment_advices' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment_advices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                advice_reference VARCHAR(64) UNIQUE NOT NULL,
                member_id INT NOT NULL,
                billing_period VARCHAR(7) NOT NULL, -- Format: YYYY-MM e.g. '2026-10'
                issue_date DATE NOT NULL,
                due_date DATE NOT NULL,
                tier_at_issuance ENUM('STANDARD', 'PLUS', 'PREMIUM') NOT NULL DEFAULT 'STANDARD',
                amount_fines DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                amount_loan_repayment DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                amount_welfare DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                amount_share_capital DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                amount_regular_savings DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                amount_target_savings DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                amount_arrears DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                total_expected_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                paid_fines DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                paid_loan DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                paid_welfare DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                paid_shares DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                paid_savings DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                paid_targets DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                total_amount_paid DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                outstanding_balance DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                status ENUM('DUE', 'PARTIALLY_PAID', 'FULLY_SETTLED', 'OVERDUE') NOT NULL DEFAULT 'DUE',
                admin_notes TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_adv_member_period (member_id, billing_period),
                INDEX idx_adv_status (status),
                CONSTRAINT fk_adv_member FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        print("  + Table 'payment_advices' verified/created.")

        print("[2] Creating 'payment_advice_distributions' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment_advice_distributions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                advice_id INT NOT NULL,
                member_id INT NOT NULL,
                payment_reference VARCHAR(128) NOT NULL,
                payment_method VARCHAR(64) NOT NULL DEFAULT 'PAYSTACK_DVA',
                total_payment_received DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                allocated_fines DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                allocated_loan DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                allocated_welfare DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                allocated_shares DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                allocated_savings DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                allocated_targets DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                allocated_surplus_savings DECIMAL(12,2) NOT NULL DEFAULT 0.00,
                narration VARCHAR(255) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_dist_advice (advice_id),
                INDEX idx_dist_ref (payment_reference),
                CONSTRAINT fk_dist_advice FOREIGN KEY (advice_id) REFERENCES payment_advices(id) ON DELETE CASCADE,
                CONSTRAINT fk_dist_member FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        print("  + Table 'payment_advice_distributions' verified/created.")

        conn.commit()
        print("\n[SUCCESS] Payment Advice schema migration completed successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
