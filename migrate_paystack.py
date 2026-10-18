"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
PAYSTACK INTEGRATION SCHEMA MIGRATION (migrate_paystack.py)
-----------------------------------------------------------------------------
Adds:
1. Paystack Customer & Dedicated Virtual Account (DVA) columns to `members` table.
2. `paystack_webhook_logs` table for idempotent real-time remittance processing.
Official Contact: wealthbridge.coopsociety@gmail.com
=============================================================================
"""

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv(override=True)

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "wbmf")

def migrate():
    print("=" * 65)
    print("MIGRATING PAYSTACK COLUMNS & WEBHOOK AUDIT TABLES")
    print("=" * 65)

    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    try:
        # Check existing columns in members
        cursor.execute("DESCRIBE members;")
        cols = [row[0] for row in cursor.fetchall()]

        paystack_cols = [
            ("paystack_customer_code", "VARCHAR(100) NULL"),
            ("paystack_dva_account_number", "VARCHAR(20) NULL"),
            ("paystack_dva_bank_name", "VARCHAR(100) NULL"),
            ("paystack_dva_account_name", "VARCHAR(150) NULL"),
            ("paystack_auth_code", "VARCHAR(100) NULL")
        ]

        for col_name, col_def in paystack_cols:
            if col_name not in cols:
                print(f"Adding column `{col_name}` to `members`...")
                cursor.execute(f"ALTER TABLE members ADD COLUMN {col_name} {col_def};")
            else:
                print(f"Column `{col_name}` already exists in `members`.")

        print("Creating `paystack_webhook_logs` table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paystack_webhook_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                event_type VARCHAR(100) NOT NULL,
                reference VARCHAR(100) NOT NULL UNIQUE,
                member_id INT NULL,
                amount DECIMAL(15, 2) NOT NULL,
                channel VARCHAR(50) DEFAULT 'dedicated_nuban',
                payload JSON NOT NULL,
                status ENUM('PROCESSED', 'IGNORED', 'FAILED') DEFAULT 'PROCESSED',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE SET NULL,
                INDEX idx_paystack_ref (reference),
                INDEX idx_paystack_member (member_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        conn.commit()
        print("[SUCCESS] Paystack schema migration executed successfully.")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
