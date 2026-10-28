"""
apply_supabase_migration.py
Applies supabase_schema.sql and supabase_seed_data.sql directly to Supabase PostgreSQL.
Usage:
    python apply_supabase_migration.py [CONNECTION_STRING_OR_PASSWORD]
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv('WEALTHBRIDGE_WEB_APP/.env', override=True)
load_dotenv('.env', override=True)

conn_str = None
if len(sys.argv) > 1:
    arg = sys.argv[1].strip()
    if arg.startswith("postgres://") or arg.startswith("postgresql://"):
        conn_str = arg
    else:
        project_ref = os.getenv("SUPABASE_PROJECT_REF", "pdbirqjqcsuhdmzbtyel")
        pooler_host = os.getenv("SUPABASE_POOLER_HOST", "aws-1-eu-west-1.pooler.supabase.com")
        conn_str = f"postgresql://postgres.{project_ref}:{arg}@{pooler_host}:5432/postgres?sslmode=require"
else:
    conn_str = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")

if not conn_str or not (conn_str.startswith("postgres://") or conn_str.startswith("postgresql://")):
    print("[ERROR] Please provide connection string or set SUPABASE_DB_URL in .env.")
    sys.exit(1)

print("[*] Connecting to Supabase PostgreSQL...")
conn = psycopg2.connect(conn_str, connect_timeout=20)
conn.autocommit = True
cur = conn.cursor()

print("[*] Applying schema: supabase_schema.sql...")
schema_file = 'supabase_schema.sql'
if not os.path.exists(schema_file):
    schema_file = os.path.join('WEALTHBRIDGE_WEB_APP', 'supabase_schema.sql')

with open(schema_file, 'r', encoding='utf-8') as f:
    schema_sql = f.read()

cur.execute(schema_sql)
print("[+] Schema successfully applied!")

print("[*] Applying seed data: supabase_seed_data.sql...")
seed_file = 'supabase_seed_data.sql'
if not os.path.exists(seed_file):
    seed_file = os.path.join('WEALTHBRIDGE_WEB_APP', 'supabase_seed_data.sql')

with open(seed_file, 'r', encoding='utf-8') as f:
    seed_sql = f.read()

cur.execute(seed_sql)
print("[+] Seed data successfully imported!")

cur.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public';
""")
tables = cur.fetchall()
print(f"[+] Total tables in Supabase public schema: {len(tables)}")

cur.close()
conn.close()
print("[+] Migration completed successfully!")
