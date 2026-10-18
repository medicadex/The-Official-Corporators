"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
DEVELOPER ADMIN ACCOUNT CREATOR (create_admin_account.py)
-----------------------------------------------------------------------------
Creates the Developer Admin Account:
  Username: admin
  Password: Pass123*
  RBAC Role: SUPER_ADMIN & TECHNOLOGY_SYSTEMS_LEAD (Full Platform Clearance)

Official Invariant Email: wealthbridge.coopsociety@gmail.com
=============================================================================
"""

import os
import mysql.connector
from dotenv import load_dotenv

# Ensure environment is loaded with the standard salt
load_dotenv(override=True)

import wbmf_db

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "wbmf")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Pass123*"
FOUNDER_PASSWORD = "Wealthbridge@2026"

def setup_admin():
    print("=" * 60)
    print("WEALTHBRIDGE COOPERATIVE: DEVELOPER ADMIN SETUP")
    print("=" * 60)

    admin_hash = wbmf_db.hash_password(ADMIN_PASSWORD)
    founder_hash = wbmf_db.hash_password(FOUNDER_PASSWORD)

    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True
    )
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Update all existing founding members with fresh consistent hash
        cursor.execute("UPDATE members SET password_hash = %s WHERE id BETWEEN 1 AND 8;", (founder_hash,))
        print(f"[OK] Synchronized founding members (IDs 1-8) default password to '{FOUNDER_PASSWORD}'.")

        # 2. Check if admin account already exists
        cursor.execute("SELECT id FROM members WHERE member_code = %s OR id = 99;", (ADMIN_USERNAME,))
        existing_admin = cursor.fetchone()

        if existing_admin:
            admin_id = existing_admin["id"]
            cursor.execute("""
                UPDATE members SET
                    member_code = %s,
                    first_name = 'System',
                    last_name = 'Administrator',
                    other_names = 'Lead Developer',
                    email = 'admin@wealthbridge.ng',
                    password_hash = %s,
                    phone = '08000000000',
                    gender = 'MALE',
                    marital_status = 'SINGLE',
                    residential_address = 'Wealthbridge Technology Operations Center, Lagos State, Nigeria',
                    identification_type = 'NIN',
                    identification_number = 'NIN-ADMIN-DEV-001',
                    employment_status = 'PROFESSIONAL',
                    employer_or_business_name = 'Wealthbridge Cooperative Systems Engineering',
                    bank_name = 'Polaris Bank Limited',
                    bank_account_number = '0000000000',
                    bank_account_name = 'Wealthbridge System Administrator',
                    bvn = '22222222222',
                    contribution_tier = 'PREMIUM',
                    status = 'ACTIVE',
                    kyc_completion_percent = 100,
                    contact_change_status = 'NONE',
                    admission_date = '2026-09-26'
                WHERE id = %s;
            """, (ADMIN_USERNAME, admin_hash, admin_id))
            print(f"[OK] Updated existing admin account (ID #{admin_id}).")
        else:
            admin_id = 99
            cursor.execute("""
                INSERT INTO members (
                    id, member_code, first_name, last_name, other_names,
                    email, password_hash, phone, gender, marital_status,
                    residential_address, identification_type, identification_number,
                    employment_status, employer_or_business_name, bank_name,
                    bank_account_number, bank_account_name, bvn, contribution_tier,
                    status, kyc_completion_percent, contact_change_status, admission_date
                ) VALUES (
                    %s, %s, 'System', 'Administrator', 'Lead Developer',
                    'admin@wealthbridge.ng', %s, '08000000000', 'MALE', 'SINGLE',
                    'Wealthbridge Technology Operations Center, Lagos State, Nigeria',
                    'NIN', 'NIN-ADMIN-DEV-001', 'PROFESSIONAL',
                    'Wealthbridge Cooperative Systems Engineering', 'Polaris Bank Limited',
                    '0000000000', 'Wealthbridge System Administrator', '22222222222',
                    'PREMIUM', 'ACTIVE', 100, 'NONE', '2026-09-26'
                );
            """, (admin_id, ADMIN_USERNAME, admin_hash))
            print(f"[OK] Inserted new Developer Admin account (ID #{admin_id}).")

        # 3. Assign Executive Portfolio in officers table
        cursor.execute("DELETE FROM officers WHERE member_id = %s;", (admin_id,))
        cursor.execute("""
            INSERT INTO officers (member_id, portfolio, appointment_date, is_active)
            VALUES (%s, 'TECHNOLOGY_SYSTEMS_LEAD', '2026-09-26', TRUE);
        """, (admin_id,))
        print("[OK] Assigned TECHNOLOGY_SYSTEMS_LEAD executive portfolio (Universal Clearance).")

        # 4. Initialize Tripartite Accounts for Developer Admin
        cursor.execute("""
            INSERT INTO share_accounts (member_id, units_held, paid_up_amount, is_minimum_met, benefits_qualified)
            VALUES (%s, 100, 100000.00, TRUE, TRUE)
            ON DUPLICATE KEY UPDATE units_held = 100, paid_up_amount = 100000.00, is_minimum_met = TRUE, benefits_qualified = TRUE;
        """, (admin_id,))

        cursor.execute("""
            INSERT INTO savings_accounts (member_id, total_balance, encumbered_balance)
            VALUES (%s, 500000.00, 0.00)
            ON DUPLICATE KEY UPDATE total_balance = 500000.00, encumbered_balance = 0.00;
        """, (admin_id,))

        cursor.execute("""
            INSERT INTO welfare_accounts (member_id, cumulative_contributions, consecutive_months_active, last_contribution_date)
            VALUES (%s, 12000.00, 12, '2026-09-26')
            ON DUPLICATE KEY UPDATE cumulative_contributions = 12000.00, consecutive_months_active = 12;
        """, (admin_id,))

        # 5. Initialize Next of Kin
        cursor.execute("SELECT id FROM next_of_kin WHERE member_id = %s;", (admin_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO next_of_kin (member_id, full_name, relationship, phone, email, residential_address, allocation_percentage)
                VALUES (%s, 'Wealthbridge Engineering Escrow', 'INSTITUTIONAL_TRUST', '08000000000', 'wealthbridge.coopsociety@gmail.com', 'Operations Center', 100.00);
            """, (admin_id,))

        print("[OK] Initialized Tripartite Financial Accounts (Shares, Savings, Welfare, NOK).")

        # 6. Verify Authentication via DB method
        auth_test = wbmf_db.WealthbridgeDB().authenticate_user(ADMIN_USERNAME, ADMIN_PASSWORD)
        print("\n" + "=" * 60)
        print("[SUCCESS] Developer Admin Authentication Verified:")
        print(f"  User ID:       {auth_test['user']['id']}")
        print(f"  Username:      {auth_test['user']['member_code']}")
        print(f"  Full Name:     {auth_test['user']['full_name']}")
        print(f"  Primary Role:  {auth_test['user']['primary_role']}")
        print(f"  Roles:         {auth_test['user']['roles']}")
        print(f"  Permissions:   {len(auth_test['user']['permissions'])} Total Permissions")
        print(f"  Executive:     {auth_test['user']['is_executive']}")
        print("=" * 60)

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    setup_admin()
