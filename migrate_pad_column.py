import sys
from wbmf_db import WealthbridgeDB

def main():
    db = WealthbridgeDB()
    conn = db.get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SHOW COLUMNS FROM payment_advice_distributions LIKE 'allocated_registration'")
        col = cur.fetchone()
        if not col:
            print("Adding allocated_registration to payment_advice_distributions...")
            cur.execute("""
                ALTER TABLE payment_advice_distributions
                ADD COLUMN allocated_registration DECIMAL(15,2) DEFAULT 0.00 AFTER allocated_fines;
            """)
            conn.commit()
            print("Successfully added allocated_registration column!")
        else:
            print("allocated_registration column already exists.")
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    main()
