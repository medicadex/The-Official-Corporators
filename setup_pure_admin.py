"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
PURE DEVELOPER ADMIN SETUP & MEMBER PURGE SCRIPT (setup_pure_admin.py)
-----------------------------------------------------------------------------
Architecture:
- The Developer Admin is strictly a system/developer console user.
- Admin does NOT have any member records, share accounts, savings accounts,
  welfare accounts, or payment transactions.
- Admin accounts live in dedicated `admin_users` table.
- Purges all dummy records for member #99 from cooperative tables.

Official Contact: wealthbridge.coopsociety@gmail.com
=============================================================================
"""

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv(override=True)
import wbmf_db

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "wbmf")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Pass123*"

def setup():
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor(dictionary=True)
    try:
        print("1. Creating `admin_users` table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                email VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'SUPER_ADMIN',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        print("2. Inserting / updating Developer Admin in `admin_users` table...")
        admin_hash = wbmf_db.hash_password(ADMIN_PASSWORD)
        cursor.execute("""
            INSERT INTO admin_users (username, email, password_hash, full_name, role, is_active)
            VALUES (%s, 'admin@wealthbridge.ng', %s, 'Developer Administrator', 'SUPER_ADMIN', TRUE)
            ON DUPLICATE KEY UPDATE 
                password_hash = %s,
                full_name = 'Developer Administrator',
                role = 'SUPER_ADMIN',
                is_active = TRUE;
        """, (ADMIN_USERNAME, admin_hash, admin_hash))

        print("3. Purging dummy member #99 from all cooperative member and financial tables...")
        # Check if member 99 or member_code = 'admin' exists in members
        cursor.execute("SELECT id FROM members WHERE id = 99 OR LOWER(member_code) = 'admin';")
        m_rows = cursor.fetchall()
        for r in m_rows:
            mid = r["id"]
            cursor.execute("DELETE FROM next_of_kin WHERE member_id = %s;", (mid,))
            cursor.execute("DELETE FROM officers WHERE member_id = %s;", (mid,))
            cursor.execute("DELETE FROM share_accounts WHERE member_id = %s;", (mid,))
            cursor.execute("DELETE FROM savings_accounts WHERE member_id = %s;", (mid,))
            cursor.execute("DELETE FROM welfare_accounts WHERE member_id = %s;", (mid,))
            cursor.execute("DELETE FROM transactions WHERE member_id = %s;", (mid,))
            cursor.execute("DELETE FROM disciplinary_fines WHERE member_id = %s;", (mid,))
            cursor.execute("DELETE FROM members WHERE id = %s;", (mid,))
            print(f"   [OK] Purged member #{mid} from cooperative tables.")

        conn.commit()
        print("\n[SUCCESS] Dedicated Developer Admin provisioned in `admin_users`.")
        print("[SUCCESS] Cooperative members table is clean: contains 0 dummy admin records.")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    setup()
