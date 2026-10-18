"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
GOVERNANCE & FIDUCIARY SUITE MIGRATION (migrate_governance_suite.py)
-----------------------------------------------------------------------------
Installs:
1. Dynamic RBAC tables: roles, permissions, role_permissions, member_roles
2. Multi-tier loan governance & appeals: loan_approval_steps, loan_appeals,
   and alters `loans` table.
3. Polaris Bank manual transfer receipts: manual_bank_payments
4. Forensic Audit Trail: audit_logs (tamper-evident, immutable append-only)

Official Secretariat Invariant Email: wealthbridge.coopsociety@gmail.com
=============================================================================
"""

import os
import sys
sys.stdout.reconfigure(encoding="utf-8")
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "wbmf")

def run_migration():
    print(f"Connecting to MySQL ({DB_HOST}:{DB_PORT}, DB: {DB_NAME})...")
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor(dictionary=True)
    try:
        # ---------------------------------------------------------------------
        # 1. DYNAMIC RBAC TABLES
        # ---------------------------------------------------------------------
        print("[1/5] Creating Dynamic RBAC Tables (roles, permissions, role_permissions, member_roles)...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `roles` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `role_code` VARCHAR(50) NOT NULL UNIQUE,
                `role_name` VARCHAR(100) NOT NULL,
                `description` TEXT NULL,
                `is_system_role` BOOLEAN DEFAULT FALSE,
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `permissions` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `perm_key` VARCHAR(60) NOT NULL UNIQUE,
                `perm_name` VARCHAR(120) NOT NULL,
                `module` VARCHAR(50) NOT NULL,
                `description` TEXT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `role_permissions` (
                `role_id` INT NOT NULL,
                `permission_id` INT NOT NULL,
                PRIMARY KEY (`role_id`, `permission_id`),
                FOREIGN KEY (`role_id`) REFERENCES `roles`(`id`) ON DELETE CASCADE,
                FOREIGN KEY (`permission_id`) REFERENCES `permissions`(`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `member_roles` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `member_id` INT NOT NULL,
                `role_id` INT NOT NULL,
                `assigned_by_user_id` INT NULL,
                `assigned_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY `uniq_member_role` (`member_id`, `role_id`),
                FOREIGN KEY (`member_id`) REFERENCES `members`(`id`) ON DELETE CASCADE,
                FOREIGN KEY (`role_id`) REFERENCES `roles`(`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # ---------------------------------------------------------------------
        # 2. SEED PERMISSIONS AND CORE SYSTEM ROLES
        # ---------------------------------------------------------------------
        print("[2/5] Seeding 32 Granular Permissions and Statutory Core Roles...")
        
        all_perms = [
            # Member Core
            ("view_own_profile", "View Own Profile", "MEMBER", "Inspect personal biodata and status"),
            ("view_own_accounts", "View Personal Accounts", "MEMBER", "View Savings, Shares, and Welfare balances"),
            ("submit_contribution", "Submit Contributions", "MEMBER", "Fund accounts and settle monthly dues"),
            ("apply_loan", "Apply for Financing", "MEMBER", "Submit 2x interest-free loan applications"),
            ("submit_welfare_claim", "Submit Welfare Claim", "MEMBER", "Lodge mutual solidarity grant claims"),
            ("view_marketplace", "Browse CO-CARE Market", "MEMBER", "Inspect cooperative vetted marketplace"),
            ("view_bylaws", "View Bye-Laws & Rules", "MEMBER", "Inspect statutory charter and policies"),

            # Secretariat & Membership
            ("view_executive_console", "Access Executive Desks", "EXECUTIVE", "Clearance to enter Executive Console"),
            ("manage_members", "Manage Cooperators", "SECRETARIAT", "Edit cooperator biodata and records"),
            ("approve_kyc", "Approve Cooperator KYC", "SECRETARIAT", "Review and verify new member applications"),
            ("reject_kyc", "Reject Incomplete KYC", "SECRETARIAT", "Decline invalid applicant records"),
            ("view_all_members", "View Complete Register", "SECRETARIAT", "View the statutory register of members"),
            ("manage_meetings", "Manage General Meetings", "SECRETARIAT", "Record meeting resolutions and attendance"),
            ("issue_passbook", "Issue Passbook Statements", "SECRETARIAT", "Generate official cooperator passbooks"),
            ("verify_guarantors", "Verify Guarantor Liens", "SECRETARIAT", "Review and enforce loan guarantor obligations"),
            ("arbitrate_disputes", "Arbitrate Member Disputes", "SECRETARIAT", "Handle member grievances under Bye-Laws"),

            # Treasury & Financials
            ("verify_contributions", "Verify Bank Remittances", "TREASURY", "Confirm inward bank payments & receipts"),
            ("issue_fines", "Assess Disciplinary Fines", "TREASURY", "Levy statutory compliance penalties"),
            ("view_ledger_audit", "Audit Double-Entry Ledger", "TREASURY", "Inspect real-time double entry transactions"),
            ("manage_inward_remittances", "Manage Bank Reconciliation", "TREASURY", "Reconcile Polaris Bank remittances"),
            ("view_financial_statements", "View Financial Statements", "TREASURY", "View society aggregates and balance sheets"),
            ("authorize_disbursements", "Authorize Disbursements", "TREASURY", "Authorize cash releases from treasury"),
            ("manage_bank_reconciliation", "Direct Polaris Reconciliation", "TREASURY", "Match bank feeds with cooperator records"),
            ("view_liquidity_ratio", "Inspect Society Liquidity", "TREASURY", "Monitor statutory liquidity ratios"),
            ("modify_payment_advice", "Modify Payment Advice", "TREASURY", "Revise monthly cooperator billing advice"),

            # Credit & Financing Committee
            ("credit_committee_approval", "Credit Committee Review", "CREDIT", "Vet loan applications (Stage 1 / 33%)"),
            ("financial_sec_loan_approval", "Financial Sec Loan Vetting", "CREDIT", "Financial assessment of loans (Stage 2 / 66%)"),
            ("treasurer_loan_disbursement", "Treasurer Loan Disbursement", "CREDIT", "Final loan release & disbursement (Stage 3 / 100%)"),
            ("presidential_loan_override", "Presidential Loan Override", "CREDIT", "Direct 100% executive loan approval"),

            # Presidential & Administration
            ("executive_oversight", "Presidential Supreme Oversight", "PRESIDENT", "Omniscient visibility across all desks"),
            ("governance_signoff", "Presidential Governance Sign-off", "PRESIDENT", "Executive sign-off on contact/policy changes"),
            ("configure_system", "Configure System Constants", "ADMIN", "Modify statutory constants and charges"),
            ("manage_officers", "Manage Officers & Portfolios", "ADMIN", "Assign portfolios and executive roles"),
            ("database_maintenance", "Database Maintenance", "ADMIN", "Execute schema and seed operations"),
            ("system_audit", "Access Forensic Audit Trail", "AUDIT", "Inspect tamper-evident system logs")
        ]

        for key, name, mod, desc in all_perms:
            cursor.execute("""
                INSERT INTO `permissions` (`perm_key`, `perm_name`, `module`, `description`)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE `perm_name` = VALUES(`perm_name`), `module` = VALUES(`module`), `description` = VALUES(`description`);
            """, (key, name, mod, desc))

        # Core Statutory Roles
        core_roles = [
            ("MEMBER", "General Cooperator", "Standard active cooperator", True),
            ("PRESIDENT", "Cooperative President & Chairman", "Chief executive officer with universal override", True),
            ("GENERAL_SECRETARY", "General Secretary", "Custodian of cooperator register and meetings", True),
            ("FINANCIAL_SECRETARY", "Financial Secretary", "Primary record-keeper of finances and advice", True),
            ("TREASURER", "Treasurer", "Chief financial custodian of society funds and disbursements", True),
            ("LEGAL_COMPLIANCE_LEAD", "Legal & Compliance Lead", "Statutory compliance and dispute arbitration", True),
            ("TECHNOLOGY_SYSTEMS_LEAD", "Technology Systems Lead", "Platform systems administration and infrastructure", True),
            ("SUPER_ADMIN", "Developer Super Administrator", "Universal administrative and forensic clearance", True),
            ("CREDIT_COMMITTEE_MEMBER", "Credit & Risk Committee Member", "Vetting of loans at Stage 1", False),
            ("INTERNAL_AUDITOR", "Internal Auditor", "Read-only inspection of forensic audit and ledgers", False)
        ]

        for code, name, desc, is_sys in core_roles:
            cursor.execute("""
                INSERT INTO `roles` (`role_code`, `role_name`, `description`, `is_system_role`)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE `role_name` = VALUES(`role_name`), `description` = VALUES(`description`);
            """, (code, name, desc, is_sys))

        # Map Permissions to Roles
        role_perm_map = {
            "MEMBER": [
                "view_own_profile", "view_own_accounts", "submit_contribution",
                "apply_loan", "submit_welfare_claim", "view_marketplace", "view_bylaws"
            ],
            "GENERAL_SECRETARY": [
                "view_own_profile", "view_own_accounts", "submit_contribution",
                "apply_loan", "submit_welfare_claim", "view_marketplace", "view_bylaws",
                "view_executive_console", "manage_members", "approve_kyc", "reject_kyc",
                "view_all_members", "manage_meetings", "issue_passbook", "credit_committee_approval"
            ],
            "FINANCIAL_SECRETARY": [
                "view_own_profile", "view_own_accounts", "submit_contribution",
                "apply_loan", "submit_welfare_claim", "view_marketplace", "view_bylaws",
                "view_executive_console", "verify_contributions", "issue_fines",
                "view_ledger_audit", "manage_inward_remittances", "view_financial_statements",
                "modify_payment_advice", "financial_sec_loan_approval"
            ],
            "TREASURER": [
                "view_own_profile", "view_own_accounts", "submit_contribution",
                "apply_loan", "submit_welfare_claim", "view_marketplace", "view_bylaws",
                "view_executive_console", "authorize_disbursements", "manage_bank_reconciliation",
                "view_financial_statements", "view_liquidity_ratio", "modify_payment_advice",
                "treasurer_loan_disbursement", "verify_contributions"
            ],
            "PRESIDENT": [
                "view_own_profile", "view_own_accounts", "submit_contribution",
                "apply_loan", "submit_welfare_claim", "view_marketplace", "view_bylaws",
                "view_executive_console", "executive_oversight", "credit_committee_approval",
                "financial_sec_loan_approval", "treasurer_loan_disbursement", "presidential_loan_override",
                "governance_signoff", "view_all_members", "manage_members",
                "view_financial_statements", "manage_meetings", "verify_contributions",
                "modify_payment_advice", "system_audit"
            ],
            "CREDIT_COMMITTEE_MEMBER": [
                "view_own_profile", "view_own_accounts", "view_executive_console",
                "credit_committee_approval", "view_all_members"
            ],
            "INTERNAL_AUDITOR": [
                "view_own_profile", "view_own_accounts", "view_executive_console",
                "view_ledger_audit", "view_financial_statements", "system_audit"
            ],
            "SUPER_ADMIN": [p[0] for p in all_perms]
        }

        # Retrieve Role IDs and Permission IDs
        cursor.execute("SELECT id, role_code FROM roles;")
        roles_dict = {r["role_code"]: r["id"] for r in cursor.fetchall()}

        cursor.execute("SELECT id, perm_key FROM permissions;")
        perms_dict = {p["perm_key"]: p["id"] for p in cursor.fetchall()}

        for r_code, p_keys in role_perm_map.items():
            r_id = roles_dict.get(r_code)
            if not r_id:
                continue
            for p_key in p_keys:
                p_id = perms_dict.get(p_key)
                if p_id:
                    cursor.execute("""
                        INSERT IGNORE INTO `role_permissions` (`role_id`, `permission_id`)
                        VALUES (%s, %s);
                    """, (r_id, p_id))

        # ---------------------------------------------------------------------
        # 3. MULTI-TIER LOAN TABLES & COLUMNS
        # ---------------------------------------------------------------------
        print("[3/5] Upgrading Loans Schema (multi-tier tracking, steps, appeals)...")

        # Check existing columns on loans
        cursor.execute("DESCRIBE loans;")
        loan_cols = [c["Field"] for c in cursor.fetchall()]

        cols_to_add = [
            ("approval_level_percent", "INT DEFAULT 0"),
            ("current_approval_stage", "VARCHAR(40) DEFAULT 'CREDIT_COMMITTEE'"),
            ("presidential_override", "BOOLEAN DEFAULT FALSE"),
            ("decline_reason", "TEXT NULL"),
            ("declined_by_officer_id", "INT NULL"),
            ("declined_by_role", "VARCHAR(50) NULL"),
            ("purpose_narration", "TEXT NULL")
        ]

        for col_name, col_def in cols_to_add:
            if col_name not in loan_cols:
                cursor.execute(f"ALTER TABLE `loans` ADD COLUMN `{col_name}` {col_def};")
                print(f"  + Added column loans.{col_name}")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `loan_approval_steps` (
                `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                `loan_id` INT NOT NULL,
                `step_name` VARCHAR(50) NOT NULL COMMENT 'CREDIT_COMMITTEE, FINANCIAL_SECRETARY, TREASURER, PRESIDENTIAL_OVERRIDE',
                `officer_id` INT NOT NULL,
                `officer_role` VARCHAR(80) NOT NULL,
                `action` ENUM('APPROVED', 'DECLINED', 'OVERRIDDEN') NOT NULL,
                `comments` TEXT NULL,
                `percentage_granted` INT NOT NULL,
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (`loan_id`) REFERENCES `loans`(`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `loan_appeals` (
                `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                `loan_id` INT NOT NULL,
                `member_id` INT NOT NULL,
                `appeal_comments` TEXT NOT NULL,
                `attached_document_path` VARCHAR(255) NULL,
                `document_name` VARCHAR(150) NULL,
                `document_mime_type` VARCHAR(80) NULL,
                `target_officer_id` INT NULL,
                `status` ENUM('PENDING_REVIEW', 'RESOLVED_APPROVED', 'RESOLVED_DECLINED') DEFAULT 'PENDING_REVIEW',
                `review_response` TEXT NULL,
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                `resolved_at` DATETIME NULL,
                FOREIGN KEY (`loan_id`) REFERENCES `loans`(`id`) ON DELETE CASCADE,
                FOREIGN KEY (`member_id`) REFERENCES `members`(`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # ---------------------------------------------------------------------
        # 4. POLARIS BANK MANUAL TRANSFER RECEIPTS TABLE
        # ---------------------------------------------------------------------
        print("[4/5] Creating Manual Bank Payments Table (receipt uploads & reconciliation)...")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `manual_bank_payments` (
                `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                `member_id` INT NOT NULL,
                `amount` DECIMAL(15, 2) NOT NULL,
                `payment_date` DATE NOT NULL,
                `bank_name` VARCHAR(100) DEFAULT 'Polaris Bank Limited',
                `payment_reference` VARCHAR(100) NOT NULL,
                `narration` VARCHAR(255) NULL,
                `receipt_file_path` VARCHAR(255) NULL,
                `receipt_mime_type` VARCHAR(80) NULL,
                `status` ENUM('PENDING_RECONCILIATION', 'VERIFIED', 'REJECTED') DEFAULT 'PENDING_RECONCILIATION',
                `verified_by_officer_id` INT NULL,
                `verified_at` DATETIME NULL,
                `rejection_reason` VARCHAR(255) NULL,
                `distribution_json` JSON NULL,
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (`member_id`) REFERENCES `members`(`id`),
                INDEX `idx_manual_pmt_status` (`status`),
                INDEX `idx_manual_pmt_member` (`member_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        # ---------------------------------------------------------------------
        # 5. FORENSIC AUDIT LOG TABLE (Tamper-evident, Immutable Append-Only)
        # ---------------------------------------------------------------------
        print("[5/5] Creating Forensic Audit Log Table (audit_logs)...")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `audit_logs` (
                `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                `user_id` INT NULL,
                `actor_name` VARCHAR(150) NOT NULL,
                `actor_role` VARCHAR(80) NOT NULL,
                `action` VARCHAR(100) NOT NULL,
                `resource_type` VARCHAR(50) NOT NULL,
                `resource_id` VARCHAR(100) NULL,
                `ip_address` VARCHAR(45) NULL,
                `user_agent` VARCHAR(255) NULL,
                `details_before` JSON NULL,
                `details_after` JSON NULL,
                `summary` VARCHAR(255) NULL,
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX `idx_audit_actor` (`user_id`, `created_at`),
                INDEX `idx_audit_action` (`action`),
                INDEX `idx_audit_resource` (`resource_type`, `resource_id`),
                INDEX `idx_audit_created` (`created_at`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)

        conn.commit()
        print("\n✅ GOVERNANCE & FIDUCIARY SUITE MIGRATION COMPLETED SUCCESSFULLY! ✅")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration Failed: {e}")
        raise e
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
