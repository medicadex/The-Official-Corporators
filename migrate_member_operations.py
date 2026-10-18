"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
DATABASE MIGRATION: MEMBER OPERATIONS & EXIT GOVERNANCE
-----------------------------------------------------------------------------
1. Updates members.status enum to include ('PENDING_KYC', 'ACTIVE', 'SUSPENDED', 'EXITED', 'DECEASED')
2. Ensures loan_guarantors table has full status and consent columns
3. Creates member_exits table for statutory withdrawal and estate settlement (Articles 9 & 11)

Official Invariant Email: wealthbridge.coopsociety@gmail.com
=============================================================================
"""

import sys
from wbmf_db import WealthbridgeDB

def run_migration():
    print("=" * 70)
    print("MIGRATING MEMBER OPERATIONS & EXIT GOVERNANCE SCHEMA")
    print("=" * 70)

    db = WealthbridgeDB()
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        # 1. Update members.status ENUM
        print("-> Updating members.status ENUM to include EXITED and DECEASED...")
        cursor.execute("""
            ALTER TABLE members 
            MODIFY COLUMN status ENUM('PENDING_KYC', 'ACTIVE', 'SUSPENDED', 'EXITED', 'DECEASED') 
            NOT NULL DEFAULT 'PENDING_KYC';
        """)
        print("   [OK] members.status ENUM updated.")

        # 2. Check / update loan_guarantors status ENUM
        print("-> Checking loan_guarantors columns...")
        cursor.execute("""
            ALTER TABLE loan_guarantors 
            MODIFY COLUMN status ENUM('PENDING_CONSENT', 'ACCEPTED', 'DECLINED', 'RELEASED', 'INVOKED') 
            NOT NULL DEFAULT 'PENDING_CONSENT';
        """)
        print("   [OK] loan_guarantors status ENUM updated.")

        # 3. Create member_exits table
        print("-> Creating member_exits table (Articles 9 & 11)...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS member_exits (
                id INT AUTO_INCREMENT PRIMARY KEY,
                member_id INT NOT NULL,
                exit_type ENUM('VOLUNTARY_WITHDRAWAL', 'DEATH_ESTATE_SETTLEMENT', 'EXPULSION') NOT NULL DEFAULT 'VOLUNTARY_WITHDRAWAL',
                notice_date DATE NOT NULL,
                statutory_notice_expiry_date DATE NOT NULL,
                reason TEXT,
                supporting_doc_url VARCHAR(500),
                nok_claimant_name VARCHAR(150),
                nok_claimant_phone VARCHAR(30),
                nok_relationship VARCHAR(50),
                status ENUM('PENDING_CLEARANCE', 'FINANCIALLY_CLEARED', 'SETTLED_REFUNDED', 'REJECTED') NOT NULL DEFAULT 'PENDING_CLEARANCE',
                total_savings_at_exit DECIMAL(15,2) NOT NULL DEFAULT 0.00,
                total_target_savings_at_exit DECIMAL(15,2) NOT NULL DEFAULT 0.00,
                total_shares_at_exit DECIMAL(15,2) NOT NULL DEFAULT 0.00,
                outstanding_loans_at_exit DECIMAL(15,2) NOT NULL DEFAULT 0.00,
                outstanding_fines_at_exit DECIMAL(15,2) NOT NULL DEFAULT 0.00,
                active_guarantor_commitments_count INT NOT NULL DEFAULT 0,
                exit_processing_fee DECIMAL(15,2) NOT NULL DEFAULT 0.00,
                bereavement_welfare_grant DECIMAL(15,2) NOT NULL DEFAULT 0.00,
                net_refund_amount DECIMAL(15,2) NOT NULL DEFAULT 0.00,
                cleared_by_officer_id INT,
                approved_by_president_id INT,
                rejection_reason TEXT,
                refund_payment_ref VARCHAR(100),
                refund_disbursed_at DATETIME,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE RESTRICT,
                INDEX idx_member_exit_status (status),
                INDEX idx_member_exit_type (exit_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """)
        print("   [OK] member_exits table created successfully.")

        conn.commit()
        print("\n" + "=" * 70)
        print("MIGRATION COMPLETED SUCCESSFULLY (100% GREEN)!")
        print("=" * 70)

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
