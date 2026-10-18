import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "wbmf")

def run_migration():
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()

    queries = [
        "ALTER TABLE members ADD COLUMN passport_photo LONGTEXT NULL AFTER identification_number;",
        "ALTER TABLE members ADD COLUMN bank_name VARCHAR(100) NULL AFTER employer_or_business_name;",
        "ALTER TABLE members ADD COLUMN bank_account_number VARCHAR(20) NULL AFTER bank_name;",
        "ALTER TABLE members ADD COLUMN bank_account_name VARCHAR(150) NULL AFTER bank_account_number;",
        "ALTER TABLE members ADD COLUMN bvn VARCHAR(20) NULL AFTER bank_account_name;",
        "ALTER TABLE members ADD COLUMN marital_status ENUM('SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED') DEFAULT 'SINGLE' AFTER gender;",
        "ALTER TABLE members ADD COLUMN kyc_completion_percent INT DEFAULT 20 AFTER contribution_tier;",
        "ALTER TABLE members ADD COLUMN pending_email VARCHAR(100) NULL AFTER kyc_completion_percent;",
        "ALTER TABLE members ADD COLUMN pending_phone VARCHAR(20) NULL AFTER pending_email;",
        "ALTER TABLE members ADD COLUMN pending_address TEXT NULL AFTER pending_phone;",
        "ALTER TABLE members ADD COLUMN contact_change_status ENUM('NONE', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED') DEFAULT 'NONE' AFTER pending_address;",
        "ALTER TABLE members ADD COLUMN contact_change_requested_at DATETIME NULL AFTER contact_change_status;",
        "ALTER TABLE members ADD COLUMN contact_change_reviewed_by INT NULL AFTER contact_change_requested_at;",
        "ALTER TABLE members ADD COLUMN contact_change_reviewed_at DATETIME NULL AFTER contact_change_reviewed_by;",
        """CREATE TABLE IF NOT EXISTS contact_change_approvals (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            member_id INT NOT NULL,
            officer_id INT NOT NULL,
            officer_portfolio ENUM('PRESIDENT', 'GENERAL_SECRETARY') NOT NULL,
            approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_contact_change_approver (member_id, officer_id),
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
            FOREIGN KEY (officer_id) REFERENCES members(id)
        );"""
    ]

    for q in queries:
        try:
            cursor.execute(q)
            conn.commit()
            print("[+] Executed:", q.split()[4])
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("[-] Already exists:", q.split()[4])
            else:
                print("[!] Error:", e)

    cursor.execute("DESCRIBE members;")
    columns = [r[0] for r in cursor.fetchall()]
    print("\nTotal columns in members:", len(columns))
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    run_migration()
