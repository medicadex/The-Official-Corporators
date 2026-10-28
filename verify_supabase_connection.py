"""
verify_supabase_connection.py
Tests connection to Supabase PostgreSQL and checks schema & data status.
Usage:
    python verify_supabase_connection.py [CONNECTION_STRING_OR_PASSWORD]
"""

import os
import sys
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv('WEALTHBRIDGE_WEB_APP/.env', override=True)
load_dotenv('.env', override=True)

conn_str = None
if len(sys.argv) > 1:
    arg = sys.argv[1].strip()
    if arg.startswith("postgres://") or arg.startswith("postgresql://"):
        conn_str = arg
    else:
        # Assumed to be database password
        project_ref = os.getenv("SUPABASE_PROJECT_REF", "pdbirqjqcsuhdmzbtyel")
        # Try common pooler regions
        pooler_host = os.getenv("SUPABASE_POOLER_HOST", "aws-1-eu-west-1.pooler.supabase.com")
        conn_str = f"postgresql://postgres.{project_ref}:{arg}@{pooler_host}:6543/postgres?sslmode=require"
else:
    conn_str = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")

if not conn_str or not (conn_str.startswith("postgres://") or conn_str.startswith("postgresql://")):
    print("[ERROR] No Supabase PostgreSQL connection string found.")
    print("Please provide connection string or password as argument, or set SUPABASE_DB_URL in .env.")
    print("Example: python verify_supabase_connection.py 'postgresql://postgres.pdbirqjqcsuhdmzbtyel:YOUR_PASSWORD@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require'")
    sys.exit(1)

print(f"[*] Attempting connection to Supabase PostgreSQL...")
# Mask password in log
masked = conn_str
if "@" in masked and ":" in masked:
    prefix, rest = masked.split("@", 1)
    p_parts = prefix.split(":")
    if len(p_parts) >= 3:
        p_parts[-1] = "******"
        masked = ":".join(p_parts) + "@" + rest
print(f"[*] Target URI: {masked}")

try:
    conn = psycopg2.connect(conn_str, connect_timeout=15)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT version();")
    ver = cur.fetchone()["version"]
    print(f"[+] Successfully connected to Supabase PostgreSQL!")
    print(f"    PostgreSQL Version: {ver}")
    
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    tables = [r["table_name"] for r in cur.fetchall()]
    print(f"[+] Found {len(tables)} tables in public schema:")
    print("    " + ", ".join(tables[:15]) + ("..." if len(tables) > 15 else ""))
    
    if "members" in tables:
        cur.execute("SELECT COUNT(*) AS cnt FROM public.members;")
        m_cnt = cur.fetchone()["cnt"]
        print(f"[+] Members count in Supabase: {m_cnt}")
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"[ERROR] Failed to connect: {e}")
    sys.exit(1)
