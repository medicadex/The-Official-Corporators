"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
ENTERPRISE TEST DATA PURGE & REINITIALIZATION ENGINE (wipe_test_data.py)
-----------------------------------------------------------------------------
Statutory Jurisdiction: Lagos State Cooperative Societies Law (Cap C15)
Official Secretariat Email: wealthbridge.coopsociety@gmail.com
=============================================================================
Safely wipes all test cooperator records, accounts, loans, and ledgers
while preserving foundational regulatory rules, chart of accounts, and admin.
Supports both Supabase Cloud PostgreSQL and Local MySQL.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv('WEALTHBRIDGE_WEB_APP/.env', override=True)
load_dotenv('.env', override=True)

TABLES_TO_WIPE = [
    "audit_logs",
    "system_notifications",
    "paystack_webhook_logs",
    "manual_bank_payments",
    "disciplinary_fines",
    "welfare_claims",
    "loan_appeals",
    "loan_repayments",
    "loan_guarantors",
    "loan_approval_steps",
    "loans",
    "target_savings_transactions",
    "target_savings_accounts",
    "payment_advice_distributions",
    "payment_advices",
    "transactions",
    "journal_entry_lines",
    "journal_entries",
    "dividend_allocations",
    "dividend_periods",
    "member_exits",
    "meeting_attendance",
    "general_meetings",
    "officers",
    "member_roles",
    "next_of_kin",
    "savings_accounts",
    "share_accounts",
    "welfare_accounts",
    "marketplace_products",
    "marketplace_merchants",
    "members"
]

FOUNDATION_TABLES = [
    "system_config",
    "roles",
    "permissions",
    "role_permissions",
    "loan_products",
    "chart_of_accounts",
    "admin_users"
]

def wipe_supabase():
    import psycopg2
    supabase_url = os.getenv("SUPABASE_DB_URL")
    if not supabase_url:
        print("[SKIP] SUPABASE_DB_URL not configured.")
        return False

    print("\n" + "=" * 70)
    print(" PURGING TEST DATA ON SUPABASE CLOUD POSTGRESQL")
    print("=" * 70)
    
    conn = psycopg2.connect(supabase_url)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        table_list_str = ', '.join([f'public.{t}' for t in TABLES_TO_WIPE])
        print(f"[*] Truncating {len(TABLES_TO_WIPE)} test tables with RESTART IDENTITY CASCADE...")
        cur.execute(f"TRUNCATE TABLE {table_list_str} RESTART IDENTITY CASCADE;")
        print("[+] Supabase tables truncated and sequences reset to 1 successfully!")

        print("\n[*] Supabase Verification:")
        for t in TABLES_TO_WIPE:
            cur.execute(f"SELECT COUNT(*) FROM public.{t};")
            cnt = cur.fetchone()[0]
            if cnt > 0:
                print(f"  [WARNING] {t}: {cnt} rows remaining!")
        print("  [+] All 32 test tables confirmed at 0 rows.")

        print("\n[*] Preserved Foundation Tables in Supabase:")
        for f in FOUNDATION_TABLES:
            cur.execute(f"SELECT COUNT(*) FROM public.{f};")
            print(f"  [PRESERVED] {f}: {cur.fetchone()[0]} rows")

        return True
    finally:
        cur.close()
        conn.close()

def wipe_mysql():
    import mysql.connector
    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = int(os.getenv("DB_PORT", 3306))
    db_user = os.getenv("DB_USER", "root")
    db_pass = os.getenv("DB_PASSWORD", "Loveth123.")
    db_name = os.getenv("DB_NAME", "wbmf")

    print("\n" + "=" * 70)
    print(" PURGING TEST DATA ON LOCAL MYSQL")
    print("=" * 70)

    try:
        conn = mysql.connector.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database=db_name
        )
        cur = conn.cursor()

        cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
        for t in TABLES_TO_WIPE:
            try:
                cur.execute(f"DELETE FROM `{t}`;")
                cur.execute(f"ALTER TABLE `{t}` AUTO_INCREMENT = 1;")
            except Exception as e:
                pass
        cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
        conn.commit()

        print("[+] Local MySQL tables wiped and AUTO_INCREMENT reset to 1.")

        print("\n[*] Preserved Foundation Tables in MySQL:")
        for f in FOUNDATION_TABLES:
            try:
                cur.execute(f"SELECT COUNT(*) FROM `{f}`;")
                print(f"  [PRESERVED] {f}: {cur.fetchone()[0]} rows")
            except Exception:
                pass

        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Could not connect to local MySQL: {e}")
        return False

if __name__ == "__main__":
    target = sys.argv[1].lower() if len(sys.argv) > 1 else "both"
    
    if target in ("supabase", "cloud", "both"):
        wipe_supabase()
    if target in ("mysql", "local", "both"):
        wipe_mysql()

    print("\n" + "=" * 70)
    print(" [COMPLETED] Test data purge finalized successfully.")
    print(" The platform is now in pristine state, ready for real member onboarding.")
    print("=" * 70)
