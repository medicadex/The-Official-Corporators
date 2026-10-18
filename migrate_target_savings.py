"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
DYNAMIC TARGET SAVINGS LEDGER MIGRATION SCRIPT (migrate_target_savings.py)
-----------------------------------------------------------------------------
Creates:
- `target_savings_accounts`: Dynamic member-created voluntary target savings ledgers
- `target_savings_transactions`: Audit trail for target savings deposits & maturity payouts
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
    print("MIGRATING DYNAMIC TARGET SAVINGS LEDGERS")
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
        print("1. Creating `target_savings_accounts` table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS target_savings_accounts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                member_id INT NOT NULL,
                target_type ENUM(
                    'BIRTHDAY',
                    'CHRISTMAS',
                    'ILEYA',
                    'BUILDING',
                    'PILGRIMAGE',
                    'EDUCATION',
                    'OTHERS'
                ) NOT NULL,
                title VARCHAR(150) NOT NULL,
                target_amount DECIMAL(15, 2) NOT NULL,
                current_balance DECIMAL(15, 2) NOT NULL DEFAULT 0.00,
                start_date DATE NOT NULL,
                maturity_date DATE NOT NULL,
                auto_save_amount DECIMAL(15, 2) DEFAULT 0.00,
                status ENUM('ACTIVE', 'MATURED', 'WITHDRAWN', 'CANCELLED') NOT NULL DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
                INDEX idx_member_target (member_id, status)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        print("2. Creating `target_savings_transactions` table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS target_savings_transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                target_account_id INT NOT NULL,
                member_id INT NOT NULL,
                transaction_type ENUM('DEPOSIT', 'WITHDRAWAL', 'INTEREST_DIVIDEND') NOT NULL,
                amount DECIMAL(15, 2) NOT NULL,
                balance_after DECIMAL(15, 2) NOT NULL,
                payment_method VARCHAR(50) DEFAULT 'POLARIS_BANK_TRANSFER',
                channel_reference VARCHAR(100) NOT NULL,
                narration TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (target_account_id) REFERENCES target_savings_accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
                INDEX idx_target_tx (target_account_id, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        conn.commit()
        print("[SUCCESS] Target Savings tables created successfully.")

        # Seed sample target ledgers for demo founding members if empty
        cursor.execute("SELECT COUNT(*) FROM target_savings_accounts;")
        count = cursor.fetchone()[0]
        if count == 0:
            print("3. Seeding representative sample target savings ledgers for founding members...")
            sample_ledgers = [
                # Member 1 (President Adebowale): Building Target
                (1, 'BUILDING', 'Ibeju-Lekki Estate Land Target', 5000000.00, 750000.00, '2026-09-26', '2027-09-30', 'ACTIVE'),
                # Member 1: Ileya Target
                (1, 'ILEYA', '2027 Ileya Ram & Family Feast Target', 350000.00, 120000.00, '2026-10-01', '2027-06-01', 'ACTIVE'),
                # Member 2 (Sec. Olaoye): Education Target
                (2, 'EDUCATION', 'Postgraduate Tuition & Professional Certs', 800000.00, 250000.00, '2026-10-01', '2027-03-31', 'ACTIVE'),
                # Member 3 (Legal Lead Olajide): Pilgrimage Target
                (3, 'PILGRIMAGE', 'Holy Pilgrimage to Makkah (Hajj 2027)', 2500000.00, 450000.00, '2026-10-01', '2027-05-15', 'ACTIVE'),
                # Member 4 (Fin Sec Yahaya): Christmas Target (already matured sample for withdrawal test)
                (4, 'CHRISTMAS', '2026 End of Year Family Celebration', 200000.00, 200000.00, '2026-01-01', '2026-10-10', 'MATURED')
            ]

            for s in sample_ledgers:
                cursor.execute("""
                    INSERT INTO target_savings_accounts 
                    (member_id, target_type, title, target_amount, current_balance, start_date, maturity_date, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """, s)
                target_id = cursor.lastrowid
                if s[4] > 0:
                    cursor.execute("""
                        INSERT INTO target_savings_transactions
                        (target_account_id, member_id, transaction_type, amount, balance_after, payment_method, channel_reference, narration)
                        VALUES (%s, %s, 'DEPOSIT', %s, %s, 'POLARIS_BANK_TRANSFER', %s, %s);
                    """, (
                        target_id, s[0], s[4], s[4],
                        f"TS-DEP-INIT-{target_id}-2026",
                        f"Initial allocation for {s[2]}"
                    ))

            conn.commit()
            print("[SUCCESS] Seeded initial target savings ledgers.")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
