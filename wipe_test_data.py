import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "wbmf")

def wipe_all_test_data():
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    
    tables_to_wipe = [
        "transactions",
        "loan_repayments",
        "loan_guarantors",
        "loans",
        "welfare_claims",
        "disciplinary_fines",
        "meeting_attendance",
        "officers",
        "next_of_kin",
        "marketplace_products",
        "marketplace_merchants",
        "share_accounts",
        "savings_accounts",
        "welfare_accounts",
        "members"
    ]
    
    print("Disabling foreign key checks...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    
    for table in tables_to_wipe:
        print(f"Deleting data from table: {table}")
        cursor.execute(f"DELETE FROM `{table}`;")
        try:
            cursor.execute(f"ALTER TABLE `{table}` AUTO_INCREMENT = 1;")
        except Exception:
            pass
        
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    conn.commit()
    
    print("\nVerifying table counts:")
    for table in tables_to_wipe + ["system_config", "loan_products"]:
        cursor.execute(f"SELECT COUNT(*) FROM `{table}`;")
        count = cursor.fetchone()[0]
        print(f"  - {table}: {count} records")
        
    cursor.close()
    conn.close()
    print("\n[SUCCESS] All test transactions, member accounts, and member registries have been completely wiped.")

if __name__ == "__main__":
    wipe_all_test_data()
