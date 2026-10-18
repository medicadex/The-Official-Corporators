"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
SEED FOUNDING MEMBERS UTILITY (seed_founding_members.py)
-----------------------------------------------------------------------------
Populates the 8 Founding Members, Tripartite Accounts, Executive Officers,
and Inaugural General Meeting Attendance.
Official Contact: wealthbridge.coopsociety@gmail.com
=============================================================================
"""

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "wbmf")

def run_seed():
    sql_path = os.path.join(os.path.dirname(__file__), "seed_founding_members.sql")
    if not os.path.exists(sql_path):
        print(f"Error: {sql_path} does not exist.")
        return

    with open(sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Filter out pure comment lines
    clean_lines = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or stripped.startswith("/*"):
            continue
        clean_lines.append(line)

    clean_sql = "\n".join(clean_lines)
    statements = [s.strip() for s in clean_sql.split(";") if s.strip()]

    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()

    print("Executing seed_founding_members.sql...")
    for stmt in statements:
        if stmt.upper().startswith("USE"):
            continue
        try:
            cursor.execute(stmt)
        except Exception as e:
            print(f"Error executing statement: {e}")

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM members;")
    members_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM officers;")
    officers_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM share_accounts;")
    share_count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    print(f"\n[SUCCESS] Seed complete!")
    print(f"  - Active Members: {members_count}")
    print(f"  - Executive Officers: {officers_count}")
    print(f"  - Tripartite Accounts: {share_count}")

if __name__ == "__main__":
    run_seed()
