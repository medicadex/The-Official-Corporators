"""
migrate_registration_fee_advice.py
Adds amount_registration_fee and paid_registration columns to payment_advices table,
and injects the mandatory ₦5,000 Entrance/Registration Fee into initial payment advices.
"""

from decimal import Decimal
from wbmf_db import WealthbridgeDB

def migrate():
    db = WealthbridgeDB()
    conn = db.get_connection()
    cur = conn.cursor(dictionary=True)

    print("Checking payment_advices columns...")
    cur.execute("DESCRIBE payment_advices")
    existing_cols = [r["Field"] for r in cur.fetchall()]

    if "amount_registration_fee" not in existing_cols:
        print("Adding amount_registration_fee column...")
        cur.execute("""
            ALTER TABLE payment_advices
            ADD COLUMN amount_registration_fee DECIMAL(15, 2) NOT NULL DEFAULT 0.00 AFTER amount_fines;
        """)

    if "paid_registration" not in existing_cols:
        print("Adding paid_registration column...")
        cur.execute("""
            ALTER TABLE payment_advices
            ADD COLUMN paid_registration DECIMAL(15, 2) NOT NULL DEFAULT 0.00 AFTER paid_fines;
        """)

    conn.commit()
    print("Schema updated successfully!")

    # Check which members have already paid registration fee in transactions
    cur.execute("""
        SELECT DISTINCT member_id 
        FROM transactions 
        WHERE ledger_category = 'REGISTRATION_FEE' AND status = 'VERIFIED';
    """)
    paid_members = {r["member_id"] for r in cur.fetchall()}
    print(f"Members with settled registration fee: {paid_members}")

    # For each member without settled registration fee:
    # Check if they have an existing advice for this month, and add ₦5,000 if not already added
    cur.execute("SELECT id FROM members;")
    all_members = [r["id"] for r in cur.fetchall()]

    for m_id in all_members:
        if m_id not in paid_members:
            # Check their latest advice
            cur.execute("""
                SELECT * FROM payment_advices 
                WHERE member_id = %s 
                ORDER BY billing_period ASC LIMIT 1;
            """, (m_id,))
            first_adv = cur.fetchone()
            if first_adv:
                if Decimal(str(first_adv["amount_registration_fee"])) == Decimal("0.00"):
                    new_tot = Decimal(str(first_adv["total_expected_amount"])) + Decimal("5000.00")
                    new_out = Decimal(str(first_adv["outstanding_balance"])) + Decimal("5000.00")
                    cur.execute("""
                        UPDATE payment_advices
                        SET amount_registration_fee = 5000.00,
                            total_expected_amount = %s,
                            outstanding_balance = %s
                        WHERE id = %s;
                    """, (new_tot, new_out, first_adv["id"]))
                    print(f"Updated member {m_id} first advice #{first_adv['advice_reference']} with NGN 5,000 Registration Fee.")

    conn.commit()
    cur.close()
    conn.close()
    print("Migration and retro-fit completed successfully.")

if __name__ == "__main__":
    migrate()
