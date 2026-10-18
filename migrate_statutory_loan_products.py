"""
migrate_statutory_loan_products.py
Synchronizes statutory loan products in Wealthbridge Cooperative Database
Per Bye-Laws:
1. Ordinary loan (*2 of savings)
2. Investment Loan
3. Salary Advance Loan
4. General Purchase Loan (redirects to marketplace)
"""

from wbmf_db import WealthbridgeDB

def migrate_loan_products():
    db = WealthbridgeDB()
    conn = db.get_connection()
    cur = conn.cursor(dictionary=True)

    products = [
        {
            "id": 1,
            "product_name": "Ordinary loan (*2 of savings)",
            "product_code": "ORDINARY_LOAN",
            "description": "Ordinary facility up to 2x savings collateral per statutory bye-laws",
            "min_membership_months": 6,
            "max_multiplier_of_savings": 2.0,
            "max_principal_ceiling": 5000000.00,
            "admin_cost_fee_percent": 2.50,
            "min_tenure_months": 1,
            "max_tenure_months": 24,
            "is_active": 1
        },
        {
            "id": 2,
            "product_name": "Investment Loan",
            "product_code": "INVESTMENT_LOAN",
            "description": "Asset acquisition, enterprise development and high-yield cooperative investment projects",
            "min_membership_months": 6,
            "max_multiplier_of_savings": 3.0,
            "max_principal_ceiling": 10000000.00,
            "admin_cost_fee_percent": 3.00,
            "min_tenure_months": 3,
            "max_tenure_months": 36,
            "is_active": 1
        },
        {
            "id": 3,
            "product_name": "Salary Advance Loan",
            "product_code": "SALARY_ADVANCE",
            "description": "Short-term payroll liquidity advance facility (1-3 months)",
            "min_membership_months": 1,
            "max_multiplier_of_savings": 1.0,
            "max_principal_ceiling": 500000.00,
            "admin_cost_fee_percent": 1.50,
            "min_tenure_months": 1,
            "max_tenure_months": 3,
            "is_active": 1
        },
        {
            "id": 4,
            "product_name": "General Purchase Loan",
            "product_code": "GENERAL_PURCHASE_LOAN",
            "description": "Consumer goods, electronics, and household asset financing via CO-CARE Marketplace portal",
            "min_membership_months": 3,
            "max_multiplier_of_savings": 2.0,
            "max_principal_ceiling": 2000000.00,
            "admin_cost_fee_percent": 2.00,
            "min_tenure_months": 1,
            "max_tenure_months": 12,
            "is_active": 1
        }
    ]

    for p in products:
        cur.execute("""
            INSERT INTO loan_products (
                id, product_name, product_code, description, min_membership_months,
                max_multiplier_of_savings, max_principal_ceiling, admin_cost_fee_percent,
                min_tenure_months, max_tenure_months, is_active
            ) VALUES (
                %(id)s, %(product_name)s, %(product_code)s, %(description)s, %(min_membership_months)s,
                %(max_multiplier_of_savings)s, %(max_principal_ceiling)s, %(admin_cost_fee_percent)s,
                %(min_tenure_months)s, %(max_tenure_months)s, %(is_active)s
            )
            ON DUPLICATE KEY UPDATE
                product_name = VALUES(product_name),
                product_code = VALUES(product_code),
                description = VALUES(description),
                min_membership_months = VALUES(min_membership_months),
                max_multiplier_of_savings = VALUES(max_multiplier_of_savings),
                max_principal_ceiling = VALUES(max_principal_ceiling),
                admin_cost_fee_percent = VALUES(admin_cost_fee_percent),
                min_tenure_months = VALUES(min_tenure_months),
                max_tenure_months = VALUES(max_tenure_months),
                is_active = VALUES(is_active);
        """, p)

    conn.commit()
    print("Successfully updated loan_products with 4 statutory bye-law products:")
    cur.execute("SELECT id, product_name, product_code, max_multiplier_of_savings, max_principal_ceiling FROM loan_products")
    for row in cur.fetchall():
        print(f"[{row['id']}] {row['product_name']} ({row['product_code']}) - Up to {row['max_multiplier_of_savings']}x savings, Cap: NGN {row['max_principal_ceiling']:,.2f}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    migrate_loan_products()
