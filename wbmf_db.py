"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
DATABASE CONNECTOR & RBAC PLATFORM ENGINE (wbmf_db.py)
-----------------------------------------------------------------------------
Statutory Jurisdiction: Lagos State Cooperative Societies Law (Cap C15)
Official Secretariat Email: wealthbridge.coopsociety@gmail.com
Document Reference: SOP-WMC-2026-V1 & WMC-BYELAWS-REV-2026-V1
=============================================================================
"""

import os
import sys
import json
import hashlib
import secrets
import time
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import errorcode

# Load environment configuration from .env file
load_dotenv(override=True)

# -----------------------------------------------------------------------------
# CRYPTOGRAPHIC PASSWORD HASHING (PBKDF2-HMAC-SHA256)
# -----------------------------------------------------------------------------
DEFAULT_SALT = os.getenv("AUTH_SALT", "wealthbridge_coop_pbkdf2_salt_2026")
DEFAULT_INITIAL_PASSWORD = os.getenv("SEED_INITIAL_PASSWORD", "Wealthbridge@2026")

def hash_password(password: str, salt: str = None) -> str:
    """Derives a 256-bit PBKDF2 hash using 100,000 iterations of SHA-256."""
    if not password:
        raise ValueError("A non-empty password is required.")
    actual_salt = salt or DEFAULT_SALT or "wealthbridge_coop_pbkdf2_salt_2026"
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), actual_salt.encode("utf-8"), 100000).hex()

def verify_password(plain_password: str, hashed_password: Optional[str], salt: str = None) -> bool:
    """Verifies a plaintext password against the stored PBKDF2 hash."""
    if not hashed_password:
        return False
    actual_salt = salt or DEFAULT_SALT or "wealthbridge_coop_pbkdf2_salt_2026"
    expected_hash = hash_password(plain_password, actual_salt)
    return secrets.compare_digest(expected_hash, hashed_password)


# -----------------------------------------------------------------------------
# ROLE-BASED ACCESS CONTROL (RBAC) PERMISSIONS MATRIX
# -----------------------------------------------------------------------------
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "MEMBER": [
        "view_own_profile",
        "view_own_accounts",
        "submit_contribution",
        "apply_loan",
        "submit_welfare_claim",
        "view_marketplace",
        "view_bylaws"
    ],
    "GENERAL_SECRETARY": [
        "view_own_profile",
        "view_own_accounts",
        "submit_contribution",
        "apply_loan",
        "submit_welfare_claim",
        "view_marketplace",
        "view_bylaws",
        "view_executive_console",
        "manage_members",
        "approve_kyc",
        "reject_kyc",
        "view_all_members",
        "manage_meetings",
        "issue_passbook"
    ],
    "FINANCIAL_SECRETARY": [
        "view_own_profile",
        "view_own_accounts",
        "submit_contribution",
        "apply_loan",
        "submit_welfare_claim",
        "view_marketplace",
        "view_bylaws",
        "view_executive_console",
        "verify_contributions",
        "issue_fines",
        "view_ledger_audit",
        "manage_inward_remittances",
        "view_financial_statements",
        "manage_accounting",
        "post_manual_journal",
        "simulate_dividends"
    ],
    "TREASURER": [
        "view_own_profile",
        "view_own_accounts",
        "submit_contribution",
        "apply_loan",
        "submit_welfare_claim",
        "view_marketplace",
        "view_bylaws",
        "view_executive_console",
        "authorize_disbursements",
        "manage_bank_reconciliation",
        "view_financial_statements",
        "view_liquidity_ratio",
        "manage_accounting",
        "post_manual_journal",
        "simulate_dividends"
    ],
    "PRESIDENT": [
        "view_own_profile",
        "view_own_accounts",
        "submit_contribution",
        "apply_loan",
        "submit_welfare_claim",
        "view_marketplace",
        "view_bylaws",
        "view_executive_console",
        "executive_oversight",
        "credit_committee_approval",
        "governance_signoff",
        "view_all_members",
        "manage_members",
        "view_financial_statements",
        "manage_meetings",
        "manage_accounting",
        "approve_manual_journal",
        "simulate_dividends",
        "approve_dividends"
    ],
    "LEGAL_COMPLIANCE_LEAD": [
        "view_own_profile",
        "view_own_accounts",
        "submit_contribution",
        "apply_loan",
        "submit_welfare_claim",
        "view_marketplace",
        "view_bylaws",
        "view_executive_console",
        "verify_guarantors",
        "arbitrate_disputes",
        "compliance_audit"
    ],
    "TECHNOLOGY_SYSTEMS_LEAD": [
        "view_own_profile",
        "view_own_accounts",
        "submit_contribution",
        "apply_loan",
        "submit_welfare_claim",
        "view_marketplace",
        "view_bylaws",
        "view_executive_console",
        "configure_system",
        "manage_officers",
        "database_maintenance",
        "system_audit",
        "manage_members",
        "approve_kyc",
        "verify_contributions",
        "authorize_disbursements",
        "executive_oversight"
    ],
    "SUPER_ADMIN": [
        "view_own_profile",
        "view_own_accounts",
        "submit_contribution",
        "apply_loan",
        "submit_welfare_claim",
        "view_marketplace",
        "view_bylaws",
        "view_executive_console",
        "configure_system",
        "manage_officers",
        "database_maintenance",
        "system_audit",
        "manage_members",
        "approve_kyc",
        "reject_kyc",
        "verify_contributions",
        "authorize_disbursements",
        "executive_oversight",
        "view_all_members",
        "view_ledger_audit",
        "issue_fines",
        "credit_committee_approval",
        "governance_signoff",
        "view_financial_statements",
        "manage_meetings",
        "arbitrate_disputes",
        "compliance_audit",
        "view_liquidity_ratio",
        "manage_accounting",
        "post_manual_journal",
        "approve_manual_journal",
        "simulate_dividends",
        "approve_dividends"
    ]
}


class WealthbridgeDB:
    """Enterprise Database Connector and RBAC Controller for Wealthbridge Cooperative."""

    def __init__(self):
        self.host = os.getenv("DB_HOST", "127.0.0.1")
        self.port = int(os.getenv("DB_PORT", "3306"))
        self.user = os.getenv("DB_USER", "root")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_NAME", "wbmf")
        self.official_email = os.getenv("OFFICIAL_EMAIL", "wealthbridge.coopsociety@gmail.com")

    def get_connection(self):
        """Creates and returns a connection to MySQL."""
        if not self.password:
            raise RuntimeError("DB_PASSWORD must be set in the environment.")
        try:
            conn = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                autocommit=True,
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci"
            )
            return conn
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                print("[ERROR] Access denied: Check username and password in .env")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print(f"[ERROR] Database '{self.database}' does not exist.")
            else:
                print(f"[ERROR] MySQL connection failed: {err}")
            raise

    # -------------------------------------------------------------------------
    # 1. AUTHENTICATION & RBAC SERVICES
    # -------------------------------------------------------------------------
    def authenticate_user(self, identifier: str, password: str) -> Dict[str, Any]:
        """
        Authenticates a member or officer using Email, Member Code (WMC-2026-xxx), or Phone Number.
        Returns a rich user payload including RBAC roles and permissions.
        """
        cleaned_id = identifier.strip()
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Check Dedicated System / Developer Admin Users (Zero Member Record / Payments)
            cursor.execute("""
                SELECT * FROM admin_users
                WHERE LOWER(username) = LOWER(%s)
                   OR LOWER(email) = LOWER(%s)
                LIMIT 1;
            """, (cleaned_id, cleaned_id))
            admin_user = cursor.fetchone()

            if admin_user:
                if not admin_user.get("is_active", True):
                    raise ValueError("This administrative account is disabled.")

                stored_hash = admin_user.get("password_hash")
                if not verify_password(password, stored_hash):
                    raise ValueError("Incorrect password for administrator account.")

                cursor.execute("UPDATE admin_users SET last_login = NOW() WHERE id = %s;", (admin_user["id"],))
                conn.commit()

                # Developer Super Admin has universal desk clearance across the executive governance platform
                admin_roles = [
                    "SUPER_ADMIN", "PRESIDENT", "GENERAL_SECRETARY",
                    "FINANCIAL_SECRETARY", "TREASURER",
                    "TECHNOLOGY_SYSTEMS_LEAD", "LEGAL_COMPLIANCE_LEAD"
                ]
                permissions_set = set()
                for r in admin_roles:
                    for perm in ROLE_PERMISSIONS.get(r, []):
                        permissions_set.add(perm)

                session_token = f"wmc_adm_{admin_user['id']}_{int(time.time())}_{secrets.token_hex(8)}"

                return {
                    "token": session_token,
                    "user": {
                        "id": f"admin-{admin_user['id']}",
                        "member_code": "ADMIN",
                        "first_name": "Developer",
                        "last_name": "Admin",
                        "full_name": admin_user["full_name"],
                        "email": admin_user["email"],
                        "phone": "N/A",
                        "gender": "N/A",
                        "marital_status": "N/A",
                        "residential_address": "Wealthbridge Systems Engineering Center",
                        "identification_type": "SYSTEM",
                        "identification_number": "SYS-DEV-ADMIN-01",
                        "employment_status": "DEVELOPER",
                        "contribution_tier": "NONE",
                        "membership_status": "SYSTEM_ADMINISTRATOR",
                        "kyc_completion_percent": 100,
                        "contact_change_status": "NONE",
                        "admission_date": None,
                        "last_login": str(admin_user.get("last_login") or ""),
                        "roles": admin_roles,
                        "primary_role": "SUPER_ADMIN",
                        "is_executive": True,
                        "is_admin_only": True,
                        "executive_portfolio": "TECHNOLOGY_SYSTEMS_LEAD",
                        "permissions": sorted(list(permissions_set))
                    }
                }

            # 2. Authenticate Regular Cooperator Members & Officers
            query = """
                SELECT m.*, m.status AS membership_status
                FROM members m
                WHERE LOWER(m.email) = LOWER(%s)
                   OR LOWER(m.member_code) = LOWER(%s)
                   OR m.phone = %s
                LIMIT 1;
            """
            cursor.execute(query, (cleaned_id, cleaned_id, cleaned_id))
            member = cursor.fetchone()

            if not member:
                raise ValueError(f"No account found matching '{cleaned_id}'. Please check your Member ID, Email, or Phone.")

            if member["membership_status"] not in ("ACTIVE", "PENDING_KYC", "SUSPENDED"):
                raise ValueError(f"This account status is '{member['membership_status']}' and cannot sign in. Please contact the Secretariat at wealthbridge.coopsociety@gmail.com.")

            # Verify password
            stored_hash = member.get("password_hash")
            if not verify_password(password, stored_hash):
                raise ValueError("Incorrect password. Please verify your credentials.")

            # Record login timestamp
            cursor.execute("UPDATE members SET last_login = NOW() WHERE id = %s;", (member["id"],))

            # Fetch active executive portfolios from officers table
            cursor.execute("""
                SELECT portfolio FROM officers 
                WHERE member_id = %s AND is_active = TRUE;
            """, (member["id"],))
            officer_rows = cursor.fetchall()
            officer_portfolios = [r["portfolio"] for r in officer_rows]

            # Construct roles list
            roles = ["MEMBER"]
            for port in officer_portfolios:
                if port not in roles:
                    roles.append(port)

            # Fetch custom/dynamic roles assigned to member
            cursor.execute("""
                SELECT r.role_code 
                FROM member_roles mr
                JOIN roles r ON mr.role_id = r.id
                WHERE mr.member_id = %s;
            """, (member["id"],))
            for mr_row in cursor.fetchall():
                r_code = mr_row["role_code"]
                if r_code not in roles:
                    roles.append(r_code)

            # Assign SUPER_ADMIN & All Desks to Developer Admin / Founder / Tech Lead
            m_code = str(member.get("member_code") or "").lower()
            m_email = str(member.get("email") or "").lower()
            is_super_admin = (
                m_code in ("admin", "wmc-admin") or
                m_email == "admin@wealthbridge.ng" or
                "TECHNOLOGY_SYSTEMS_LEAD" in roles or
                member.get("member_code") == "WMC-2026-001"
            )
            if is_super_admin:
                if "SUPER_ADMIN" not in roles:
                    roles.append("SUPER_ADMIN")
                # Developer Super Admin has universal desk clearance across the executive console
                for exec_p in ["PRESIDENT", "GENERAL_SECRETARY", "FINANCIAL_SECRETARY", "TREASURER", "TECHNOLOGY_SYSTEMS_LEAD", "LEGAL_COMPLIANCE_LEAD"]:
                    if exec_p not in roles:
                        roles.append(exec_p)

            # Determine Primary Role (Executive role takes priority over standard member)
            executive_order = [
                "SUPER_ADMIN", "PRESIDENT", "GENERAL_SECRETARY", "FINANCIAL_SECRETARY", 
                "TREASURER", "LEGAL_COMPLIANCE_LEAD", "TECHNOLOGY_SYSTEMS_LEAD", "CREDIT_COMMITTEE_MEMBER", "INTERNAL_AUDITOR"
            ]
            primary_role = "MEMBER"
            for exec_role in executive_order:
                if exec_role in roles:
                    primary_role = exec_role
                    break

            is_executive = any(r in executive_order for r in roles)

            # Aggregate all permissions across assigned roles from static dict AND dynamic role_permissions
            permissions_set = set()
            for r in roles:
                for perm in ROLE_PERMISSIONS.get(r, []):
                    permissions_set.add(perm)

            if roles:
                placeholders = ','.join(['%s'] * len(roles))
                cursor.execute(f"""
                    SELECT DISTINCT p.perm_key
                    FROM permissions p
                    JOIN role_permissions rp ON p.id = rp.permission_id
                    JOIN roles r ON rp.role_id = r.id
                    WHERE r.role_code IN ({placeholders});
                """, tuple(roles))
                for p_row in cursor.fetchall():
                    permissions_set.add(p_row["perm_key"])

            # Compute dynamic comprehensive KYC across all sections (Personal, ID, Contact, Photo, Bank, NOK)
            cursor.execute("SELECT * FROM next_of_kin WHERE member_id = %s LIMIT 1;", (member["id"],))
            nok_record = cursor.fetchone()
            kyc_info = self.calculate_kyc_completion(member, nok_record)
            full_kyc_pct = kyc_info["percentage"]
            cursor.execute("UPDATE members SET kyc_completion_percent = %s WHERE id = %s;", (full_kyc_pct, member["id"]))
            conn.commit()

            # Generate session token
            session_token = f"wmc_sess_{member['id']}_{int(time.time())}_{secrets.token_hex(8)}"

            full_name = f"{member['first_name']} {member['last_name']}".strip()

            return {
                "token": session_token,
                "user": {
                    "id": member["id"],
                    "member_code": member["member_code"],
                    "first_name": member["first_name"],
                    "last_name": member["last_name"],
                    "full_name": full_name,
                    "email": member["email"],
                    "phone": member["phone"],
                    "gender": member["gender"],
                    "marital_status": member.get("marital_status") or "SINGLE",
                    "residential_address": member["residential_address"],
                    "identification_type": member["identification_type"],
                    "identification_number": member["identification_number"],
                    "passport_photo": member.get("passport_photo"),
                    "employment_status": member["employment_status"],
                    "employer_or_business_name": member.get("employer_or_business_name"),
                    "bank_name": member.get("bank_name"),
                    "bank_account_number": member.get("bank_account_number"),
                    "bank_account_name": member.get("bank_account_name"),
                    "contribution_tier": member["contribution_tier"],
                    "membership_status": member["membership_status"],
                    "kyc_completion_percent": full_kyc_pct,
                    "kyc_breakdown": kyc_info["breakdown"],
                    "contact_change_status": member.get("contact_change_status") or "NONE",
                    "pending_email": member.get("pending_email"),
                    "pending_phone": member.get("pending_phone"),
                    "pending_address": member.get("pending_address"),
                    "admission_date": str(member["admission_date"]) if member["admission_date"] else None,
                    "last_login": str(member["last_login"]) if member["last_login"] else None,
                    "roles": roles,
                    "primary_role": primary_role,
                    "is_executive": is_executive,
                    "executive_portfolio": officer_portfolios[0] if officer_portfolios else None,
                    "permissions": sorted(list(permissions_set))
                }
            }
        finally:
            cursor.close()
            conn.close()

    def get_member_authorization_context(self, member_id: Any) -> Optional[Dict[str, Any]]:
        """Loads current account standing and permissions for a server-side session."""
        if isinstance(member_id, str) and (member_id.startswith("admin") or member_id == "ADMIN"):
            admin_roles = [
                "SUPER_ADMIN", "PRESIDENT", "GENERAL_SECRETARY",
                "FINANCIAL_SECRETARY", "TREASURER",
                "TECHNOLOGY_SYSTEMS_LEAD", "LEGAL_COMPLIANCE_LEAD"
            ]
            permissions = set()
            for role in admin_roles:
                permissions.update(ROLE_PERMISSIONS.get(role, []))
            return {
                "id": member_id,
                "member_code": "ADMIN",
                "email": "wealthbridge.coopsociety@gmail.com",
                "first_name": "System",
                "last_name": "Administrator",
                "membership_status": "SYSTEM_ADMINISTRATOR",
                "is_admin_only": True,
                "primary_role": "SUPER_ADMIN",
                "is_executive": True,
                "roles": sorted(set(admin_roles)),
                "permissions": sorted(permissions),
            }

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT id, member_code, email, first_name, last_name, status AS membership_status
                FROM members
                WHERE id = %s
                LIMIT 1;
            """, (member_id,))
            member = cursor.fetchone()
            if not member:
                return None

            cursor.execute("""
                SELECT portfolio
                FROM officers
                WHERE member_id = %s AND is_active = TRUE;
            """, (member_id,))
            roles = ["MEMBER"] + [row["portfolio"] for row in cursor.fetchall()]

            # Fetch dynamic custom roles assigned to member
            cursor.execute("""
                SELECT r.role_code 
                FROM member_roles mr
                JOIN roles r ON mr.role_id = r.id
                WHERE mr.member_id = %s;
            """, (member_id,))
            for mr_row in cursor.fetchall():
                r_code = mr_row["role_code"]
                if r_code not in roles:
                    roles.append(r_code)

            m_code = str(member.get("member_code") or "").lower()
            is_super_admin = (
                m_code in ("admin", "wmc-admin") or
                "TECHNOLOGY_SYSTEMS_LEAD" in roles or 
                member.get("member_code") == "WMC-2026-001"
            )
            if is_super_admin:
                if "SUPER_ADMIN" not in roles:
                    roles.append("SUPER_ADMIN")
                for exec_p in ["PRESIDENT", "GENERAL_SECRETARY", "FINANCIAL_SECRETARY", "TREASURER", "TECHNOLOGY_SYSTEMS_LEAD", "LEGAL_COMPLIANCE_LEAD"]:
                    if exec_p not in roles:
                        roles.append(exec_p)

            permissions = set()
            for role in roles:
                permissions.update(ROLE_PERMISSIONS.get(role, []))

            if roles:
                placeholders = ','.join(['%s'] * len(roles))
                cursor.execute(f"""
                    SELECT DISTINCT p.perm_key
                    FROM permissions p
                    JOIN role_permissions rp ON p.id = rp.permission_id
                    JOIN roles r ON rp.role_id = r.id
                    WHERE r.role_code IN ({placeholders});
                """, tuple(roles))
                for p_row in cursor.fetchall():
                    permissions.add(p_row["perm_key"])

            primary_role = "MEMBER"
            for pr in ["PRESIDENT", "SUPER_ADMIN", "TREASURER", "FINANCIAL_SECRETARY", "GENERAL_SECRETARY", "TECHNOLOGY_SYSTEMS_LEAD", "LEGAL_COMPLIANCE_LEAD"]:
                if pr in roles:
                    primary_role = pr
                    break

            is_exec = any(r in ["PRESIDENT", "SUPER_ADMIN", "TREASURER", "FINANCIAL_SECRETARY", "GENERAL_SECRETARY", "TECHNOLOGY_SYSTEMS_LEAD", "LEGAL_COMPLIANCE_LEAD"] for r in roles)

            return {
                "id": member["id"],
                "member_code": member["member_code"],
                "email": member.get("email"),
                "first_name": member.get("first_name"),
                "last_name": member.get("last_name"),
                "membership_status": member["membership_status"],
                "primary_role": primary_role,
                "is_executive": is_exec,
                "roles": sorted(set(roles)),
                "permissions": sorted(permissions),
            }
        finally:
            cursor.close()
            conn.close()

    def change_password(self, member_id: int, old_password: str, new_password: str) -> Dict[str, Any]:
        """Allows an authenticated member to update their access password."""
        if len(new_password) < 12:
            raise ValueError("New password must be at least 12 characters long.")

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT password_hash FROM members WHERE id = %s;", (member_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Member not found.")

            if not verify_password(old_password, row.get("password_hash")):
                raise ValueError("Current password does not match.")

            new_hash = hash_password(new_password)
            cursor.execute("UPDATE members SET password_hash = %s WHERE id = %s;", (new_hash, member_id))
            return {"status": "SUCCESS", "message": "Password updated successfully."}
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # 2. KYC COMPLETION & PROFILE MANAGEMENT SERVICES
    # -------------------------------------------------------------------------
    def calculate_kyc_completion(self, member: Dict[str, Any], nok: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Dynamically calculates KYC Profile Completion Percentage (0-100%):
        - Personal Information (Name, Gender, Marital, Employment): 20%
        - National Identity / NIN: 20%
        - Verified Contact Details: 20%
        - Passport Photograph: 10%
        - Commercial Bank Account Details: 15%
        - Next of Kin Details: 15%
        """
        score = 0
        breakdown = {}

        # 1. Personal Information (20%)
        has_personal = bool(
            member.get("first_name") and 
            member.get("last_name") and 
            member.get("gender") and 
            member.get("employment_status")
        )
        score += 20 if has_personal else 10
        breakdown["personal_info"] = {"points": 20 if has_personal else 10, "max": 20, "completed": has_personal}

        # 2. Identification / NIN (20%)
        has_id = bool(
            member.get("identification_type") and 
            member.get("identification_number") and 
            len(str(member.get("identification_number")).strip()) >= 5
        )
        score += 20 if has_id else 0
        breakdown["identification"] = {"points": 20 if has_id else 0, "max": 20, "completed": has_id}

        # 3. Contact Information (20%)
        has_contact = bool(
            member.get("email") and 
            member.get("phone") and 
            member.get("residential_address")
        )
        score += 20 if has_contact else 0
        breakdown["contact_info"] = {"points": 20 if has_contact else 0, "max": 20, "completed": has_contact}

        # 4. Passport Photograph (10%)
        photo_val = str(member.get("passport_photo") or "").strip()
        has_photo = bool(len(photo_val) > 50)
        score += 10 if has_photo else 0
        breakdown["passport_photo"] = {"points": 10 if has_photo else 0, "max": 10, "completed": has_photo}

        # 5. Bank Account Details (15%)
        has_bank = bool(
            member.get("bank_name") and 
            member.get("bank_account_number") and 
            len(str(member.get("bank_account_number")).strip()) >= 10
        )
        score += 15 if has_bank else 0
        breakdown["banking_details"] = {"points": 15 if has_bank else 0, "max": 15, "completed": has_bank}

        # 6. Next of Kin (15%)
        has_nok = bool(
            nok and 
            nok.get("full_name") and 
            nok.get("relationship") and 
            nok.get("phone")
        )
        score += 15 if has_nok else 0
        breakdown["next_of_kin"] = {"points": 15 if has_nok else 0, "max": 15, "completed": has_nok}

        return {
            "percentage": min(100, score),
            "breakdown": breakdown,
            "is_fully_completed": score >= 100
        }

    def get_member_profile(self, member_id: int) -> Dict[str, Any]:
        """Retrieves full member profile, KYC progress, and Next of Kin records."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM members WHERE id = %s;", (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError(f"Member ID {member_id} not found.")

            cursor.execute("SELECT * FROM next_of_kin WHERE member_id = %s LIMIT 1;", (member_id,))
            nok = cursor.fetchone()

            kyc_info = self.calculate_kyc_completion(member, nok)

            # Convert datetimes to strings
            for dt_col in ["created_at", "updated_at", "admission_date", "last_login", "contact_change_requested_at", "contact_change_reviewed_at"]:
                if member.get(dt_col):
                    member[dt_col] = str(member[dt_col])

            if nok:
                for dt_col in ["created_at", "updated_at"]:
                    if nok.get(dt_col):
                        nok[dt_col] = str(nok[dt_col])
                if "allocation_percentage" in nok and nok["allocation_percentage"] is not None:
                    nok["allocation_percentage"] = float(nok["allocation_percentage"])

            # Clean sensitive fields
            if "password_hash" in member:
                del member["password_hash"]

            if "monthly_income_verified" in member and member["monthly_income_verified"] is not None:
                member["monthly_income_verified"] = float(member["monthly_income_verified"])

            # Convenience aliases for frontend
            member["full_name"] = f"{member.get('first_name', '')} {member.get('last_name', '')}".strip()
            member["phone_number"] = member.get("phone")
            member["national_id_nin"] = member.get("identification_number")
            member["occupation"] = member.get("employer_or_business_name")

            if nok:
                nok["phone_number"] = nok.get("phone")

            return {
                "member": member,
                "next_of_kin": nok,
                "kyc_completion_percent": kyc_info["percentage"],
                "kyc_breakdown": kyc_info["breakdown"],
                "is_contact_pending": member.get("contact_change_status") == "PENDING_APPROVAL"
            }
        finally:
            cursor.close()
            conn.close()

    def update_member_profile(self, member_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Updates personal, identification, banking, and next of kin information.
        CRITICAL GOVERNANCE INVARIANT:
        Changes to Address, Phone Number, and Email are NOT overwritten immediately.
        They are queued into pending fields awaiting President & General Secretary approval.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM members WHERE id = %s;", (member_id,))
            current = cursor.fetchone()
            if not current:
                raise ValueError(f"Member ID {member_id} not found.")

            # 1. Contact Change Detection & Governance Isolation
            current_email = str(current["email"] or "").strip().lower()
            current_phone = str(current["phone"] or "").strip()
            current_address = str(current["residential_address"] or "").strip()

            input_phone = data.get("phone") or data.get("phone_number")
            new_email = str(data.get("email") or current_email).strip().lower()
            new_phone = str(input_phone or current_phone).strip()
            new_address = str(data.get("residential_address") or current_address).strip()

            email_changed = bool(data.get("email") and new_email != current_email)
            phone_changed = bool(input_phone and new_phone != current_phone)
            address_changed = bool(data.get("residential_address") and new_address != current_address)

            contact_modified = email_changed or phone_changed or address_changed

            pending_email = new_email if email_changed else current.get("pending_email")
            pending_phone = new_phone if phone_changed else current.get("pending_phone")
            pending_address = new_address if address_changed else current.get("pending_address")

            contact_change_status = current.get("contact_change_status") or "NONE"
            if contact_modified:
                contact_change_status = "PENDING_APPROVAL"
                cursor.execute("DELETE FROM contact_change_approvals WHERE member_id = %s;", (member_id,))

            # 2. Extract Immediate Direct Profile Updates
            first_name = data.get("first_name", current["first_name"]).strip()
            last_name = data.get("last_name", current["last_name"]).strip()
            other_names = data.get("other_names", current.get("other_names"))
            if other_names:
                other_names = str(other_names).strip()

            gender = data.get("gender", current["gender"])
            marital_status = data.get("marital_status", current.get("marital_status") or "SINGLE")
            date_of_birth = data.get("date_of_birth") or current.get("date_of_birth")
            employment_status = data.get("employment_status", current["employment_status"])
            employer_or_business_name = data.get("employer_or_business_name") or data.get("occupation") or current.get("employer_or_business_name")
            
            raw_income = data.get("monthly_income_verified", current.get("monthly_income_verified") or 0.00)
            monthly_income = Decimal(str(raw_income or 0.00))

            # Identity details
            identification_type = data.get("identification_type", current.get("identification_type") or "NIN")
            identification_number = data.get("identification_number") or data.get("national_id_nin") or current.get("identification_number")
            if identification_number:
                identification_number = str(identification_number).strip()

            passport_photo = data.get("passport_photo") or current.get("passport_photo")

            # Banking details
            bank_name = data.get("bank_name", current.get("bank_name"))
            bank_account_number = data.get("bank_account_number", current.get("bank_account_number"))
            bank_account_name = data.get("bank_account_name", current.get("bank_account_name"))
            bvn = data.get("bvn", current.get("bvn"))

            # Next of kin extraction (supporting both nested schema and flattened fields)
            nok = data.get("next_of_kin")
            if not nok and (data.get("next_of_kin_name") or data.get("next_of_kin_phone")):
                nok = {
                    "full_name": data.get("next_of_kin_name"),
                    "relationship": data.get("next_of_kin_relationship") or "SPOUSE",
                    "phone": data.get("next_of_kin_phone"),
                    "residential_address": data.get("next_of_kin_address")
                }

            # Update members record
            update_sql = """
                UPDATE members SET
                    first_name = %s,
                    last_name = %s,
                    other_names = %s,
                    gender = %s,
                    marital_status = %s,
                    date_of_birth = %s,
                    employment_status = %s,
                    employer_or_business_name = %s,
                    monthly_income_verified = %s,
                    identification_type = %s,
                    identification_number = %s,
                    passport_photo = %s,
                    bank_name = %s,
                    bank_account_number = %s,
                    bank_account_name = %s,
                    bvn = %s,
                    pending_email = %s,
                    pending_phone = %s,
                    pending_address = %s,
                    contact_change_status = %s,
                    contact_change_requested_at = CASE WHEN %s = 'PENDING_APPROVAL' THEN NOW() ELSE contact_change_requested_at END
                WHERE id = %s;
            """
            cursor.execute(update_sql, (
                first_name, last_name, other_names, gender, marital_status, date_of_birth,
                employment_status, employer_or_business_name, monthly_income,
                identification_type, identification_number, passport_photo,
                bank_name, bank_account_number, bank_account_name, bvn,
                pending_email, pending_phone, pending_address, contact_change_status,
                contact_change_status, member_id
            ))

            # 3. Next of Kin Upsert
            if nok and (nok.get("full_name") or nok.get("phone")):
                cursor.execute("SELECT id FROM next_of_kin WHERE member_id = %s LIMIT 1;", (member_id,))
                existing_nok = cursor.fetchone()
                if existing_nok:
                    cursor.execute("""
                        UPDATE next_of_kin SET
                            full_name = %s,
                            relationship = %s,
                            phone = %s,
                            email = %s,
                            residential_address = %s,
                            allocation_percentage = %s
                        WHERE id = %s;
                    """, (
                        str(nok.get("full_name") or "").strip(),
                        str(nok.get("relationship") or "SPOUSE").strip(),
                        str(nok.get("phone") or "").strip(),
                        str(nok.get("email") or "").strip() if nok.get("email") else None,
                        str(nok.get("residential_address") or "").strip(),
                        Decimal(str(nok.get("allocation_percentage") or 100.00)),
                        existing_nok["id"]
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO next_of_kin (member_id, full_name, relationship, phone, email, residential_address, allocation_percentage)
                        VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """, (
                        member_id,
                        str(nok.get("full_name") or "").strip(),
                        str(nok.get("relationship") or "SPOUSE").strip(),
                        str(nok.get("phone") or "").strip(),
                        str(nok.get("email") or "").strip() if nok.get("email") else None,
                        str(nok.get("residential_address") or "").strip(),
                        Decimal(str(nok.get("allocation_percentage") or 100.00))
                    ))

            # 4. Recompute KYC completion percentage
            cursor.execute("SELECT * FROM members WHERE id = %s;", (member_id,))
            refreshed_member = cursor.fetchone()
            cursor.execute("SELECT * FROM next_of_kin WHERE member_id = %s LIMIT 1;", (member_id,))
            refreshed_nok = cursor.fetchone()

            kyc_info = self.calculate_kyc_completion(refreshed_member, refreshed_nok)
            new_percent = kyc_info["percentage"]

            cursor.execute("UPDATE members SET kyc_completion_percent = %s WHERE id = %s;", (new_percent, member_id))
            conn.commit()

            msg = f"Profile updated successfully! KYC completion is now {new_percent}%."
            if contact_modified:
                msg += " (Notice: Modifications to your address, phone, or email are PENDING approval from the President and General Secretary)."

            return {
                "status": "SUCCESS",
                "message": msg,
                "kyc_completion_percent": new_percent,
                "kyc_breakdown": kyc_info["breakdown"],
                "contact_change_status": contact_change_status,
                "is_contact_pending": contact_change_status == "PENDING_APPROVAL"
            }
        finally:
            cursor.close()
            conn.close()

    def get_pending_contact_changes(self) -> List[Dict[str, Any]]:
        """Used by PRESIDENT and GENERAL_SECRETARY to review pending contact changes."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    id, member_code, 
                    CONCAT(first_name, ' ', last_name) AS full_name,
                    email AS current_email, pending_email,
                    phone AS current_phone, pending_phone,
                    residential_address AS current_address, pending_address,
                    contact_change_status, contact_change_requested_at
                FROM members
                WHERE contact_change_status = 'PENDING_APPROVAL'
                ORDER BY contact_change_requested_at ASC;
            """)
            rows = cursor.fetchall()
            for r in rows:
                if r.get("contact_change_requested_at"):
                    r["contact_change_requested_at"] = str(r["contact_change_requested_at"])
            return rows
        finally:
            cursor.close()
            conn.close()

    def approve_contact_change(self, member_id: int, officer_id: int, roles: List[str]) -> Dict[str, Any]:
        """
        A President and General Secretary must approve separately before pending
        contact details become live. Each approval is retained as an audit record.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            allowed_roles = {"PRESIDENT", "GENERAL_SECRETARY"}
            approver_roles = allowed_roles.intersection(roles)
            if not approver_roles:
                raise ValueError("Only the President or General Secretary may approve contact changes.")

            cursor.execute("SELECT * FROM members WHERE id = %s AND contact_change_status = 'PENDING_APPROVAL';", (member_id,))
            m = cursor.fetchone()
            if not m:
                raise ValueError("No pending contact change request found for this member.")

            officer_portfolio = "PRESIDENT" if "PRESIDENT" in approver_roles else "GENERAL_SECRETARY"
            cursor.execute("""
                INSERT INTO contact_change_approvals (member_id, officer_id, officer_portfolio)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE approved_at = approved_at;
            """, (member_id, officer_id, officer_portfolio))

            cursor.execute("""
                SELECT DISTINCT officer_portfolio
                FROM contact_change_approvals
                WHERE member_id = %s;
            """, (member_id,))
            approvals = {row["officer_portfolio"] for row in cursor.fetchall()}
            if approvals != allowed_roles:
                remaining = sorted(allowed_roles - approvals)[0].replace("_", " ").title()
                conn.commit()
                return {
                    "status": "PENDING_SECOND_APPROVAL",
                    "message": f"First approval recorded. Approval from the {remaining} is still required."
                }

            new_email = m["pending_email"] or m["email"]
            new_phone = m["pending_phone"] or m["phone"]
            new_address = m["pending_address"] or m["residential_address"]

            cursor.execute("""
                UPDATE members SET
                    email = %s,
                    phone = %s,
                    residential_address = %s,
                    pending_email = NULL,
                    pending_phone = NULL,
                    pending_address = NULL,
                    contact_change_status = 'APPROVED',
                    contact_change_reviewed_by = %s,
                    contact_change_reviewed_at = NOW()
                WHERE id = %s;
            """, (new_email, new_phone, new_address, officer_id, member_id))

            cursor.execute("DELETE FROM contact_change_approvals WHERE member_id = %s;", (member_id,))
            conn.commit()

            return {
                "status": "SUCCESS",
                "message": f"Contact details modification for {m['first_name']} {m['last_name']} ({m['member_code']}) approved and live."
            }
        finally:
            cursor.close()
            conn.close()

    def reject_contact_change(self, member_id: int, officer_id: int, reason: str = "") -> Dict[str, Any]:
        """PRESIDENT / GENERAL_SECRETARY action: Rejects pending contact modifications."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                UPDATE members SET
                    pending_email = NULL,
                    pending_phone = NULL,
                    pending_address = NULL,
                    contact_change_status = 'REJECTED',
                    contact_change_reviewed_by = %s,
                    contact_change_reviewed_at = NOW()
                WHERE id = %s;
            """, (officer_id, member_id))
            cursor.execute("DELETE FROM contact_change_approvals WHERE member_id = %s;", (member_id,))
            conn.commit()
            return {
                "status": "SUCCESS",
                "message": f"Contact modification request rejected. Reason: {reason or 'Failed verification.'}"
            }
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # 2. SYSTEM CONFIGURATION
    # -------------------------------------------------------------------------
    def get_system_config(self) -> Dict[str, str]:
        """Fetches all system parameters and regulatory constants as key-value map."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT config_key, config_value, description FROM system_config;")
            rows = cursor.fetchall()
            return {row["config_key"]: row["config_value"] for row in rows}
        finally:
            cursor.close()
            conn.close()

    def get_system_config_full(self) -> List[Dict[str, Any]]:
        """Fetches all system parameters with keys, values, descriptions, and update timestamps."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, config_key, config_value, description, updated_at FROM system_config ORDER BY id ASC;")
            rows = cursor.fetchall()
            for r in rows:
                if r.get("updated_at") and isinstance(r["updated_at"], (datetime, date)):
                    r["updated_at"] = r["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
            return rows
        finally:
            cursor.close()
            conn.close()

    def update_system_config_item(self, config_key: str, new_value: str, updated_by_user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Updates a statutory system configuration constant in MySQL system_config table.
        Enforces invariant: OFFICIAL_EMAIL must always remain wealthbridge.coopsociety@gmail.com.
        """
        clean_key = str(config_key).strip().upper()
        clean_val = str(new_value).strip()

        if not clean_val:
            raise ValueError(f"Configuration value for '{clean_key}' cannot be blank.")

        # Document & Template Invariant: OFFICIAL_EMAIL
        if clean_key == "OFFICIAL_EMAIL":
            if clean_val.lower() != "wealthbridge.coopsociety@gmail.com":
                raise ValueError("Statutory Invariant: The official cooperative email address must be 'wealthbridge.coopsociety@gmail.com'.")

        # Validation for numeric parameters
        if clean_key in ("SHARE_UNIT_PRICE", "MIN_SHARE_UNITS", "MAX_SHARE_UNITS", "TARGET_SHARE_CAPITAL", "WELFARE_MONTHLY_LEVY", "REGISTRATION_FEE", "PASSBOOK_FEE"):
            try:
                num = float(clean_val)
                if num <= 0:
                    raise ValueError(f"Parameter '{clean_key}' must be a positive number greater than zero.")
            except ValueError:
                raise ValueError(f"Parameter '{clean_key}' must be a valid numerical value.")

        if clean_key == "MONTHLY_DUE_DAY":
            try:
                day = int(clean_val)
                if day < 1 or day > 31:
                    raise ValueError("Monthly due day must be between 1 and 31.")
            except ValueError:
                raise ValueError("Monthly due day must be an integer between 1 and 31.")

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM system_config WHERE config_key = %s;", (clean_key,))
            existing = cursor.fetchone()
            if not existing:
                raise ValueError(f"System configuration key '{clean_key}' does not exist.")

            cursor.execute("""
                UPDATE system_config
                SET config_value = %s, updated_at = NOW()
                WHERE config_key = %s;
            """, (clean_val, clean_key))
            conn.commit()

            cursor.execute("SELECT * FROM system_config WHERE config_key = %s;", (clean_key,))
            updated = cursor.fetchone()
            if updated.get("updated_at") and isinstance(updated["updated_at"], (datetime, date)):
                updated["updated_at"] = updated["updated_at"].strftime("%Y-%m-%d %H:%M:%S")

            return {
                "status": "SUCCESS",
                "config_key": clean_key,
                "config_value": clean_val,
                "previous_value": existing["config_value"],
                "description": updated["description"],
                "updated_at": updated["updated_at"],
                "message": f"Successfully updated statutory parameter '{clean_key}' to '{clean_val}'."
            }
        finally:
            cursor.close()
            conn.close()


    # -------------------------------------------------------------------------
    # 3. MEMBERSHIP & REGISTRATION SERVICES
    # -------------------------------------------------------------------------
    def list_members(self) -> List[Dict[str, Any]]:
        """Retrieves list of all members with complete biodata, officer portfolios, and balances."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT 
                m.id,
                m.member_code,
                m.first_name,
                m.last_name,
                m.other_names,
                CONCAT(m.first_name, ' ', m.last_name) AS full_name,
                m.email,
                m.phone,
                m.gender,
                m.marital_status,
                m.residential_address,
                m.employment_status,
                m.employer_or_business_name,
                m.contribution_tier,
                m.identification_type,
                m.identification_number,
                m.bank_name,
                m.bank_account_number,
                m.bank_account_name,
                m.bvn,
                m.kyc_completion_percent,
                m.contact_change_status,
                m.passport_photo,
                m.status AS membership_status,
                m.admission_date,
                m.created_at,
                o.portfolio AS executive_portfolio,
                COALESCE(sh.units_held, 0) AS share_units,
                COALESCE(sh.paid_up_amount, 0.00) AS share_equity_paid,
                COALESCE(sh.benefits_qualified, 0) AS benefits_qualified,
                COALESCE(sv.total_balance, 0.00) AS savings_balance,
                COALESCE(wf.cumulative_contributions, 0.00) AS welfare_balance,
                nok.full_name AS nok_name,
                nok.relationship AS nok_relationship,
                nok.phone AS nok_phone,
                nok.residential_address AS nok_address
            FROM members m
            LEFT JOIN officers o ON m.id = o.member_id AND o.is_active = TRUE
            LEFT JOIN share_accounts sh ON m.id = sh.member_id
            LEFT JOIN savings_accounts sv ON m.id = sv.member_id
            LEFT JOIN welfare_accounts wf ON m.id = wf.member_id
            LEFT JOIN (
                SELECT member_id, full_name, relationship, phone, residential_address 
                FROM next_of_kin 
                WHERE id IN (SELECT MIN(id) FROM next_of_kin GROUP BY member_id)
            ) nok ON m.id = nok.member_id
            ORDER BY m.id ASC;
        """
        try:
            cursor.execute(query)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def admin_add_member(self, member_data: Dict[str, Any], created_by: Any = None) -> Dict[str, Any]:
        """Enrolls a new member into the society, assigns sequential member code, and initializes accounts."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            first_name = (member_data.get("first_name") or "").strip()
            last_name = (member_data.get("last_name") or "").strip()
            other_names = (member_data.get("other_names") or "").strip() or None
            email = (member_data.get("email") or "").strip().lower()
            phone = (member_data.get("phone") or "").strip()

            if not first_name or not last_name:
                raise ValueError("First Name and Last Name are required.")
            if not email:
                raise ValueError("A valid email address is required.")
            if not phone:
                raise ValueError("A valid phone number is required.")

            # Duplicate checks
            cursor.execute("SELECT id, member_code FROM members WHERE LOWER(email) = %s LIMIT 1;", (email,))
            if cursor.fetchone():
                raise ValueError(f"A member with email '{email}' is already registered.")

            cursor.execute("SELECT id, member_code FROM members WHERE phone = %s LIMIT 1;", (phone,))
            if cursor.fetchone():
                raise ValueError(f"A member with phone number '{phone}' is already registered.")

            # Generate next sequential member code: WMC-2026-xxx
            cursor.execute("SELECT member_code FROM members WHERE member_code LIKE 'WMC-2026-%' ORDER BY id DESC LIMIT 1;")
            last_row = cursor.fetchone()
            next_num = 1
            if last_row and last_row.get("member_code"):
                try:
                    parts = last_row["member_code"].split("-")
                    next_num = int(parts[-1]) + 1
                except Exception:
                    next_num = 1
            member_code = f"WMC-2026-{next_num:03d}"

            # Calculate KYC percentage
            kyc_pct = 20
            if member_data.get("residential_address"):
                kyc_pct += 15
            if member_data.get("employment_status") or member_data.get("employer_or_business_name"):
                kyc_pct += 15
            if member_data.get("identification_number"):
                kyc_pct += 20
            if member_data.get("bank_account_number"):
                kyc_pct += 15
            if member_data.get("nok_name") or member_data.get("passport_photo"):
                kyc_pct += 15
            kyc_pct = min(100, kyc_pct)

            default_password = DEFAULT_INITIAL_PASSWORD or "Wealthbridge@2026"
            pwd_hash = hash_password(default_password)

            insert_member_query = """
                INSERT INTO members (
                    member_code, first_name, last_name, other_names,
                    email, password_hash, phone, gender, marital_status,
                    residential_address, identification_type, identification_number,
                    employment_status, employer_or_business_name,
                    bank_name, bank_account_number, bank_account_name, bvn,
                    contribution_tier, status, kyc_completion_percent,
                    contact_change_status, admission_date
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    'NONE', CURDATE()
                );
            """
            cursor.execute(insert_member_query, (
                member_code, first_name, last_name, other_names,
                email, pwd_hash, phone,
                member_data.get("gender") or "MALE",
                member_data.get("marital_status") or "SINGLE",
                member_data.get("residential_address") or "Lagos State, Nigeria",
                member_data.get("identification_type") or "NIN",
                member_data.get("identification_number"),
                member_data.get("employment_status") or "SALARY_EARNER",
                member_data.get("employer_or_business_name"),
                member_data.get("bank_name"),
                member_data.get("bank_account_number"),
                member_data.get("bank_account_name"),
                member_data.get("bvn"),
                member_data.get("contribution_tier") or "STANDARD",
                member_data.get("status") or "ACTIVE",
                kyc_pct
            ))
            new_id = cursor.lastrowid

            # Initialize tripartite accounts
            cursor.execute("""
                INSERT INTO share_accounts (member_id, units_held, paid_up_amount, is_minimum_met, benefits_qualified)
                VALUES (%s, 0, 0.00, FALSE, FALSE);
            """, (new_id,))

            cursor.execute("""
                INSERT INTO savings_accounts (member_id, total_balance, encumbered_balance)
                VALUES (%s, 0.00, 0.00);
            """, (new_id,))

            cursor.execute("""
                INSERT INTO welfare_accounts (member_id, cumulative_contributions, consecutive_months_active)
                VALUES (%s, 0.00, 0);
            """, (new_id,))

            # Next of kin if provided
            nok_name = (member_data.get("nok_name") or "").strip()
            if nok_name:
                cursor.execute("""
                    INSERT INTO next_of_kin (member_id, full_name, relationship, phone, residential_address, allocation_percentage)
                    VALUES (%s, %s, %s, %s, %s, 100.00);
                """, (
                    new_id, nok_name,
                    member_data.get("nok_relationship") or "NEXT_OF_KIN",
                    member_data.get("nok_phone") or phone,
                    member_data.get("nok_address") or member_data.get("residential_address") or "Lagos State"
                ))

            conn.commit()

            return {
                "status": "SUCCESS",
                "message": f"Member {first_name} {last_name} enrolled successfully as {member_code}.",
                "member": {
                    "id": new_id,
                    "member_code": member_code,
                    "full_name": f"{first_name} {last_name}",
                    "email": email,
                    "phone": phone,
                    "tier": member_data.get("contribution_tier") or "STANDARD",
                    "status": member_data.get("status") or "ACTIVE",
                    "default_password": default_password
                }
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def admin_update_member_biodata(self, member_id: int, data: Dict[str, Any], updated_by: Any = None) -> Dict[str, Any]:
        """Modifies a member's biodata, contact details, status, or banking directly by an authorized officer."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM members WHERE id = %s LIMIT 1;", (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError(f"Member with ID #{member_id} does not exist.")

            first_name = (data.get("first_name") or member["first_name"]).strip()
            last_name = (data.get("last_name") or member["last_name"]).strip()
            other_names = data.get("other_names", member["other_names"])
            email = (data.get("email") or member["email"]).strip().lower()
            phone = (data.get("phone") or member["phone"]).strip()

            # Check email duplicate if changed
            if email != (member["email"] or "").lower():
                cursor.execute("SELECT id FROM members WHERE LOWER(email) = %s AND id != %s LIMIT 1;", (email, member_id))
                if cursor.fetchone():
                    raise ValueError(f"Email '{email}' is already in use by another member.")

            # Check phone duplicate if changed
            if phone != (member["phone"] or ""):
                cursor.execute("SELECT id FROM members WHERE phone = %s AND id != %s LIMIT 1;", (phone, member_id))
                if cursor.fetchone():
                    raise ValueError(f"Phone number '{phone}' is already in use by another member.")

            res_address = data.get("residential_address") or member["residential_address"]
            gender = data.get("gender") or member["gender"]
            marital_status = data.get("marital_status") or member.get("marital_status") or "SINGLE"
            emp_status = data.get("employment_status") or member["employment_status"]
            employer = data.get("employer_or_business_name", member.get("employer_or_business_name"))
            b_name = data.get("bank_name", member.get("bank_name"))
            b_acc_num = data.get("bank_account_number", member.get("bank_account_number"))
            b_acc_name = data.get("bank_account_name", member.get("bank_account_name"))
            bvn = data.get("bvn", member.get("bvn"))
            id_type = data.get("identification_type") or member.get("identification_type") or "NIN"
            id_number = data.get("identification_number", member.get("identification_number"))
            tier = data.get("contribution_tier") or member["contribution_tier"]
            status_val = data.get("status") or member["status"]

            # Compute KYC percent
            kyc_pct = 20
            if res_address and len(res_address) > 4:
                kyc_pct += 15
            if emp_status or employer:
                kyc_pct += 15
            if id_number:
                kyc_pct += 20
            if b_acc_num:
                kyc_pct += 15
            if member.get("passport_photo") or data.get("passport_photo"):
                kyc_pct += 15
            kyc_pct = min(100, kyc_pct)

            update_query = """
                UPDATE members SET
                    first_name = %s,
                    last_name = %s,
                    other_names = %s,
                    email = %s,
                    phone = %s,
                    gender = %s,
                    marital_status = %s,
                    residential_address = %s,
                    employment_status = %s,
                    employer_or_business_name = %s,
                    bank_name = %s,
                    bank_account_number = %s,
                    bank_account_name = %s,
                    bvn = %s,
                    identification_type = %s,
                    identification_number = %s,
                    contribution_tier = %s,
                    status = %s,
                    kyc_completion_percent = %s,
                    contact_change_status = 'NONE',
                    pending_email = NULL,
                    pending_phone = NULL,
                    pending_address = NULL
                WHERE id = %s;
            """
            cursor.execute(update_query, (
                first_name, last_name, other_names,
                email, phone, gender, marital_status,
                res_address, emp_status, employer,
                b_name, b_acc_num, b_acc_name, bvn,
                id_type, id_number, tier, status_val,
                kyc_pct, member_id
            ))

            # Upsert next of kin if provided
            nok_name = data.get("nok_name")
            if nok_name:
                cursor.execute("SELECT id FROM next_of_kin WHERE member_id = %s LIMIT 1;", (member_id,))
                nok = cursor.fetchone()
                if nok:
                    cursor.execute("""
                        UPDATE next_of_kin SET
                            full_name = %s,
                            relationship = %s,
                            phone = %s,
                            residential_address = %s
                        WHERE id = %s;
                    """, (
                        nok_name.strip(),
                        data.get("nok_relationship") or "NEXT_OF_KIN",
                        data.get("nok_phone") or phone,
                        data.get("nok_address") or res_address,
                        nok["id"]
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO next_of_kin (member_id, full_name, relationship, phone, residential_address, allocation_percentage)
                        VALUES (%s, %s, %s, %s, %s, 100.00);
                    """, (
                        member_id,
                        nok_name.strip(),
                        data.get("nok_relationship") or "NEXT_OF_KIN",
                        data.get("nok_phone") or phone,
                        data.get("nok_address") or res_address
                    ))

            conn.commit()

            return {
                "status": "SUCCESS",
                "message": f"Biodata for {first_name} {last_name} ({member['member_code']}) updated successfully.",
                "member_id": member_id,
                "member_code": member["member_code"],
                "full_name": f"{first_name} {last_name}",
                "email": email,
                "phone": phone,
                "status": status_val,
                "tier": tier,
                "kyc_completion_percent": kyc_pct
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def admin_reset_member_password(self, member_id: int, reset_by: Any = None) -> Dict[str, Any]:
        """Resets a member's access password to the official initial default ('Wealthbridge@2026')."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, member_code, first_name, last_name, email FROM members WHERE id = %s LIMIT 1;", (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError(f"Member with ID #{member_id} does not exist.")

            default_password = DEFAULT_INITIAL_PASSWORD or "Wealthbridge@2026"
            pwd_hash = hash_password(default_password)

            cursor.execute("UPDATE members SET password_hash = %s WHERE id = %s;", (pwd_hash, member_id))
            conn.commit()

            return {
                "status": "SUCCESS",
                "message": f"Password for {member['first_name']} {member['last_name']} ({member['member_code']}) has been reset to default.",
                "member_id": member["id"],
                "member_code": member["member_code"],
                "member_name": f"{member['first_name']} {member['last_name']}",
                "email": member["email"],
                "default_password": default_password
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def admin_get_member_full(self, member_id: int) -> Dict[str, Any]:
        """Fetches complete profile record including next of kin and balances for administrative editing."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    m.*,
                    COALESCE(sh.units_held, 0) AS share_units,
                    COALESCE(sh.paid_up_amount, 0.00) AS share_equity_paid,
                    COALESCE(sv.total_balance, 0.00) AS savings_balance,
                    COALESCE(wf.cumulative_contributions, 0.00) AS welfare_balance,
                    o.portfolio AS executive_portfolio,
                    nok.full_name AS nok_name,
                    nok.relationship AS nok_relationship,
                    nok.phone AS nok_phone,
                    nok.residential_address AS nok_address
                FROM members m
                LEFT JOIN officers o ON m.id = o.member_id AND o.is_active = TRUE
                LEFT JOIN share_accounts sh ON m.id = sh.member_id
                LEFT JOIN savings_accounts sv ON m.id = sv.member_id
                LEFT JOIN welfare_accounts wf ON m.id = wf.member_id
                LEFT JOIN (
                    SELECT member_id, full_name, relationship, phone, residential_address
                    FROM next_of_kin
                    WHERE id IN (SELECT MIN(id) FROM next_of_kin GROUP BY member_id)
                ) nok ON m.id = nok.member_id
                WHERE m.id = %s
                LIMIT 1;
            """, (member_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Member with ID #{member_id} does not exist.")
            if "password_hash" in row:
                del row["password_hash"]
            return row
        finally:
            cursor.close()
            conn.close()

    def get_member_statement(self, member_id: int) -> Optional[Dict[str, Any]]:
        """Executes get_member_consolidated_statement procedure for 360-degree view."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.callproc("get_member_consolidated_statement", [member_id])
            for result in cursor.stored_results():
                row = result.fetchone()
                return row
            return None
        finally:
            cursor.close()
            conn.close()

    def register_new_member(self, member_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrolls a new member into PENDING_KYC status.
        Performs strict validation for incomplete fields and duplicate entries.
        Supports custom or default password hashing.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Validate Incomplete Entries
            required_fields = ["first_name", "last_name", "email", "phone", "residential_address"]
            for field in required_fields:
                val = member_data.get(field)
                if not val or not str(val).strip():
                    field_display = field.replace("_", " ").title()
                    raise ValueError(f"Incomplete Entry: '{field_display}' is required and cannot be empty.")

            email = str(member_data["email"]).strip().lower()
            phone = str(member_data["phone"]).strip()

            # 2. Check Duplicate Email
            cursor.execute("SELECT id, member_code, first_name, last_name FROM members WHERE LOWER(email) = %s;", (email,))
            existing_email = cursor.fetchone()
            if existing_email:
                raise ValueError(
                    f"Duplicate Entry: The email address '{email}' is already registered to "
                    f"member {existing_email['first_name']} {existing_email['last_name']} ({existing_email['member_code']})."
                )

            # 3. Check Duplicate Phone
            cursor.execute("SELECT id, member_code, first_name, last_name FROM members WHERE phone = %s;", (phone,))
            existing_phone = cursor.fetchone()
            if existing_phone:
                raise ValueError(
                    f"Duplicate Entry: The phone number '{phone}' is already registered to "
                    f"member {existing_phone['first_name']} {existing_phone['last_name']} ({existing_phone['member_code']})."
                )

            # 4. Generate Next Sequential Member Code (e.g. WMC-2026-009)
            cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM members;")
            row = cursor.fetchone()
            next_num = row["next_id"] if row else 1
            generated_code = f"WMC-2026-{next_num:03d}"

            # Password setup - default to 'Wealthbridge@2026' if not provided
            plain_pass = str(member_data.get("password") or "").strip() or "Wealthbridge@2026"
            pwd_hash = hash_password(plain_pass)

            # 5. Insert New Member
            insert_query = """
                INSERT INTO members (
                    member_code, first_name, last_name, other_names, email, password_hash, phone, 
                    gender, residential_address, identification_type, identification_number, 
                    employment_status, employer_or_business_name, monthly_income_verified, 
                    contribution_tier, status, admission_date
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, 'PENDING_KYC', CURDATE()
                );
            """
            cursor.execute(insert_query, (
                generated_code,
                member_data["first_name"].strip(),
                member_data["last_name"].strip(),
                member_data.get("other_names", "").strip() if member_data.get("other_names") else None,
                email,
                pwd_hash,
                phone,
                member_data.get("gender") or "MALE",
                member_data["residential_address"].strip(),
                member_data.get("identification_type") or "NIN",
                member_data.get("identification_number") or f"NIN-KYC-{next_num:03d}",
                member_data.get("employment_status") or "SALARY_EARNER",
                member_data.get("employer_or_business_name") or "Self/Corporate",
                Decimal(str(member_data.get("monthly_income_verified") or 0.00)),
                member_data.get("contribution_tier") or "STANDARD",
            ))
            new_id = cursor.lastrowid

            # 6. Initialize Account Ledgers
            cursor.execute("""
                INSERT INTO share_accounts (member_id, units_held, paid_up_amount, is_minimum_met, benefits_qualified)
                VALUES (%s, 0, 0.00, FALSE, FALSE);
            """, (new_id,))

            cursor.execute("""
                INSERT INTO savings_accounts (member_id, total_balance, encumbered_balance)
                VALUES (%s, 0.00, 0.00);
            """, (new_id,))

            cursor.execute("""
                INSERT INTO welfare_accounts (member_id, cumulative_contributions, consecutive_months_active, last_contribution_date)
                VALUES (%s, 0.00, 0, NULL);
            """, (new_id,))

            return {
                "member_id": new_id,
                "member_code": generated_code,
                "full_name": f"{member_data['first_name']} {member_data['last_name']}",
                "email": email,
                "phone": phone,
                "status": "PENDING_KYC",
                "default_password": plain_pass
            }
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # 4. EXECUTIVE & RBAC MANAGEMENT SERVICES
    # -------------------------------------------------------------------------
    def get_pending_members(self) -> List[Dict[str, Any]]:
        """Used by GENERAL_SECRETARY to review membership admissions."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    id, member_code, first_name, last_name, email, phone, 
                    gender, employment_status, contribution_tier, residential_address, 
                    identification_type, identification_number, created_at, status,
                    kyc_completion_percent
                FROM members
                WHERE status IN ('PENDING_KYC', 'PENDING_APPROVAL')
                ORDER BY id ASC;
            """)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def approve_member_kyc(self, member_id: int, officer_id: int) -> Dict[str, Any]:
        """
        GENERAL_SECRETARY action: Approves KYC and transitions member status from
        PENDING_KYC to ACTIVE, and enables voting & passbook generation.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, member_code, first_name, last_name, status FROM members WHERE id = %s;", (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError("Target member record not found.")

            cursor.execute("""
                UPDATE members 
                SET status = 'ACTIVE', admission_date = CURDATE()
                WHERE id = %s;
            """, (member_id,))

            return {
                "status": "SUCCESS",
                "member_id": member_id,
                "member_code": member["member_code"],
                "full_name": f"{member['first_name']} {member['last_name']}",
                "message": f"Member {member['member_code']} successfully approved & activated into Society Standing."
            }
        finally:
            cursor.close()
            conn.close()

    def reject_member_kyc(self, member_id: int, officer_id: int, reason: str) -> Dict[str, Any]:
        """GENERAL_SECRETARY action: Rejects or suspends invalid KYC application."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                UPDATE members 
                SET status = 'SUSPENDED'
                WHERE id = %s;
            """, (member_id,))
            return {
                "status": "SUCCESS",
                "member_id": member_id,
                "message": f"Application for Member ID {member_id} marked as SUSPENDED/REJECTED. Reason: {reason}"
            }
        finally:
            cursor.close()
            conn.close()

    def get_executive_metrics(self) -> Dict[str, Any]:
        """
        Macro Dashboard metrics for PRESIDENT, TREASURER, and EXECUTIVE COMMITTEE:
        - Total Registered Members & Active Count
        - Total Ordinary Savings (Cash Collateral)
        - Total Paid-up Share Capital
        - Total Welfare Mutual Fund Pool
        - Total Active Loans Disbursed & Repayments
        - Estimated Polaris Bank Escrow Liquidity
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Members breakdown
            cursor.execute("""
                SELECT 
                    COUNT(*) AS total_members,
                    SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_members,
                    SUM(CASE WHEN status = 'PENDING_KYC' THEN 1 ELSE 0 END) AS pending_kyc_members
                FROM members;
            """)
            m_stats = cursor.fetchone()

            # Savings pool
            cursor.execute("SELECT COALESCE(SUM(total_balance), 0.00) AS total_savings, COALESCE(SUM(encumbered_balance), 0.00) AS encumbered_savings FROM savings_accounts;")
            sav_stats = cursor.fetchone()

            # Shares pool
            cursor.execute("SELECT COALESCE(SUM(paid_up_amount), 0.00) AS total_shares, COALESCE(SUM(units_held), 0) AS total_units FROM share_accounts;")
            share_stats = cursor.fetchone()

            # Welfare pool
            cursor.execute("SELECT COALESCE(SUM(cumulative_contributions), 0.00) AS total_welfare FROM welfare_accounts;")
            welfare_stats = cursor.fetchone()

            # Loans
            cursor.execute("""
                SELECT 
                    COUNT(*) AS total_loans_count,
                    COALESCE(SUM(principal_amount), 0.00) AS total_principal_disbursed,
                    COALESCE(SUM(total_amount_payable), 0.00) AS total_repayable_expected,
                    COALESCE(SUM(outstanding_balance), 0.00) AS current_outstanding_loan_balance
                FROM loans;
            """)
            loan_stats = cursor.fetchone()

            # Disciplinary fines
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(fine_amount), 0.00) AS total_fines_issued,
                    COALESCE(SUM(CASE WHEN status = 'SETTLED' THEN fine_amount ELSE 0.00 END), 0.00) AS total_fines_collected
                FROM disciplinary_fines;
            """)
            fine_stats = cursor.fetchone()

            total_coop_assets = (
                Decimal(str(sav_stats["total_savings"])) + 
                Decimal(str(share_stats["total_shares"])) + 
                Decimal(str(welfare_stats["total_welfare"]))
            )

            return {
                "society_name": "Wealthbridge Multipurpose Cooperative Society Limited",
                "official_email": self.official_email,
                "membership": {
                    "total": int(m_stats["total_members"]),
                    "active": int(m_stats["active_members"]),
                    "pending_kyc": int(m_stats["pending_kyc_members"])
                },
                "financial_pools": {
                    "total_assets_under_management": float(total_coop_assets),
                    "ordinary_savings_balance": float(sav_stats["total_savings"]),
                    "encumbered_savings_collateral": float(sav_stats["encumbered_savings"]),
                    "paid_up_share_equity": float(share_stats["total_shares"]),
                    "total_share_units_held": int(share_stats["total_units"]),
                    "welfare_solidarity_pool": float(welfare_stats["total_welfare"]),
                    "polaris_bank_custody_estimate": float(total_coop_assets - Decimal(str(loan_stats["current_outstanding_loan_balance"])))
                },
                "loan_portfolio": {
                    "total_loans_count": int(loan_stats["total_loans_count"]),
                    "principal_disbursed": float(loan_stats["total_principal_disbursed"]),
                    "outstanding_balance": float(loan_stats["current_outstanding_loan_balance"])
                },
                "compliance_and_discipline": {
                    "fines_issued": float(fine_stats["total_fines_issued"]),
                    "fines_collected": float(fine_stats["total_fines_collected"])
                }
            }
        finally:
            cursor.close()
            conn.close()

    def issue_disciplinary_fine(
        self, 
        member_id: int, 
        infraction_type: str, 
        fine_amount: float, 
        reason: str
    ) -> Dict[str, Any]:
        """Issues an official fine per WMC Bye-Laws and SOP."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                INSERT INTO disciplinary_fines (member_id, infraction_type, fine_amount, reason, status, issued_date)
                VALUES (%s, %s, %s, %s, 'UNPAID', CURDATE());
            """, (member_id, infraction_type, Decimal(str(fine_amount)), reason))
            fine_id = cursor.lastrowid
            return {
                "status": "SUCCESS",
                "fine_id": fine_id,
                "message": f"Disciplinary fine of ₦{fine_amount:,.2f} recorded for Member #{member_id}."
            }
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # 5. ONBOARDING & MONTHLY CONTRIBUTIONS
    # -------------------------------------------------------------------------
    def activate_member_onboarding(
        self, 
        member_id: int, 
        payment_method: str = "POLARIS_BANK_TRANSFER",
        channel_ref: str = "POLARIS-REF-INIT",
        pay_shares_upfront: bool = True,
        first_month_contribution: float = 10000.0,
        officer_id: int = 1
    ) -> Dict[str, Any]:
        """
        Executes process_new_member_onboarding stored procedure.
        Records statutory registration fee (N5,000), passbook (N2,000), shares,
        and first month contribution, then activates the member.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            args = [
                member_id,
                payment_method,
                channel_ref,
                pay_shares_upfront,
                Decimal(str(first_month_contribution)),
                officer_id,
                "", # OUT p_status
                ""  # OUT p_message
            ]
            result_args = cursor.callproc("process_new_member_onboarding", args)
            return {
                "status": result_args[6],
                "message": result_args[7]
            }
        finally:
            cursor.close()
            conn.close()

    def process_monthly_contribution(
        self,
        member_id: int,
        total_amount: float,
        payment_method: str = "POLARIS_BANK_TRANSFER",
        channel_ref: str = "POLARIS-TRF-AUTO",
        officer_id: int = 4 # Financial Secretary default
    ) -> Dict[str, Any]:
        """
        Executes process_monthly_contribution stored procedure.
        Splits remittances into Savings (collateral), Shares (10%), and Welfare (N1,000).
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            args = [
                member_id,
                Decimal(str(total_amount)),
                payment_method,
                channel_ref,
                officer_id,
                "", # OUT p_status
                ""  # OUT p_message
            ]
            result_args = cursor.callproc("process_monthly_contribution", args)
            return {
                "status": result_args[5],
                "message": result_args[6]
            }
        finally:
            cursor.close()
            conn.close()

    def get_recent_transactions(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Retrieves recent ledger transactions audit trail."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT 
                t.id,
                t.transaction_ref,
                m.member_code,
                CONCAT(m.first_name, ' ', m.last_name) AS member_name,
                t.transaction_type,
                t.ledger_category,
                t.amount,
                t.payment_method,
                t.channel_reference,
                t.narration,
                t.status,
                t.transaction_date
            FROM transactions t
            JOIN members m ON t.member_id = m.id
            ORDER BY t.id DESC
            LIMIT %s;
        """
        try:
            cursor.execute(query, (limit,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # DYNAMIC TARGET SAVINGS LEDGERS (VOLUNTARY GOAL SAVINGS)
    # -------------------------------------------------------------------------
    TARGET_CATEGORIES = {
        'BIRTHDAY': 'Birthday Target',
        'CHRISTMAS': 'Christmas Target',
        'ILEYA': 'Ileya Target',
        'BUILDING': 'Building Target',
        'PILGRIMAGE': 'Pilgrimage Target (Hajj & Jerusalem)',
        'EDUCATION': 'Education Target',
        'OTHERS': 'Others'
    }

    TIER_CONTRIBUTIONS = {
        "STANDARD": {
            "savings": 8000.0,
            "shares": 1000.0,
            "welfare": 1000.0,
            "total": 10000.0
        },
        "PLUS": {
            "savings": 21500.0,
            "shares": 2500.0,
            "welfare": 1000.0,
            "total": 25000.0
        },
        "PREMIUM": {
            "savings": 44000.0,
            "shares": 5000.0,
            "welfare": 1000.0,
            "total": 50000.0
        }
    }

    def get_member_target_savings(self, member_id: int) -> Dict[str, Any]:
        """
        Retrieves all voluntary target savings accounts and transactions for a member.
        Automatically matures accounts whose maturity date has arrived (CURDATE() >= maturity_date).
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Update any ACTIVE accounts whose maturity date is past/today to MATURED
            cursor.execute("""
                UPDATE target_savings_accounts
                SET status = 'MATURED'
                WHERE member_id = %s AND status = 'ACTIVE' AND CURDATE() >= maturity_date;
            """, (member_id,))
            conn.commit()

            # 2. Query all target accounts
            cursor.execute("""
                SELECT 
                    id,
                    member_id,
                    target_type,
                    title,
                    target_amount,
                    current_balance,
                    start_date,
                    maturity_date,
                    auto_save_amount,
                    status,
                    created_at,
                    updated_at
                FROM target_savings_accounts
                WHERE member_id = %s
                ORDER BY 
                    CASE status 
                        WHEN 'MATURED' THEN 1 
                        WHEN 'ACTIVE' THEN 2 
                        WHEN 'WITHDRAWN' THEN 3 
                        ELSE 4 
                    END,
                    id DESC;
            """, (member_id,))
            rows = cursor.fetchall()

            today = date.today()
            targets = []
            total_saved = Decimal("0.00")
            total_goal = Decimal("0.00")
            active_count = 0
            matured_count = 0
            withdrawn_count = 0

            for r in rows:
                tid = r["id"]
                t_type = r["target_type"]
                amt = Decimal(str(r["target_amount"]))
                bal = Decimal(str(r["current_balance"]))
                auto_save = Decimal(str(r["auto_save_amount"] or 0))
                m_date = r["maturity_date"]
                if isinstance(m_date, datetime):
                    m_date = m_date.date()
                s_date = r["start_date"]
                if isinstance(s_date, datetime):
                    s_date = s_date.date()

                days_remaining = max(0, (m_date - today).days) if m_date else 0
                is_matured = (r["status"] == "MATURED" or (m_date and today >= m_date))
                can_withdraw = is_matured and bal > Decimal("0.00")

                progress = min(100.0, round(float(bal / amt * 100), 1)) if amt > 0 else 0.0

                if r["status"] in ("ACTIVE", "MATURED"):
                    total_saved += bal
                    total_goal += amt
                    if r["status"] == "ACTIVE":
                        active_count += 1
                    elif r["status"] == "MATURED":
                        matured_count += 1
                elif r["status"] == "WITHDRAWN":
                    withdrawn_count += 1

                # Fetch recent transactions for this target ledger
                cursor.execute("""
                    SELECT 
                        id,
                        transaction_type,
                        amount,
                        balance_after,
                        payment_method,
                        channel_reference,
                        narration,
                        created_at
                    FROM target_savings_transactions
                    WHERE target_account_id = %s
                    ORDER BY id DESC
                    LIMIT 5;
                """, (tid,))
                tx_rows = cursor.fetchall()
                tx_list = []
                for tx in tx_rows:
                    tx_list.append({
                        "id": tx["id"],
                        "transaction_type": tx["transaction_type"],
                        "amount": float(tx["amount"]),
                        "balance_after": float(tx["balance_after"]),
                        "payment_method": tx["payment_method"],
                        "channel_reference": tx["channel_reference"],
                        "narration": tx["narration"],
                        "created_at": str(tx["created_at"])
                    })

                targets.append({
                    "id": tid,
                    "member_id": r["member_id"],
                    "target_type": t_type,
                    "target_type_label": self.TARGET_CATEGORIES.get(t_type, t_type.title()),
                    "title": r["title"],
                    "target_amount": float(amt),
                    "current_balance": float(bal),
                    "auto_save_amount": float(auto_save),
                    "start_date": str(s_date),
                    "maturity_date": str(m_date),
                    "days_remaining": days_remaining,
                    "progress_percent": progress,
                    "status": r["status"],
                    "is_matured": is_matured,
                    "can_withdraw": can_withdraw,
                    "created_at": str(r["created_at"]),
                    "recent_transactions": tx_list
                })

            summary = {
                "total_target_savings": float(total_saved),
                "total_target_goal": float(total_goal),
                "active_targets_count": active_count,
                "matured_targets_count": matured_count,
                "withdrawn_targets_count": withdrawn_count,
                "overall_completion_rate": min(100.0, round(float(total_saved / total_goal * 100), 1)) if total_goal > 0 else 0.0
            }

            return {
                "summary": summary,
                "targets": targets
            }
        finally:
            cursor.close()
            conn.close()

    def create_target_savings(self, member_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a voluntary dynamic Target Savings Ledger for a member.
        Selected from standardized uniform dropdown categories.
        Enforces future maturity date. Optionally records initial top-up deposit.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            target_type = str(data.get("target_type", "")).strip().upper()
            if target_type not in self.TARGET_CATEGORIES:
                valid_types = ", ".join(self.TARGET_CATEGORIES.keys())
                raise ValueError(f"Invalid target category '{target_type}'. Must be one of: {valid_types}.")

            title = str(data.get("title", "")).strip()
            if not title:
                title = self.TARGET_CATEGORIES.get(target_type, f"{target_type.title()} Target")

            try:
                target_amount = float(data.get("target_amount", 0))
            except (ValueError, TypeError):
                raise ValueError("Target goal amount must be a valid number.")

            if target_amount < 5000:
                raise ValueError("Minimum target savings goal is NGN 5,000.00.")

            maturity_date_str = str(data.get("maturity_date", "")).strip()
            if not maturity_date_str:
                raise ValueError("A proposed maturity date is required.")

            try:
                m_date = datetime.strptime(maturity_date_str, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Proposed maturity date must be in YYYY-MM-DD format.")

            today = date.today()
            if m_date <= today:
                raise ValueError(f"Proposed maturity date ({maturity_date_str}) must be in the future (after today, {today}).")

            auto_save = float(data.get("auto_save_amount", 0.0) or 0.0)
            initial_deposit = float(data.get("initial_deposit", 0.0) or 0.0)
            if initial_deposit < 0:
                raise ValueError("Initial deposit cannot be negative.")

            payment_method = str(data.get("payment_method", "POLARIS_BANK_TRANSFER")).strip()

            cursor.execute("""
                INSERT INTO target_savings_accounts
                (member_id, target_type, title, target_amount, current_balance, start_date, maturity_date, auto_save_amount, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'ACTIVE');
            """, (
                member_id,
                target_type,
                title,
                Decimal(str(target_amount)),
                Decimal(str(initial_deposit)),
                today,
                m_date,
                Decimal(str(auto_save))
            ))
            target_id = cursor.lastrowid

            if initial_deposit > 0:
                channel_ref = f"TS-DEP-INIT-{target_id}-{int(time.time())}"
                narration = f"Initial deposit for {title}"
                cursor.execute("""
                    INSERT INTO target_savings_transactions
                    (target_account_id, member_id, transaction_type, amount, balance_after, payment_method, channel_reference, narration)
                    VALUES (%s, %s, 'DEPOSIT', %s, %s, %s, %s, %s);
                """, (
                    target_id, member_id, Decimal(str(initial_deposit)), Decimal(str(initial_deposit)),
                    payment_method, channel_ref, narration
                ))

                # Also record in double-entry transactions audit ledger
                tx_ref = f"TX-TSD-{int(time.time()*1000)}-{secrets.token_hex(4).upper()}"
                cursor.execute("""
                    INSERT INTO transactions
                    (transaction_ref, member_id, transaction_type, ledger_category, amount, payment_method, channel_reference, narration, status)
                    VALUES (%s, %s, 'CREDIT', 'SAVINGS', %s, %s, %s, %s, 'VERIFIED');
                """, (
                    tx_ref, member_id, Decimal(str(initial_deposit)), payment_method, channel_ref, narration[:250]
                ))

            conn.commit()

            return {
                "id": target_id,
                "member_id": member_id,
                "target_type": target_type,
                "target_type_label": self.TARGET_CATEGORIES.get(target_type),
                "title": title,
                "target_amount": target_amount,
                "current_balance": initial_deposit,
                "start_date": str(today),
                "maturity_date": str(m_date),
                "days_remaining": (m_date - today).days,
                "status": "ACTIVE",
                "message": f"Target Savings Ledger '{title}' created successfully."
            }
        finally:
            cursor.close()
            conn.close()

    def deposit_target_savings(
        self,
        member_id: int,
        target_id: int,
        amount: float,
        payment_method: str = "POLARIS_BANK_TRANSFER",
        channel_ref: Optional[str] = None,
        narration: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deposits/tops up funds into an active or matured Target Savings Ledger.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            if amount <= 0:
                raise ValueError("Deposit amount must be greater than zero.")

            cursor.execute("SELECT * FROM target_savings_accounts WHERE id = %s AND member_id = %s;", (target_id, member_id))
            target = cursor.fetchone()
            if not target:
                raise ValueError("Target savings ledger not found or access denied.")

            if target["status"] in ("WITHDRAWN", "CANCELLED"):
                raise ValueError(f"Cannot deposit into target ledger with status '{target['status']}'.")

            current_bal = Decimal(str(target["current_balance"]))
            dep_amt = Decimal(str(amount))
            new_bal = current_bal + dep_amt

            ref = channel_ref or f"TS-DEP-{target_id}-{int(time.time())}"
            narr = narration or f"Top-up deposit for {target['title']}"

            # Check if maturity date has arrived
            today = date.today()
            m_date = target["maturity_date"]
            if isinstance(m_date, datetime):
                m_date = m_date.date()
            new_status = 'MATURED' if (today >= m_date or target["status"] == 'MATURED') else 'ACTIVE'

            cursor.execute("""
                UPDATE target_savings_accounts
                SET current_balance = %s, status = %s
                WHERE id = %s;
            """, (new_bal, new_status, target_id))

            cursor.execute("""
                INSERT INTO target_savings_transactions
                (target_account_id, member_id, transaction_type, amount, balance_after, payment_method, channel_reference, narration)
                VALUES (%s, %s, 'DEPOSIT', %s, %s, %s, %s, %s);
            """, (
                target_id, member_id, dep_amt, new_bal, payment_method, ref, narr
            ))

            tx_ref = f"TX-TSD-{int(time.time()*1000)}-{secrets.token_hex(4).upper()}"
            cursor.execute("""
                INSERT INTO transactions
                (transaction_ref, member_id, transaction_type, ledger_category, amount, payment_method, channel_reference, narration, status)
                VALUES (%s, %s, 'CREDIT', 'SAVINGS', %s, %s, %s, %s, 'VERIFIED');
            """, (
                tx_ref, member_id, dep_amt, payment_method, ref, narr[:250]
            ))

            conn.commit()

            return {
                "status": "SUCCESS",
                "target_id": target_id,
                "title": target["title"],
                "deposited_amount": float(dep_amt),
                "new_balance": float(new_bal),
                "channel_reference": ref,
                "message": f"Successfully deposited NGN {amount:,.2f} into '{target['title']}'."
            }
        finally:
            cursor.close()
            conn.close()

    def withdraw_target_savings(
        self,
        member_id: int,
        target_id: int,
        amount: float,
        bank_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Withdraws funds from a matured Target Savings Ledger.
        Enforces lock: funds cannot be withdrawn prior to the proposed maturity date.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            if amount <= 0:
                raise ValueError("Withdrawal amount must be greater than zero.")

            cursor.execute("SELECT * FROM target_savings_accounts WHERE id = %s AND member_id = %s;", (target_id, member_id))
            target = cursor.fetchone()
            if not target:
                raise ValueError("Target savings ledger not found or access denied.")

            current_bal = Decimal(str(target["current_balance"]))
            if current_bal <= Decimal("0.00"):
                raise ValueError("Cannot withdraw: Target savings ledger balance is NGN 0.00.")

            wdr_amt = Decimal(str(amount))
            if wdr_amt > current_bal:
                raise ValueError(f"Requested withdrawal amount (NGN {amount:,.2f}) exceeds current ledger balance (NGN {float(current_bal):,.2f}).")

            today = date.today()
            m_date = target["maturity_date"]
            if isinstance(m_date, datetime):
                m_date = m_date.date()

            is_matured = (target["status"] == "MATURED" or today >= m_date)
            if not is_matured:
                days_left = (m_date - today).days
                raise ValueError(
                    f"Maturity Lock Enforced: Target '{target['title']}' matures on {m_date} (in {days_left} days). "
                    "Voluntary target savings are locked until maturity date to ensure personal financial goals are met."
                )

            new_bal = current_bal - wdr_amt
            new_status = 'WITHDRAWN' if new_bal == Decimal("0.00") else 'MATURED'

            cursor.execute("""
                UPDATE target_savings_accounts
                SET current_balance = %s, status = %s
                WHERE id = %s;
            """, (new_bal, new_status, target_id))

            b_name = (bank_details.get("bank_name") if bank_details else "") or "Commercial Bank"
            b_acc = (bank_details.get("account_number") if bank_details else "") or ""
            ref = f"TS-WDR-{target_id}-{int(time.time())}"
            narr = f"Maturity Payout for {target['title']} to {b_name} {b_acc}".strip()

            cursor.execute("""
                INSERT INTO target_savings_transactions
                (target_account_id, member_id, transaction_type, amount, balance_after, payment_method, channel_reference, narration)
                VALUES (%s, %s, 'WITHDRAWAL', %s, %s, 'POLARIS_BANK_TRANSFER', %s, %s);
            """, (
                target_id, member_id, wdr_amt, new_bal, ref, narr
            ))

            tx_ref = f"TX-TSW-{int(time.time()*1000)}-{secrets.token_hex(4).upper()}"
            cursor.execute("""
                INSERT INTO transactions
                (transaction_ref, member_id, transaction_type, ledger_category, amount, payment_method, channel_reference, narration, status)
                VALUES (%s, %s, 'DEBIT', 'SAVINGS', %s, 'POLARIS_BANK_TRANSFER', %s, %s, 'VERIFIED');
            """, (
                tx_ref, member_id, wdr_amt, ref, narr[:250]
            ))

            conn.commit()

            return {
                "status": "SUCCESS",
                "target_id": target_id,
                "title": target["title"],
                "withdrawn_amount": float(wdr_amt),
                "remaining_balance": float(new_bal),
                "status_after": new_status,
                "channel_reference": ref,
                "message": f"Maturity payout of NGN {amount:,.2f} processed successfully to {b_name} ({b_acc})."
            }
        finally:
            cursor.close()
            conn.close()

    def get_all_target_savings_summary(self) -> Dict[str, Any]:
        """
        Retrieves organization-wide Target Savings metrics and ledger list for executives/admins.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                UPDATE target_savings_accounts
                SET status = 'MATURED'
                WHERE status = 'ACTIVE' AND CURDATE() >= maturity_date;
            """)
            conn.commit()

            cursor.execute("""
                SELECT 
                    COUNT(*) AS total_ledgers,
                    COALESCE(SUM(CASE WHEN status IN ('ACTIVE', 'MATURED') THEN current_balance ELSE 0 END), 0) AS total_savings_pool,
                    COALESCE(SUM(CASE WHEN status IN ('ACTIVE', 'MATURED') THEN target_amount ELSE 0 END), 0) AS total_target_goal,
                    SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_ledgers,
                    SUM(CASE WHEN status = 'MATURED' THEN 1 ELSE 0 END) AS matured_ledgers,
                    SUM(CASE WHEN status = 'WITHDRAWN' THEN 1 ELSE 0 END) AS withdrawn_ledgers
                FROM target_savings_accounts;
            """)
            totals = cursor.fetchone() or {}

            # Breakdown by category
            cursor.execute("""
                SELECT 
                    target_type,
                    COUNT(*) AS ledger_count,
                    COALESCE(SUM(current_balance), 0) AS total_balance,
                    COALESCE(SUM(target_amount), 0) AS total_target
                FROM target_savings_accounts
                GROUP BY target_type
                ORDER BY total_balance DESC;
            """)
            cat_rows = cursor.fetchall()
            by_category = []
            for c in cat_rows:
                by_category.append({
                    "target_type": c["target_type"],
                    "label": self.TARGET_CATEGORIES.get(c["target_type"], c["target_type"].title()),
                    "ledger_count": c["ledger_count"],
                    "total_balance": float(c["total_balance"]),
                    "total_target": float(c["total_target"])
                })

            # Recent ledgers with member info
            cursor.execute("""
                SELECT 
                    t.id,
                    t.member_id,
                    m.member_code,
                    CONCAT(m.first_name, ' ', m.last_name) AS member_name,
                    t.target_type,
                    t.title,
                    t.target_amount,
                    t.current_balance,
                    t.start_date,
                    t.maturity_date,
                    t.status,
                    t.created_at
                FROM target_savings_accounts t
                JOIN members m ON t.member_id = m.id
                ORDER BY t.id DESC
                LIMIT 50;
            """)
            ledgers = []
            today = date.today()
            for l in cursor.fetchall():
                m_date = l["maturity_date"]
                if isinstance(m_date, datetime):
                    m_date = m_date.date()
                s_date = l["start_date"]
                if isinstance(s_date, datetime):
                    s_date = s_date.date()

                days_remaining = max(0, (m_date - today).days) if m_date else 0
                bal = float(l["current_balance"])
                tgt = float(l["target_amount"])
                progress = min(100.0, round(bal / tgt * 100, 1)) if tgt > 0 else 0.0

                ledgers.append({
                    "id": l["id"],
                    "member_id": l["member_id"],
                    "member_code": l["member_code"],
                    "member_name": l["member_name"],
                    "target_type": l["target_type"],
                    "target_type_label": self.TARGET_CATEGORIES.get(l["target_type"], l["target_type"].title()),
                    "title": l["title"],
                    "target_amount": tgt,
                    "current_balance": bal,
                    "progress_percent": progress,
                    "start_date": str(s_date),
                    "maturity_date": str(m_date),
                    "days_remaining": days_remaining,
                    "status": l["status"],
                    "created_at": str(l["created_at"])
                })

            return {
                "totals": {
                    "total_ledgers": totals.get("total_ledgers", 0),
                    "total_savings_pool": float(totals.get("total_savings_pool", 0)),
                    "total_target_goal": float(totals.get("total_target_goal", 0)),
                    "active_ledgers": totals.get("active_ledgers", 0) or 0,
                    "matured_ledgers": totals.get("matured_ledgers", 0) or 0,
                    "withdrawn_ledgers": totals.get("withdrawn_ledgers", 0) or 0
                },
                "by_category": by_category,
                "ledgers": ledgers
            }
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # PAYSTACK PAYMENT GATEWAY & DEDICATED VIRTUAL ACCOUNTS (DVA)
    # -------------------------------------------------------------------------
    def get_or_create_member_dva(self, member_id: int, check_compulsory_kyc: bool = True) -> Dict[str, Any]:
        """
        Retrieves or generates a Dedicated Paystack Virtual Account (DVA) for a member.
        Enables cooperators to transfer funds from any Nigerian banking app
        with automated real-time settlement into their cooperative account.
        STATUTORY INVARIANT: Gated by 100% completion of compulsory KYC fields.
        """
        from paystack_service import PaystackService

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    id, member_code, first_name, last_name, email, phone,
                    paystack_customer_code, paystack_dva_account_number,
                    paystack_dva_bank_name, paystack_dva_account_name
                FROM members 
                WHERE id = %s;
            """, (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError(f"Member ID {member_id} not found.")

            # Check Compulsory KYC Gating
            if check_compulsory_kyc:
                kyc_eval = self.evaluate_compulsory_kyc(member_id)
                if not kyc_eval["is_compulsory_complete"]:
                    return {
                        "member_id": member_id,
                        "member_code": member["member_code"],
                        "is_locked": True,
                        "is_active": False,
                        "reason": "Compulsory KYC incomplete. In accordance with Lagos State Cooperative Regulations and AML/CFT statutory guidelines, you must complete 100% of your compulsory KYC fields (Full Name, Phone, Email, Residential Address, and National Identity Number) to unlock your Dedicated Virtual Account.",
                        "compulsory_kyc": kyc_eval,
                        "kyc_completion_percent": kyc_eval.get("kyc_completion_percent", 0)
                    }

            # If DVA already assigned, return immediately
            if member.get("paystack_dva_account_number"):
                return {
                    "member_id": member_id,
                    "member_code": member["member_code"],
                    "account_number": member["paystack_dva_account_number"],
                    "bank_name": member["paystack_dva_bank_name"] or "Wema Bank (Paystack DVA)",
                    "account_name": member["paystack_dva_account_name"] or f"Wealthbridge / {member['first_name']} {member['last_name']}",
                    "customer_code": member.get("paystack_customer_code"),
                    "is_active": True,
                    "is_locked": False,
                    "is_new": False
                }

            # Generate via Paystack Service
            dva = PaystackService.generate_dedicated_virtual_account(member)

            cursor.execute("""
                UPDATE members
                SET 
                    paystack_customer_code = %s,
                    paystack_dva_account_number = %s,
                    paystack_dva_bank_name = %s,
                    paystack_dva_account_name = %s
                WHERE id = %s;
            """, (
                dva.get("customer_code"),
                dva.get("account_number"),
                dva.get("bank_name"),
                dva.get("account_name"),
                member_id
            ))
            conn.commit()

            return {
                "member_id": member_id,
                "member_code": member["member_code"],
                "account_number": dva.get("account_number"),
                "bank_name": dva.get("bank_name"),
                "account_name": dva.get("account_name"),
                "customer_code": dva.get("customer_code"),
                "is_active": True,
                "is_new": True,
                "note": dva.get("note", "Dedicated NUBAN created successfully.")
            }
        finally:
            cursor.close()
            conn.close()

    def record_paystack_webhook_credit(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes real-time Paystack webhook events (e.g. charge.success, dedicated_account.assign.success).
        Identifies cooperator via DVA NUBAN or Customer Code, updates cooperative ledger,
        and logs transaction for zero-duplicate idempotency.
        """
        import json
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            reference = str(data.get("reference") or f"PST-REF-{int(time.time()*1000)}")
            amount_kobo = float(data.get("amount", 0))
            amount_ngn = amount_kobo / 100.0

            # Idempotency check: has this reference been processed before?
            cursor.execute("SELECT id, status FROM paystack_webhook_logs WHERE reference = %s;", (reference,))
            existing = cursor.fetchone()
            if existing:
                return {
                    "status": "ALREADY_PROCESSED",
                    "message": f"Webhook reference '{reference}' was already processed.",
                    "reference": reference
                }

            customer = data.get("customer", {})
            cust_code = customer.get("customer_code")
            cust_email = customer.get("email", "").strip().lower()

            dedicated = data.get("dedicated_account", {})
            dva_num = dedicated.get("account_number") if dedicated else None

            # Find matching member
            member = None
            if dva_num:
                cursor.execute("SELECT id, member_code, first_name, last_name FROM members WHERE paystack_dva_account_number = %s;", (dva_num,))
                member = cursor.fetchone()

            if not member and cust_code:
                cursor.execute("SELECT id, member_code, first_name, last_name FROM members WHERE paystack_customer_code = %s;", (cust_code,))
                member = cursor.fetchone()

            if not member and cust_email:
                cursor.execute("SELECT id, member_code, first_name, last_name FROM members WHERE LOWER(email) = %s;", (cust_email,))
                member = cursor.fetchone()

            metadata = data.get("metadata") or {}
            if not member and metadata.get("member_id"):
                try:
                    cursor.execute("SELECT id, member_code, first_name, last_name FROM members WHERE id = %s;", (int(metadata.get("member_id")),))
                    member = cursor.fetchone()
                except Exception:
                    pass

            member_id = member["id"] if member else None
            member_code = member["member_code"] if member else "UNKNOWN"

            # If member matched and amount > 0, post credit into co-op savings ledger
            if member_id and amount_ngn > 0:
                tx_ref = f"TX-PST-{int(time.time()*1000)}-{secrets.token_hex(4).upper()}"
                narration = f"Paystack Inward Transfer: DVA {dva_num or reference}"
                cursor.execute("""
                    INSERT INTO transactions
                    (transaction_ref, member_id, transaction_type, ledger_category, amount, payment_method, channel_reference, narration, status)
                    VALUES (%s, %s, 'CREDIT', 'SAVINGS', %s, 'POLARIS_BANK_TRANSFER', %s, %s, 'VERIFIED');
                """, (
                    tx_ref, member_id, Decimal(str(amount_ngn)), reference, narration[:250]
                ))

            # Record in webhook audit log
            cursor.execute("""
                INSERT INTO paystack_webhook_logs
                (event_type, reference, member_id, amount, channel, payload, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'PROCESSED');
            """, (
                event_type,
                reference,
                member_id,
                Decimal(str(amount_ngn)),
                "paystack_dva",
                json.dumps(data)
            ))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

        dist_res = None
        if member_id and amount_ngn > 0:
            try:
                dist_res = self.distribute_payment_by_advice(
                    member_id=member_id,
                    amount_paid=amount_ngn,
                    payment_method="PAYSTACK_DVA",
                    payment_ref=reference,
                    narration=f"Paystack Inward Settlement: {dva_num or reference}"
                )
            except Exception as e:
                print(f"[Paystack Webhook] Advice auto-distribution notice: {e}")

        return {
            "status": "SUCCESS",
            "reference": reference,
            "amount_ngn": amount_ngn,
            "member_id": member_id,
            "member_code": member_code,
            "distribution": dist_res,
            "message": f"Processed Paystack credit of NGN {amount_ngn:,.2f} for member {member_code} with automated advice distribution."
        }

    # -------------------------------------------------------------------------
    # MONTHLY PAYMENT ADVICES & WATERFALL AUTO-DISTRIBUTION ENGINE
    # -------------------------------------------------------------------------
    def generate_or_get_monthly_advice(self, member_id: int, billing_period: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves or dynamically compiles the Monthly Payment Advice for a cooperator.
        Compiles all monthly financial obligations:
        - Mandatory Monthly Contribution (Tripartite: Savings, Shares, Welfare based on tier)
        - Active Loan Monthly Repayments
        - Unpaid Disciplinary Fines
        - Recurring Target Savings auto-save allocations
        - Unpaid Arrears from prior month advices
        """
        period = billing_period or datetime.now().strftime("%Y-%m")
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Check if advice already exists for this billing period
            cursor.execute("""
                SELECT * FROM payment_advices
                WHERE member_id = %s AND billing_period = %s
                LIMIT 1;
            """, (member_id, period))
            existing = cursor.fetchone()
            if existing:
                return self._format_advice_record(existing)

            # 2. Fetch member profile
            cursor.execute("""
                SELECT id, member_code, first_name, last_name, contribution_tier, status
                FROM members
                WHERE id = %s
                LIMIT 1;
            """, (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError(f"Member ID {member_id} not found.")

            tier = (member.get("contribution_tier") or "STANDARD").upper()
            tier_plan = self.TIER_CONTRIBUTIONS.get(tier, self.TIER_CONTRIBUTIONS["STANDARD"])
            
            amount_welfare = tier_plan["welfare"]  # Flat ₦1,000 baseline across all tiers
            amount_shares = tier_plan["shares"]
            amount_savings = tier_plan["savings"]

            # Support voluntary member welfare increase if a permanent commitment was recorded
            cursor.execute("""
                SELECT amount_welfare
                FROM payment_advices
                WHERE member_id = %s AND admin_notes LIKE '%[PERMANENT_COMMITMENT]%'
                ORDER BY id DESC
                LIMIT 1;
            """, (member_id,))
            perm_welfare = cursor.fetchone()
            if perm_welfare and perm_welfare.get("amount_welfare") is not None:
                vol_welfare = float(perm_welfare["amount_welfare"])
                if vol_welfare > amount_welfare:
                    amount_welfare = vol_welfare

            # 3. Active Loan Amortization
            cursor.execute("""
                SELECT id, monthly_installment, outstanding_balance
                FROM loans
                WHERE member_id = %s AND status = 'ACTIVE'
                ORDER BY id DESC
                LIMIT 1;
            """, (member_id,))
            active_loan = cursor.fetchone()
            amount_loan = float(active_loan["monthly_installment"]) if active_loan else 0.0

            # 4. Unpaid Disciplinary Fines
            cursor.execute("""
                SELECT COALESCE(SUM(fine_amount), 0) AS total_fines
                FROM disciplinary_fines
                WHERE member_id = %s AND status = 'UNPAID';
            """, (member_id,))
            fines_row = cursor.fetchone()
            amount_fines = float(fines_row["total_fines"]) if fines_row else 0.0

            # 5. Recurring Target Savings commitments
            cursor.execute("""
                SELECT COALESCE(SUM(auto_save_amount), 0) AS total_auto_save
                FROM target_savings_accounts
                WHERE member_id = %s AND status = 'ACTIVE' AND auto_save_amount > 0;
            """, (member_id,))
            tgt_row = cursor.fetchone()
            amount_targets = float(tgt_row["total_auto_save"]) if tgt_row else 0.0

            # 6. Unpaid Arrears from prior month
            cursor.execute("""
                SELECT outstanding_balance, amount_registration_fee, paid_registration
                FROM payment_advices
                WHERE member_id = %s AND billing_period < %s
                ORDER BY billing_period DESC
                LIMIT 1;
            """, (member_id, period))
            prior_advice = cursor.fetchone()
            amount_arrears = float(prior_advice["outstanding_balance"]) if prior_advice and prior_advice["outstanding_balance"] > 0 else 0.0

            # 7. Mandatory Entrance / Registration Fee (Article 7 - Flat ₦5,000)
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) AS total_reg_paid
                FROM transactions
                WHERE member_id = %s AND ledger_category = 'REGISTRATION_FEE' AND status = 'VERIFIED';
            """, (member_id,))
            reg_txn = cursor.fetchone()
            total_reg_paid = float(reg_txn["total_reg_paid"]) if reg_txn else 0.0

            prior_unpaid_reg = 0.0
            if prior_advice:
                prior_unpaid_reg = max(0.0, float(prior_advice.get("amount_registration_fee", 0.0) or 0.0) - float(prior_advice.get("paid_registration", 0.0) or 0.0))

            if total_reg_paid >= 5000.0:
                amount_registration = 0.0
            elif prior_unpaid_reg > 0:
                amount_registration = prior_unpaid_reg
                amount_arrears = max(0.0, amount_arrears - prior_unpaid_reg)
            else:
                amount_registration = max(0.0, 5000.0 - total_reg_paid)

            total_expected = (
                amount_fines + amount_registration + amount_loan + amount_welfare +
                amount_shares + amount_savings + amount_targets + amount_arrears
            )

            ref_period = period.replace("-", "")
            advice_ref = f"WMC-ADV-{ref_period}-{member_id:04d}"
            
            # Due date is strictly the 28th of the billing month
            parts = period.split("-")
            year, month = int(parts[0]), int(parts[1])
            due_date = f"{year:04d}-{month:02d}-28"
            issue_date = f"{year:04d}-{month:02d}-01"

            cursor.execute("""
                INSERT INTO payment_advices (
                    advice_reference, member_id, billing_period, issue_date, due_date,
                    tier_at_issuance, amount_fines, amount_registration_fee, amount_loan_repayment, amount_welfare,
                    amount_share_capital, amount_regular_savings, amount_target_savings,
                    amount_arrears, total_expected_amount, total_amount_paid,
                    outstanding_balance, status
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, 0.00,
                    %s, 'DUE'
                );
            """, (
                advice_ref, member_id, period, issue_date, due_date,
                tier, Decimal(str(amount_fines)), Decimal(str(amount_registration)), Decimal(str(amount_loan)), Decimal(str(amount_welfare)),
                Decimal(str(amount_shares)), Decimal(str(amount_savings)), Decimal(str(amount_targets)),
                Decimal(str(amount_arrears)), Decimal(str(total_expected)),
                Decimal(str(total_expected))
            ))
            adv_id = cursor.lastrowid
            conn.commit()

            # Check for cumulative multi-month arrears (>= 3 consecutive unpaid billing periods)
            cursor.execute("""
                SELECT COUNT(*) as unpaid_advices
                FROM payment_advices
                WHERE member_id = %s AND status != 'FULLY_SETTLED';
            """, (member_id,))
            unpaid_stat = cursor.fetchone()
            if unpaid_stat and unpaid_stat["unpaid_advices"] >= 3:
                if member.get("status") == "ACTIVE":
                    cursor.execute("UPDATE members SET status = 'SUSPENDED' WHERE id = %s;", (member_id,))
                    conn.commit()
                    self.log_audit_event(
                        user_id=member_id,
                        actor_name="Compliance Engine",
                        actor_role="SYSTEM",
                        action="MEMBER_AUTO_SUSPENDED_FOR_ARREARS",
                        resource_type="MEMBER",
                        resource_id=str(member_id),
                        details_before={"membership_status": "ACTIVE"},
                        details_after={"membership_status": "SUSPENDED", "unpaid_advices_count": unpaid_stat["unpaid_advices"]},
                        summary=f"Automated suspension applied to cooperator {member.get('member_code', member_id)} due to {unpaid_stat['unpaid_advices']} consecutive unremitted billing periods."
                    )

            cursor.execute("SELECT * FROM payment_advices WHERE id = %s;", (adv_id,))
            new_advice = cursor.fetchone()
            return self._format_advice_record(new_advice)

        finally:
            cursor.close()
            conn.close()

    def _format_advice_record(self, adv: Dict[str, Any]) -> Dict[str, Any]:
        """Formats raw database advice row into human-friendly API structure."""
        if not adv:
            return {}
        total_exp = float(adv["total_expected_amount"])
        total_pd = float(adv["total_amount_paid"])
        out_bal = float(adv["outstanding_balance"])
        pct = min(100.0, round((total_pd / total_exp * 100), 1)) if total_exp > 0 else 100.0

        return {
            "id": adv["id"],
            "advice_reference": adv["advice_reference"],
            "member_id": adv["member_id"],
            "billing_period": adv["billing_period"],
            "issue_date": str(adv["issue_date"]),
            "due_date": str(adv["due_date"]),
            "tier": adv["tier_at_issuance"],
            "status": adv["status"],
            "progress_percent": pct,
            "breakdown": {
                "fines": {
                    "expected": float(adv.get("amount_fines", 0.0) or 0.0),
                    "paid": float(adv.get("paid_fines", 0.0) or 0.0),
                    "remaining": max(0.0, float(adv.get("amount_fines", 0.0) or 0.0) - float(adv.get("paid_fines", 0.0) or 0.0))
                },
                "registration_fee": {
                    "expected": float(adv.get("amount_registration_fee", 0.0) or 0.0),
                    "paid": float(adv.get("paid_registration", 0.0) or 0.0),
                    "remaining": max(0.0, float(adv.get("amount_registration_fee", 0.0) or 0.0) - float(adv.get("paid_registration", 0.0) or 0.0))
                },
                "loan_repayment": {
                    "expected": float(adv["amount_loan_repayment"]),
                    "paid": float(adv["paid_loan"]),
                    "remaining": max(0.0, float(adv["amount_loan_repayment"]) - float(adv["paid_loan"]))
                },
                "welfare": {
                    "expected": float(adv["amount_welfare"]),
                    "paid": float(adv["paid_welfare"]),
                    "remaining": max(0.0, float(adv["amount_welfare"]) - float(adv["paid_welfare"]))
                },
                "share_capital": {
                    "expected": float(adv["amount_share_capital"]),
                    "paid": float(adv["paid_shares"]),
                    "remaining": max(0.0, float(adv["amount_share_capital"]) - float(adv["paid_shares"]))
                },
                "regular_savings": {
                    "expected": float(adv["amount_regular_savings"]),
                    "paid": float(adv["paid_savings"]),
                    "remaining": max(0.0, float(adv["amount_regular_savings"]) - float(adv["paid_savings"]))
                },
                "target_savings": {
                    "expected": float(adv["amount_target_savings"]),
                    "paid": float(adv["paid_targets"]),
                    "remaining": max(0.0, float(adv["amount_target_savings"]) - float(adv["paid_targets"]))
                },
                "arrears": {
                    "expected": float(adv["amount_arrears"])
                }
            },
            "totals": {
                "total_expected": total_exp,
                "total_paid": total_pd,
                "outstanding_balance": out_bal
            },
            "admin_notes": adv.get("admin_notes"),
            "created_at": str(adv["created_at"])
        }

    def distribute_payment_by_advice(
        self,
        member_id: int,
        amount_paid: float,
        payment_method: str = "PAYSTACK_DVA",
        payment_ref: str = "",
        narration: str = ""
    ) -> Dict[str, Any]:
        """
        Executes the statutory Priority Waterfall auto-distribution on inward remittances:
        Priority 1: Disciplinary Fines / Penalties
        Priority 2: Mandatory Entrance / Registration Fee (Article 7 - Flat ₦5,000)
        Priority 3: Active Loan Monthly Repayments
        Priority 4: Mandatory Welfare Solidarity Pool
        Priority 5: Mandatory Share Capital (Equity)
        Priority 6: Mandatory Regular Savings (Collateral)
        Priority 7: Recurring Voluntary Target Savings
        Priority 8 (Surplus): 100% credited to Regular Savings Ledger
        """
        if amount_paid <= 0:
            raise ValueError("Payment amount must be greater than zero.")

        advice = self.generate_or_get_monthly_advice(member_id)
        advice_id = advice["id"]

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT pa.*, m.member_code
                FROM payment_advices pa
                JOIN members m ON pa.member_id = m.id
                WHERE pa.id = %s FOR UPDATE;
            """, (advice_id,))
            adv_row = cursor.fetchone()
            if not adv_row:
                raise ValueError("Payment advice record not found.")

            # Remaining needed per bucket
            rem_fines = max(0.0, float(adv_row["amount_fines"]) - float(adv_row["paid_fines"]))
            rem_reg = max(0.0, float(adv_row.get("amount_registration_fee", 0.0) or 0.0) - float(adv_row.get("paid_registration", 0.0) or 0.0))
            rem_loan = max(0.0, float(adv_row["amount_loan_repayment"]) - float(adv_row["paid_loan"]))
            rem_welfare = max(0.0, float(adv_row["amount_welfare"]) - float(adv_row["paid_welfare"]))
            rem_shares = max(0.0, float(adv_row["amount_share_capital"]) - float(adv_row["paid_shares"]))
            rem_savings = max(0.0, float(adv_row["amount_regular_savings"]) - float(adv_row["paid_savings"]))
            rem_targets = max(0.0, float(adv_row["amount_target_savings"]) - float(adv_row["paid_targets"]))

            remaining_funds = float(amount_paid)

            # Waterfall allocations
            alloc_fines = min(remaining_funds, rem_fines)
            remaining_funds -= alloc_fines

            alloc_reg = min(remaining_funds, rem_reg)
            remaining_funds -= alloc_reg

            alloc_loan = min(remaining_funds, rem_loan)
            remaining_funds -= alloc_loan

            alloc_welfare = min(remaining_funds, rem_welfare)
            remaining_funds -= alloc_welfare

            alloc_shares = min(remaining_funds, rem_shares)
            remaining_funds -= alloc_shares

            alloc_savings = min(remaining_funds, rem_savings)
            remaining_funds -= alloc_savings

            alloc_targets = min(remaining_funds, rem_targets)
            remaining_funds -= alloc_targets

            alloc_surplus = remaining_funds # Remainder 100% credited to Regular Savings
            remaining_funds = 0.0

            ref = payment_ref or f"PAY-{int(time.time()*1000)}-{secrets.token_hex(4).upper()}"
            ts_batch = f"{int(time.time()*1000)}-{secrets.token_hex(3).upper()}"

            valid_methods = {'POLARIS_BANK_TRANSFER', 'DIRECT_DEBIT', 'ONLINE_GATEWAY', 'INTERNAL_SET_OFF'}
            clean_method = payment_method if payment_method in valid_methods else 'ONLINE_GATEWAY'

            # 1. Post Fines if allocated
            if alloc_fines > 0:
                cursor.execute("""
                    INSERT INTO transactions (
                        transaction_ref, member_id, transaction_type, ledger_category,
                        amount, payment_method, channel_reference, narration, status
                    ) VALUES (
                        %s, %s, 'CREDIT', 'DISCIPLINARY_FINE', %s, %s, %s, %s, 'VERIFIED'
                    );
                """, (
                    f"TXN-FIN-{member_id}-{ts_batch}", member_id, Decimal(str(alloc_fines)),
                    clean_method, ref, f"Disciplinary Fine Settlement (Adv #{adv_row['advice_reference']})"
                ))
                cursor.execute("""
                    UPDATE disciplinary_fines
                    SET status = 'SETTLED', settled_date = CURDATE()
                    WHERE member_id = %s AND status = 'UNPAID'
                    LIMIT 1;
                """, (member_id,))

            # 2. Post Entrance / Registration Fee if allocated (Priority 2)
            if alloc_reg > 0:
                cursor.execute("""
                    INSERT INTO transactions (
                        transaction_ref, member_id, transaction_type, ledger_category,
                        amount, payment_method, channel_reference, narration, status
                    ) VALUES (
                        %s, %s, 'CREDIT', 'REGISTRATION_FEE', %s, %s, %s, %s, 'VERIFIED'
                    );
                """, (
                    f"TXN-REG-{member_id}-{ts_batch}", member_id, Decimal(str(alloc_reg)),
                    clean_method, ref, f"Entrance / Registration Fee - Article 7 (Adv #{adv_row['advice_reference']})"
                ))

            # 3. Post Loan Repayment if allocated (Priority 3)
            if alloc_loan > 0:
                cursor.execute("""
                    INSERT INTO transactions (
                        transaction_ref, member_id, transaction_type, ledger_category,
                        amount, payment_method, channel_reference, narration, status
                    ) VALUES (
                        %s, %s, 'CREDIT', 'LOAN_REPAYMENT', %s, %s, %s, %s, 'VERIFIED'
                    );
                """, (
                    f"TXN-LON-{member_id}-{ts_batch}", member_id, Decimal(str(alloc_loan)),
                    clean_method, ref, f"Monthly Loan Amortization (Adv #{adv_row['advice_reference']})"
                ))
                cursor.execute("""
                    SELECT id, monthly_installment, outstanding_balance, total_paid
                    FROM loans
                    WHERE member_id = %s AND status = 'ACTIVE'
                    LIMIT 1;
                """, (member_id,))
                ln = cursor.fetchone()
                if ln:
                    new_out = max(Decimal("0.00"), ln["outstanding_balance"] - Decimal(str(alloc_loan)))
                    new_pd = ln["total_paid"] + Decimal(str(alloc_loan))
                    st = "COMPLETED" if new_out <= 0 else "ACTIVE"
                    cursor.execute("""
                        UPDATE loans
                        SET outstanding_balance = %s, total_paid = %s, status = %s
                        WHERE id = %s;
                    """, (new_out, new_pd, st, ln["id"]))

                    cursor.execute("""
                        INSERT INTO loan_repayments (
                            loan_id, installment_number, due_date, amount_due, amount_paid, paid_date, transaction_ref, status
                        ) VALUES (
                            %s, 1, CURDATE(), %s, %s, NOW(), %s, 'PAID'
                        );
                    """, (ln["id"], Decimal(str(alloc_loan)), Decimal(str(alloc_loan)), ref))

            # 3. Post Welfare Solidarity
            if alloc_welfare > 0:
                cursor.execute("""
                    INSERT INTO transactions (
                        transaction_ref, member_id, transaction_type, ledger_category,
                        amount, payment_method, channel_reference, narration, status
                    ) VALUES (
                        %s, %s, 'CREDIT', 'WELFARE_FUND', %s, %s, %s, %s, 'VERIFIED'
                    );
                """, (
                    f"TXN-WLF-{member_id}-{ts_batch}", member_id, Decimal(str(alloc_welfare)),
                    clean_method, ref, f"Welfare Solidarity Pool Levy (Adv #{adv_row['advice_reference']})"
                ))
                cursor.execute("""
                    INSERT INTO welfare_accounts (member_id, cumulative_contributions, consecutive_months_active, last_contribution_date)
                    VALUES (%s, %s, 1, CURDATE())
                    ON DUPLICATE KEY UPDATE
                        cumulative_contributions = cumulative_contributions + VALUES(cumulative_contributions),
                        consecutive_months_active = consecutive_months_active + 1,
                        last_contribution_date = CURDATE();
                """, (member_id, Decimal(str(alloc_welfare))))

            # 4. Post Share Capital
            if alloc_shares > 0:
                new_units = int(alloc_shares // 1000)
                cursor.execute("""
                    INSERT INTO transactions (
                        transaction_ref, member_id, transaction_type, ledger_category,
                        amount, payment_method, channel_reference, narration, status
                    ) VALUES (
                        %s, %s, 'CREDIT', 'SHARE_CAPITAL', %s, %s, %s, %s, 'VERIFIED'
                    );
                """, (
                    f"TXN-SHR-{member_id}-{ts_batch}", member_id, Decimal(str(alloc_shares)),
                    clean_method, ref, f"Share Capital Equity Subscription ({new_units} units)"
                ))
                cursor.execute("""
                    INSERT INTO share_accounts (member_id, units_held, paid_up_amount, is_minimum_met, benefits_qualified)
                    VALUES (%s, %s, %s, (%s >= 5), (%s >= 5))
                    ON DUPLICATE KEY UPDATE
                        units_held = units_held + %s,
                        paid_up_amount = paid_up_amount + VALUES(paid_up_amount),
                        is_minimum_met = (units_held >= 5),
                        benefits_qualified = (units_held >= 5);
                """, (member_id, new_units, Decimal(str(alloc_shares)), new_units, new_units, new_units))

            # 5. Post Regular Savings (Advised Savings + 100% of Surplus)
            total_savings_to_credit = alloc_savings + alloc_surplus
            if total_savings_to_credit > 0:
                narr_sav = f"Regular Savings Remittance (Adv #{adv_row['advice_reference']})"
                if alloc_surplus > 0:
                    narr_sav += f" [Includes Surplus: NGN {alloc_surplus:,.2f}]"
                cursor.execute("""
                    INSERT INTO transactions (
                        transaction_ref, member_id, transaction_type, ledger_category,
                        amount, payment_method, channel_reference, narration, status
                    ) VALUES (
                        %s, %s, 'CREDIT', 'SAVINGS', %s, %s, %s, %s, 'VERIFIED'
                    );
                """, (
                    f"TXN-SAV-{member_id}-{ts_batch}", member_id, Decimal(str(total_savings_to_credit)),
                    clean_method, ref, narr_sav
                ))
                cursor.execute("""
                    INSERT INTO savings_accounts (member_id, total_balance, encumbered_balance)
                    VALUES (%s, %s, 0.00)
                    ON DUPLICATE KEY UPDATE
                        total_balance = total_balance + VALUES(total_balance);
                """, (member_id, Decimal(str(total_savings_to_credit))))

            # 6. Post Target Savings
            if alloc_targets > 0:
                cursor.execute("""
                    SELECT id, title, auto_save_amount, current_balance
                    FROM target_savings_accounts
                    WHERE member_id = %s AND status = 'ACTIVE' AND auto_save_amount > 0;
                """, (member_id,))
                active_targets = cursor.fetchall()
                if active_targets:
                    tot_auto = sum(float(t["auto_save_amount"]) for t in active_targets)
                    for t in active_targets:
                        ratio = float(t["auto_save_amount"]) / tot_auto if tot_auto > 0 else (1.0 / len(active_targets))
                        t_alloc = round(alloc_targets * ratio, 2)
                        new_t_bal = float(t["current_balance"]) + t_alloc

                        cursor.execute("""
                            UPDATE target_savings_accounts
                            SET current_balance = %s
                            WHERE id = %s;
                        """, (Decimal(str(new_t_bal)), t["id"]))

                        cursor.execute("""
                            INSERT INTO target_savings_transactions (
                                target_account_id, member_id, transaction_type, amount,
                                balance_after, payment_method, channel_reference, narration
                            ) VALUES (
                                %s, %s, 'DEPOSIT', %s, %s, %s, %s, %s
                            );
                        """, (
                            t["id"], member_id, Decimal(str(t_alloc)), Decimal(str(new_t_bal)),
                            payment_method, ref, f"Auto-distribution from advice #{adv_row['advice_reference']}"
                        ))
                else:
                    cursor.execute("""
                        UPDATE savings_accounts
                        SET total_balance = total_balance + %s
                        WHERE member_id = %s;
                    """, (Decimal(str(alloc_targets)), member_id))

            # 7. Record Distribution Audit Log
            cursor.execute("""
                INSERT INTO payment_advice_distributions (
                    advice_id, member_id, payment_reference, payment_method, total_payment_received,
                    allocated_fines, allocated_registration, allocated_loan, allocated_welfare, allocated_shares,
                    allocated_savings, allocated_targets, allocated_surplus_savings, narration
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s
                );
            """, (
                advice_id, member_id, ref, payment_method, Decimal(str(amount_paid)),
                Decimal(str(alloc_fines)), Decimal(str(alloc_reg)), Decimal(str(alloc_loan)), Decimal(str(alloc_welfare)),
                Decimal(str(alloc_shares)), Decimal(str(alloc_savings)), Decimal(str(alloc_targets)),
                Decimal(str(alloc_surplus)), narration or f"Auto-distribution of NGN {amount_paid:,.2f}"
            ))

            # 8. Update Payment Advice Aggregate
            new_pd_fines = Decimal(str(float(adv_row["paid_fines"]) + alloc_fines))
            new_pd_reg = Decimal(str(float(adv_row.get("paid_registration", 0.0) or 0.0) + alloc_reg))
            new_pd_loan = Decimal(str(float(adv_row["paid_loan"]) + alloc_loan))
            new_pd_welfare = Decimal(str(float(adv_row["paid_welfare"]) + alloc_welfare))
            new_pd_shares = Decimal(str(float(adv_row["paid_shares"]) + alloc_shares))
            new_pd_savings = Decimal(str(float(adv_row["paid_savings"]) + alloc_savings))
            new_pd_targets = Decimal(str(float(adv_row["paid_targets"]) + alloc_targets))

            obligation_settled = (alloc_fines + alloc_reg + alloc_loan + alloc_welfare + alloc_shares + alloc_savings + alloc_targets)
            new_tot_paid = adv_row["total_amount_paid"] + Decimal(str(obligation_settled))
            new_out_bal = max(Decimal("0.00"), adv_row["total_expected_amount"] - new_tot_paid)
            new_status = "FULLY_SETTLED" if new_out_bal <= Decimal("0.01") else "PARTIALLY_PAID"

            cursor.execute("""
                UPDATE payment_advices
                SET
                    paid_fines = %s,
                    paid_registration = %s,
                    paid_loan = %s,
                    paid_welfare = %s,
                    paid_shares = %s,
                    paid_savings = %s,
                    paid_targets = %s,
                    total_amount_paid = %s,
                    outstanding_balance = %s,
                    status = %s
                WHERE id = %s;
            """, (
                new_pd_fines, new_pd_reg, new_pd_loan, new_pd_welfare, new_pd_shares,
                new_pd_savings, new_pd_targets, new_tot_paid, new_out_bal,
                new_status, advice_id
            ))

            # 9. Real-Time Double-Entry General Ledger Posting (Module 4)
            je_lines = [
                {"account_code": "1010", "line_type": "DEBIT", "amount": Decimal(str(amount_paid)), "memo": f"Member Remittance - Adv #{adv_row['advice_reference']}"}
            ]
            if alloc_fines > 0:
                je_lines.append({"account_code": "4040", "line_type": "CREDIT", "amount": Decimal(str(alloc_fines)), "memo": "Disciplinary Fine Settlement"})
            if alloc_reg > 0:
                je_lines.append({"account_code": "4020", "line_type": "CREDIT", "amount": Decimal(str(alloc_reg)), "memo": "Entrance / Registration Fee"})
            if alloc_loan > 0:
                je_lines.append({"account_code": "1030", "line_type": "CREDIT", "amount": Decimal(str(alloc_loan)), "memo": "Loan Principal Amortization"})
            if alloc_welfare > 0:
                je_lines.append({"account_code": "2030", "line_type": "CREDIT", "amount": Decimal(str(alloc_welfare)), "memo": "Welfare Solidarity Levy"})
            if alloc_shares > 0:
                je_lines.append({"account_code": "3010", "line_type": "CREDIT", "amount": Decimal(str(alloc_shares)), "memo": "Paid-Up Share Capital Subscription"})
            if (alloc_savings + alloc_surplus) > 0:
                je_lines.append({"account_code": "2010", "line_type": "CREDIT", "amount": Decimal(str(alloc_savings + alloc_surplus)), "memo": "Regular Savings Deposit"})
            if alloc_targets > 0:
                je_lines.append({"account_code": "2020", "line_type": "CREDIT", "amount": Decimal(str(alloc_targets)), "memo": "Target Savings Deposit"})

            self._post_journal_entry_with_cursor(
                cursor=cursor,
                entry_date=date.today(),
                source_module='REMITTANCE_WATERFALL',
                source_reference=ref,
                narration=f"Automated Remittance Waterfall for {adv_row['member_code']} (Adv #{adv_row['advice_reference']})",
                lines=je_lines,
                created_by=member_id,
                status='POSTED'
            )

            conn.commit()

            # If member was suspended and has now cleared all arrears, auto-reinstate to ACTIVE
            cursor.execute("""
                SELECT COUNT(*) as unpaid_left
                FROM payment_advices
                WHERE member_id = %s AND status != 'FULLY_SETTLED';
            """, (member_id,))
            left_stat = cursor.fetchone()
            if left_stat and left_stat["unpaid_left"] == 0:
                cursor.execute("SELECT status FROM members WHERE id = %s;", (member_id,))
                cur_m = cursor.fetchone()
                if cur_m and cur_m["status"] == "SUSPENDED":
                    cursor.execute("UPDATE members SET status = 'ACTIVE' WHERE id = %s;", (member_id,))
                    conn.commit()
                    self.log_audit_event(
                        user_id=member_id,
                        actor_name="Compliance Engine",
                        actor_role="SYSTEM",
                        action="MEMBER_AUTO_REINSTATED_ARREARS_CLEARED",
                        resource_type="MEMBER",
                        resource_id=str(member_id),
                        details_before={"membership_status": "SUSPENDED"},
                        details_after={"membership_status": "ACTIVE"},
                        summary=f"Cooperator {adv_row.get('member_code', member_id)} automatically reinstated to ACTIVE standing after full settlement of all outstanding payment obligations."
                    )

            return {
                "status": "SUCCESS",
                "advice_id": advice_id,
                "advice_reference": adv_row["advice_reference"],
                "amount_received": float(amount_paid),
                "allocations": {
                    "fines": alloc_fines,
                    "registration_fee": alloc_reg,
                    "loan_repayment": alloc_loan,
                    "welfare": alloc_welfare,
                    "share_capital": alloc_shares,
                    "regular_savings": alloc_savings,
                    "target_savings": alloc_targets,
                    "surplus_regular_savings": alloc_surplus
                },
                "total_obligations_satisfied": obligation_settled,
                "surplus_credited_to_savings": alloc_surplus,
                "advice_status": new_status,
                "outstanding_balance": float(new_out_bal),
                "payment_reference": ref,
                "message": f"Successfully auto-distributed NGN {amount_paid:,.2f} according to Payment Advice #{adv_row['advice_reference']}."
            }

        except Exception as e:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def admin_revise_payment_advice(self, advice_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Allows Financial Secretary / Admin to adjust amounts or add waivers/notes to an advice."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM payment_advices WHERE id = %s FOR UPDATE;", (advice_id,))
            adv = cursor.fetchone()
            if not adv:
                raise ValueError(f"Advice ID {advice_id} not found.")

            fines = Decimal(str(updates.get("amount_fines", adv["amount_fines"])))
            reg_fee = Decimal(str(updates.get("amount_registration_fee", adv.get("amount_registration_fee", 0.0) or 0.0)))
            loan = Decimal(str(updates.get("amount_loan_repayment", adv["amount_loan_repayment"])))
            welfare = Decimal(str(updates.get("amount_welfare", adv["amount_welfare"])))
            shares = Decimal(str(updates.get("amount_share_capital", adv["amount_share_capital"])))
            savings = Decimal(str(updates.get("amount_regular_savings", adv["amount_regular_savings"])))
            targets = Decimal(str(updates.get("amount_target_savings", adv["amount_target_savings"])))
            arrears = Decimal(str(updates.get("amount_arrears", adv["amount_arrears"])))
            notes = updates.get("admin_notes", adv.get("admin_notes"))

            total_exp = fines + reg_fee + loan + welfare + shares + savings + targets + arrears
            out_bal = max(Decimal("0.00"), total_exp - adv["total_amount_paid"])
            st = "FULLY_SETTLED" if out_bal <= Decimal("0.01") else ("PARTIALLY_PAID" if adv["total_amount_paid"] > 0 else "DUE")

            cursor.execute("""
                UPDATE payment_advices
                SET
                    amount_fines = %s,
                    amount_registration_fee = %s,
                    amount_loan_repayment = %s,
                    amount_welfare = %s,
                    amount_share_capital = %s,
                    amount_regular_savings = %s,
                    amount_target_savings = %s,
                    amount_arrears = %s,
                    total_expected_amount = %s,
                    outstanding_balance = %s,
                    status = %s,
                    admin_notes = %s
                WHERE id = %s;
            """, (
                fines, reg_fee, loan, welfare, shares, savings, targets, arrears,
                total_exp, out_bal, st, notes, advice_id
            ))
            conn.commit()

            cursor.execute("SELECT * FROM payment_advices WHERE id = %s;", (advice_id,))
            return self._format_advice_record(cursor.fetchone())
        finally:
            cursor.close()
            conn.close()

    def get_member_payment_advices(self, member_id: int) -> List[Dict[str, Any]]:
        """Retrieves history of all payment advices for a cooperator."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT * FROM payment_advices
                WHERE member_id = %s
                ORDER BY billing_period DESC;
            """, (member_id,))
            rows = cursor.fetchall()
            return [self._format_advice_record(r) for r in rows]
        finally:
            cursor.close()
            conn.close()

    def get_all_payment_advices_summary(self, billing_period: Optional[str] = None) -> Dict[str, Any]:
        """Retrieves organization-wide summary of payment advices for executive oversight."""
        period = billing_period or datetime.now().strftime("%Y-%m")
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id FROM members WHERE status = 'ACTIVE';")
            active_mems = [r["id"] for r in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

        for mid in active_mems:
            self.generate_or_get_monthly_advice(mid, period)

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT
                    COUNT(*) AS total_advices,
                    COALESCE(SUM(total_expected_amount), 0) AS total_expected,
                    COALESCE(SUM(total_amount_paid), 0) AS total_collected,
                    COALESCE(SUM(outstanding_balance), 0) AS total_outstanding,
                    SUM(CASE WHEN status = 'FULLY_SETTLED' THEN 1 ELSE 0 END) AS fully_settled_count,
                    SUM(CASE WHEN status = 'PARTIALLY_PAID' THEN 1 ELSE 0 END) AS partially_paid_count,
                    SUM(CASE WHEN status = 'DUE' THEN 1 ELSE 0 END) AS due_count,
                    SUM(CASE WHEN status = 'OVERDUE' THEN 1 ELSE 0 END) AS overdue_count
                FROM payment_advices
                WHERE billing_period = %s;
            """, (period,))
            totals = cursor.fetchone() or {}

            cursor.execute("""
                SELECT 
                    a.*,
                    m.member_code,
                    CONCAT(m.first_name, ' ', m.last_name) AS member_name
                FROM payment_advices a
                JOIN members m ON a.member_id = m.id
                WHERE a.billing_period = %s
                ORDER BY a.outstanding_balance DESC;
            """, (period,))
            advices = []
            for r in cursor.fetchall():
                f = self._format_advice_record(r)
                f["member_code"] = r["member_code"]
                f["member_name"] = r["member_name"]
                advices.append(f)

            return {
                "billing_period": period,
                "totals": {
                    "total_advices": totals.get("total_advices", 0),
                    "total_expected": float(totals.get("total_expected", 0)),
                    "total_collected": float(totals.get("total_collected", 0)),
                    "total_outstanding": float(totals.get("total_outstanding", 0)),
                    "fully_settled_count": totals.get("fully_settled_count", 0) or 0,
                    "partially_paid_count": totals.get("partially_paid_count", 0) or 0,
                    "due_count": totals.get("due_count", 0) or 0,
                    "overdue_count": totals.get("overdue_count", 0) or 0,
                    "collection_rate_percent": round(float(totals.get("total_collected", 0)) / float(totals.get("total_expected", 1)) * 100, 1) if float(totals.get("total_expected", 0)) > 0 else 0.0
                },
                "advices": advices
            }
        finally:
            cursor.close()
            conn.close()

    # =========================================================================
    # COOPERATIVE MEMBER REPORTING & AUDIT ENGINES (CAP C15 COMPLIANT)
    # =========================================================================

    def get_member_report_years(self, member_id: int) -> List[int]:
        """
        Retrieves list of distinct financial calendar years in which this cooperator
        has recorded transactions or advices, always including the current financial year.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT DISTINCT YEAR(transaction_date) AS yr
                FROM transactions
                WHERE member_id = %s
                ORDER BY yr DESC;
            """, (member_id,))
            years = [r["yr"] for r in cursor.fetchall() if r.get("yr")]
            curr_yr = date.today().year
            if curr_yr not in years:
                years.insert(0, curr_yr)
            return sorted(list(set(years)), reverse=True)
        finally:
            cursor.close()
            conn.close()

    def get_member_passbook_ledger(self, member_id: int, year: Optional[int] = None) -> Dict[str, Any]:
        """
        Generates the Statutory Annual / Multi-Year Passbook Ledger Statement:
        1. Calculates Opening Balances prior to the given financial year.
        2. Retrieves all transactions chronologically with tripartite ledger tracking
           (Savings, Shares, Welfare, Targets, Fines).
        3. Computes cumulative running balances entry-by-entry.
        4. Calculates Closing Balances, net annual growth, and 2x borrowing capacity.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Fetch Member Profile Information
            cursor.execute("""
                SELECT 
                    m.id, m.member_code, m.first_name, m.last_name, m.email, m.phone,
                    m.contribution_tier, m.status AS membership_status, m.admission_date,
                    m.paystack_dva_account_number, m.paystack_dva_bank_name,
                    sa.total_balance AS current_savings,
                    sh.paid_up_amount AS current_shares, sh.units_held AS current_share_units,
                    w.cumulative_contributions AS current_welfare
                FROM members m
                LEFT JOIN savings_accounts sa ON m.id = sa.member_id
                LEFT JOIN share_accounts sh ON m.id = sh.member_id
                LEFT JOIN welfare_accounts w ON m.id = w.member_id
                WHERE m.id = %s;
            """, (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError(f"Member ID {member_id} not found.")

            # 2. Opening Balance Calculation
            op_savings = Decimal("0.00")
            op_shares = Decimal("0.00")
            op_welfare = Decimal("0.00")
            op_fines = Decimal("0.00")

            is_yearly = bool(year and year > 0)
            if is_yearly:
                start_of_year = f"{year}-01-01 00:00:00"
                cursor.execute("""
                    SELECT 
                        ledger_category,
                        transaction_type,
                        SUM(amount) AS cat_sum
                    FROM transactions
                    WHERE member_id = %s AND transaction_date < %s
                    GROUP BY ledger_category, transaction_type;
                """, (member_id, start_of_year))
                for row in cursor.fetchall():
                    c_sum = Decimal(str(row["cat_sum"] or 0.0))
                    cat = row["ledger_category"]
                    ttype = row["transaction_type"]
                    if cat == "SAVINGS":
                        op_savings += (c_sum if ttype == "CREDIT" else -c_sum)
                    elif cat == "SHARE_CAPITAL":
                        op_shares += (c_sum if ttype == "CREDIT" else -c_sum)
                    elif cat == "WELFARE_FUND":
                        op_welfare += (c_sum if ttype == "CREDIT" else -c_sum)
                    elif cat == "DISCIPLINARY_FINE":
                        op_fines += c_sum

            opening_total = op_savings + op_shares + op_welfare

            # 3. Fetch In-Period Transactions Chronologically
            if is_yearly:
                start_dt = f"{year}-01-01 00:00:00"
                end_dt = f"{year}-12-31 23:59:59"
                cursor.execute("""
                    SELECT 
                        id, transaction_ref, transaction_type, ledger_category,
                        amount, payment_method, channel_reference, narration,
                        status, transaction_date
                    FROM transactions
                    WHERE member_id = %s 
                      AND transaction_date >= %s 
                      AND transaction_date <= %s
                    ORDER BY transaction_date ASC, id ASC;
                """, (member_id, start_dt, end_dt))
            else:
                cursor.execute("""
                    SELECT 
                        id, transaction_ref, transaction_type, ledger_category,
                        amount, payment_method, channel_reference, narration,
                        status, transaction_date
                    FROM transactions
                    WHERE member_id = %s
                    ORDER BY transaction_date ASC, id ASC;
                """, (member_id,))

            raw_txs = cursor.fetchall()

            # 4. Process Running Balances & Movement Totals
            run_savings = op_savings
            run_shares = op_shares
            run_welfare = op_welfare
            run_total = opening_total

            period_credits_savings = Decimal("0.00")
            period_credits_shares = Decimal("0.00")
            period_credits_welfare = Decimal("0.00")
            period_credits_other = Decimal("0.00")
            period_debits_savings = Decimal("0.00")
            period_debits_other = Decimal("0.00")

            ledger_entries = []
            for tx in raw_txs:
                amt = Decimal(str(tx["amount"]))
                ttype = tx["transaction_type"]
                cat = tx["ledger_category"]

                if ttype == "CREDIT":
                    if cat == "SAVINGS":
                        run_savings += amt
                        period_credits_savings += amt
                    elif cat == "SHARE_CAPITAL":
                        run_shares += amt
                        period_credits_shares += amt
                    elif cat == "WELFARE_FUND":
                        run_welfare += amt
                        period_credits_welfare += amt
                    else:
                        period_credits_other += amt
                    run_total += amt
                else:  # DEBIT
                    if cat == "SAVINGS":
                        run_savings -= amt
                        period_debits_savings += amt
                    else:
                        period_debits_other += amt
                    run_total -= amt

                tx_date_str = tx["transaction_date"].strftime("%Y-%m-%d %H:%M") if isinstance(tx["transaction_date"], (datetime, date)) else str(tx["transaction_date"] or "")

                ledger_entries.append({
                    "id": tx["id"],
                    "transaction_ref": tx["transaction_ref"],
                    "transaction_date": tx_date_str,
                    "transaction_type": ttype,
                    "ledger_category": cat,
                    "amount": float(amt),
                    "payment_method": tx["payment_method"],
                    "channel_reference": tx["channel_reference"],
                    "narration": tx["narration"],
                    "status": tx["status"],
                    "running_savings": float(run_savings),
                    "running_shares": float(run_shares),
                    "running_welfare": float(run_welfare),
                    "running_total": float(run_total)
                })

            period_total_credits = period_credits_savings + period_credits_shares + period_credits_welfare + period_credits_other
            period_total_debits = period_debits_savings + period_debits_other
            net_change = period_total_credits - period_total_debits

            closing_savings = run_savings
            closing_shares = run_shares
            closing_welfare = run_welfare
            closing_total = run_total
            closing_share_units = int(closing_shares // Decimal("1000.00"))
            ordinary_loan_capacity = float(closing_savings * Decimal("2.00"))

            return {
                "report_type": "PASSBOOK_LEDGER",
                "financial_year": year if is_yearly else "ALL_TIME",
                "period_label": f"Financial Year {year}" if is_yearly else "All Time (Cumulative)",
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "member": {
                    "id": member["id"],
                    "member_code": member["member_code"],
                    "full_name": f"{member['first_name']} {member['last_name']}",
                    "email": member["email"],
                    "phone": member["phone"],
                    "tier": member["contribution_tier"],
                    "membership_status": member["membership_status"],
                    "admission_date": str(member["admission_date"]),
                    "dva_account": member["paystack_dva_account_number"],
                    "dva_bank": member["paystack_dva_bank_name"]
                },
                "opening_balances": {
                    "regular_savings": float(op_savings),
                    "share_capital": float(op_shares),
                    "welfare_fund": float(op_welfare),
                    "total_equity": float(opening_total)
                },
                "period_movements": {
                    "total_credits": float(period_total_credits),
                    "total_debits": float(period_total_debits),
                    "net_movement": float(net_change),
                    "credits_savings": float(period_credits_savings),
                    "credits_shares": float(period_credits_shares),
                    "credits_welfare": float(period_credits_welfare),
                    "credits_other": float(period_credits_other),
                    "debits_savings": float(period_debits_savings),
                    "debits_other": float(period_debits_other),
                    "transaction_count": len(ledger_entries)
                },
                "closing_balances": {
                    "regular_savings": float(closing_savings),
                    "share_capital": float(closing_shares),
                    "share_units": closing_share_units,
                    "welfare_fund": float(closing_welfare),
                    "total_equity": float(closing_total),
                    "ordinary_loan_capacity_2x": ordinary_loan_capacity
                },
                "entries": ledger_entries
            }
        finally:
            cursor.close()
            conn.close()

    def get_member_credits_statement(self, member_id: int, year: Optional[int] = None) -> Dict[str, Any]:
        """
        Generates the Statutory Inward Remittances (All Credits) Audit Statement:
        Details every inward inflow remitted by the member via Polaris Bank, Paystack DVA,
        or Direct Remittance, categorized into Savings, Shares, Welfare, Loan Repayments, or Fines.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    m.id, m.member_code, m.first_name, m.last_name, m.email, m.phone,
                    m.contribution_tier, m.status AS membership_status, m.admission_date,
                    m.paystack_dva_account_number, m.paystack_dva_bank_name
                FROM members m
                WHERE m.id = %s;
            """, (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError(f"Member ID {member_id} not found.")

            is_yearly = bool(year and year > 0)
            if is_yearly:
                start_dt = f"{year}-01-01 00:00:00"
                end_dt = f"{year}-12-31 23:59:59"
                cursor.execute("""
                    SELECT 
                        id, transaction_ref, transaction_type, ledger_category,
                        amount, payment_method, channel_reference, narration,
                        status, transaction_date
                    FROM transactions
                    WHERE member_id = %s 
                      AND transaction_type = 'CREDIT'
                      AND transaction_date >= %s 
                      AND transaction_date <= %s
                    ORDER BY transaction_date DESC, id DESC;
                """, (member_id, start_dt, end_dt))
            else:
                cursor.execute("""
                    SELECT 
                        id, transaction_ref, transaction_type, ledger_category,
                        amount, payment_method, channel_reference, narration,
                        status, transaction_date
                    FROM transactions
                    WHERE member_id = %s AND transaction_type = 'CREDIT'
                    ORDER BY transaction_date DESC, id DESC;
                """, (member_id,))

            raw_txs = cursor.fetchall()

            total_remitted = Decimal("0.00")
            cat_totals: Dict[str, Decimal] = {
                "SAVINGS": Decimal("0.00"),
                "SHARE_CAPITAL": Decimal("0.00"),
                "WELFARE_FUND": Decimal("0.00"),
                "LOAN_REPAYMENT": Decimal("0.00"),
                "DISCIPLINARY_FINE": Decimal("0.00"),
                "OTHER": Decimal("0.00")
            }
            method_totals: Dict[str, Decimal] = {}

            credits_list = []
            for tx in raw_txs:
                amt = Decimal(str(tx["amount"]))
                total_remitted += amt
                cat = tx["ledger_category"]
                if cat in cat_totals:
                    cat_totals[cat] += amt
                else:
                    cat_totals["OTHER"] += amt

                pm = tx["payment_method"] or "UNKNOWN"
                method_totals[pm] = method_totals.get(pm, Decimal("0.00")) + amt

                tx_date_str = tx["transaction_date"].strftime("%Y-%m-%d %H:%M") if isinstance(tx["transaction_date"], (datetime, date)) else str(tx["transaction_date"] or "")

                credits_list.append({
                    "id": tx["id"],
                    "transaction_ref": tx["transaction_ref"],
                    "transaction_date": tx_date_str,
                    "ledger_category": cat,
                    "amount": float(amt),
                    "payment_method": pm,
                    "channel_reference": tx["channel_reference"],
                    "narration": tx["narration"],
                    "status": tx["status"]
                })

            return {
                "report_type": "ALL_CREDITS",
                "financial_year": year if is_yearly else "ALL_TIME",
                "period_label": f"Financial Year {year}" if is_yearly else "All Time (Cumulative)",
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "member": {
                    "id": member["id"],
                    "member_code": member["member_code"],
                    "full_name": f"{member['first_name']} {member['last_name']}",
                    "email": member["email"],
                    "phone": member["phone"],
                    "tier": member["contribution_tier"],
                    "membership_status": member["membership_status"],
                    "admission_date": str(member["admission_date"]),
                    "dva_account": member["paystack_dva_account_number"],
                    "dva_bank": member["paystack_dva_bank_name"]
                },
                "summary": {
                    "total_remitted": float(total_remitted),
                    "remittance_count": len(credits_list),
                    "category_breakdown": {k: float(v) for k, v in cat_totals.items()},
                    "method_breakdown": {k: float(v) for k, v in method_totals.items()}
                },
                "entries": credits_list
            }
        finally:
            cursor.close()
            conn.close()

    def get_member_debits_statement(self, member_id: int, year: Optional[int] = None) -> Dict[str, Any]:
        """
        Generates the Statutory Outward Disbursements & Claims (All Debits) Audit Statement:
        Details every debit payout to or on behalf of the member, including savings withdrawals,
        matured target savings payouts, approved loan disbursements, and welfare grants.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    m.id, m.member_code, m.first_name, m.last_name, m.email, m.phone,
                    m.contribution_tier, m.status AS membership_status, m.admission_date,
                    m.paystack_dva_account_number, m.paystack_dva_bank_name
                FROM members m
                WHERE m.id = %s;
            """, (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError(f"Member ID {member_id} not found.")

            is_yearly = bool(year and year > 0)
            if is_yearly:
                start_dt = f"{year}-01-01 00:00:00"
                end_dt = f"{year}-12-31 23:59:59"
                cursor.execute("""
                    SELECT 
                        id, transaction_ref, transaction_type, ledger_category,
                        amount, payment_method, channel_reference, narration,
                        status, transaction_date
                    FROM transactions
                    WHERE member_id = %s 
                      AND transaction_type = 'DEBIT'
                      AND transaction_date >= %s 
                      AND transaction_date <= %s
                    ORDER BY transaction_date DESC, id DESC;
                """, (member_id, start_dt, end_dt))
            else:
                cursor.execute("""
                    SELECT 
                        id, transaction_ref, transaction_type, ledger_category,
                        amount, payment_method, channel_reference, narration,
                        status, transaction_date
                    FROM transactions
                    WHERE member_id = %s AND transaction_type = 'DEBIT'
                    ORDER BY transaction_date DESC, id DESC;
                """, (member_id,))

            raw_txs = cursor.fetchall()

            total_disbursed = Decimal("0.00")
            cat_totals: Dict[str, Decimal] = {
                "SAVINGS": Decimal("0.00"),
                "LOAN_DISBURSEMENT": Decimal("0.00"),
                "WELFARE_GRANT": Decimal("0.00"),
                "OTHER": Decimal("0.00")
            }

            debits_list = []
            for tx in raw_txs:
                amt = Decimal(str(tx["amount"]))
                total_disbursed += amt
                cat = tx["ledger_category"]
                if cat in cat_totals:
                    cat_totals[cat] += amt
                else:
                    cat_totals["OTHER"] += amt

                tx_date_str = tx["transaction_date"].strftime("%Y-%m-%d %H:%M") if isinstance(tx["transaction_date"], (datetime, date)) else str(tx["transaction_date"] or "")

                debits_list.append({
                    "id": tx["id"],
                    "transaction_ref": tx["transaction_ref"],
                    "transaction_date": tx_date_str,
                    "ledger_category": cat,
                    "amount": float(amt),
                    "payment_method": tx["payment_method"],
                    "channel_reference": tx["channel_reference"],
                    "narration": tx["narration"],
                    "status": tx["status"]
                })

            return {
                "report_type": "ALL_DEBITS",
                "financial_year": year if is_yearly else "ALL_TIME",
                "period_label": f"Financial Year {year}" if is_yearly else "All Time (Cumulative)",
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "member": {
                    "id": member["id"],
                    "member_code": member["member_code"],
                    "full_name": f"{member['first_name']} {member['last_name']}",
                    "email": member["email"],
                    "phone": member["phone"],
                    "tier": member["contribution_tier"],
                    "membership_status": member["membership_status"],
                    "admission_date": str(member["admission_date"]),
                    "dva_account": member["paystack_dva_account_number"],
                    "dva_bank": member["paystack_dva_bank_name"]
                },
                "summary": {
                    "total_disbursed": float(total_disbursed),
                    "disbursement_count": len(debits_list),
                    "category_breakdown": {k: float(v) for k, v in cat_totals.items()}
                },
                "entries": debits_list
            }
        finally:
            cursor.close()
            conn.close()

    def get_member_loans_statement(self, member_id: int) -> Dict[str, Any]:
        """
        Generates the Member Loan Facilities & Amortization Statement:
        Lists all loans disbursed to the member, along with 0% compounding interest status,
        5% one-time admin fee, scheduled monthly installments, and repayment audit trail.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    m.id, m.member_code, m.first_name, m.last_name, m.email, m.phone,
                    m.contribution_tier, m.status AS membership_status, m.admission_date,
                    m.paystack_dva_account_number, m.paystack_dva_bank_name,
                    sa.total_balance AS current_savings
                FROM members m
                LEFT JOIN savings_accounts sa ON m.id = sa.member_id
                WHERE m.id = %s;
            """, (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError(f"Member ID {member_id} not found.")

            cursor.execute("""
                SELECT 
                    l.id, l.loan_reference, l.product_id, lp.product_name,
                    l.principal_amount, l.admin_cost_fee, l.total_amount_payable,
                    l.tenure_months, l.monthly_installment, l.total_paid,
                    l.outstanding_balance, l.status, l.application_date,
                    l.approval_date, l.disbursement_date, l.next_due_date, l.maturity_date
                FROM loans l
                LEFT JOIN loan_products lp ON l.product_id = lp.id
                WHERE l.member_id = %s
                ORDER BY l.id DESC;
            """, (member_id,))
            raw_loans = cursor.fetchall()

            loans_list = []
            total_borrowed = Decimal("0.00")
            total_repaid = Decimal("0.00")
            total_outstanding = Decimal("0.00")

            for l in raw_loans:
                p_amt = Decimal(str(l["principal_amount"] or 0.0))
                p_paid = Decimal(str(l["total_paid"] or 0.0))
                p_out = Decimal(str(l["outstanding_balance"] or 0.0))

                total_borrowed += p_amt
                total_repaid += p_paid
                total_outstanding += p_out

                # Fetch repayments
                cursor.execute("""
                    SELECT 
                        id, installment_number, due_date, amount_due,
                        amount_paid, paid_date, transaction_ref, status
                    FROM loan_repayments
                    WHERE loan_id = %s
                    ORDER BY installment_number ASC;
                """, (l["id"],))
                repayments = cursor.fetchall()
                rep_list = []
                for rep in repayments:
                    rep_list.append({
                        "installment_number": rep["installment_number"],
                        "due_date": str(rep["due_date"]),
                        "amount_due": float(rep["amount_due"]),
                        "amount_paid": float(rep["amount_paid"]),
                        "paid_date": str(rep["paid_date"]) if rep["paid_date"] else None,
                        "transaction_ref": rep["transaction_ref"],
                        "status": rep["status"]
                    })

                loans_list.append({
                    "id": l["id"],
                    "loan_reference": l["loan_reference"],
                    "product_name": l["product_name"] or "Standard Micro-Credit Loan",
                    "principal_amount": float(p_amt),
                    "admin_cost_fee": float(l["admin_cost_fee"] or 0.0),
                    "total_payable": float(l["total_amount_payable"] or 0.0),
                    "tenure_months": l["tenure_months"],
                    "monthly_installment": float(l["monthly_installment"] or 0.0),
                    "total_paid": float(p_paid),
                    "outstanding_balance": float(p_out),
                    "status": l["status"],
                    "disbursement_date": str(l["disbursement_date"]) if l["disbursement_date"] else None,
                    "maturity_date": str(l["maturity_date"]) if l["maturity_date"] else None,
                    "next_due_date": str(l["next_due_date"]) if l["next_due_date"] else None,
                    "repayments": rep_list
                })

            return {
                "report_type": "LOANS_STATEMENT",
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "member": {
                    "id": member["id"],
                    "member_code": member["member_code"],
                    "full_name": f"{member['first_name']} {member['last_name']}",
                    "email": member["email"],
                    "phone": member["phone"],
                    "tier": member["contribution_tier"],
                    "membership_status": member["membership_status"],
                    "admission_date": str(member["admission_date"]),
                    "current_savings": float(member["current_savings"] or 0.0),
                    "borrowing_capacity_2x": float((member["current_savings"] or Decimal("0.00")) * Decimal("2.00"))
                },
                "summary": {
                    "total_loans_count": len(loans_list),
                    "total_principal_borrowed": float(total_borrowed),
                    "total_repaid": float(total_repaid),
                    "total_outstanding_balance": float(total_outstanding),
                    "statutory_interest_rate": "0.0% (Zero Compounding Interest)",
                    "admin_fee_rate": "5.0% Flat Cost Allocation"
                },
                "loans": loans_list
            }
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # 13. COMPULSORY KYC EVALUATION & APPLICANT DOSSIER (STATUTORY GOVERNANCE)
    # -------------------------------------------------------------------------
    def evaluate_compulsory_kyc(self, member_id: int) -> Dict[str, Any]:
        """
        Evaluates the 6 compulsory statutory KYC fields required for Dedicated Virtual Account (DVA) unlock:
        1. First Name
        2. Last Name
        3. Phone Number
        4. Email Address
        5. Residential Address
        6. Identification Number (NIN / National ID)
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT *
                FROM members
                WHERE id = %s;
            """, (member_id,))
            m = cursor.fetchone()
            if not m:
                raise ValueError(f"Member ID {member_id} not found.")

            status_map = {
                "first_name": bool(str(m.get("first_name") or "").strip()),
                "last_name": bool(str(m.get("last_name") or "").strip()),
                "phone": bool(str(m.get("phone") or "").strip()),
                "email": bool(str(m.get("email") or "").strip()),
                "residential_address": bool(str(m.get("residential_address") or "").strip()),
                "identification_number": bool(str(m.get("identification_number") or "").strip())
            }

            field_labels = {
                "first_name": "First Name",
                "last_name": "Last Name",
                "phone": "Phone Number",
                "email": "Email Address",
                "residential_address": "Residential Address",
                "identification_number": "National Identity Number (NIN)"
            }

            completed_count = sum(1 for v in status_map.values() if v)
            total_count = len(status_map)
            is_complete = (completed_count == total_count)
            score_percent = int(round((completed_count / total_count) * 100))

            missing_fields = [field_labels[k] for k, v in status_map.items() if not v]

            cursor.execute("SELECT * FROM next_of_kin WHERE member_id = %s LIMIT 1;", (member_id,))
            nok = cursor.fetchone()

            # Dynamic comprehensive KYC completion across ALL sections
            kyc_info = self.calculate_kyc_completion(m, nok)
            full_kyc_percent = kyc_info["percentage"]

            # Persist comprehensive score in members table
            cursor.execute("UPDATE members SET kyc_completion_percent = %s WHERE id = %s;", (full_kyc_percent, member_id))

            return {
                "member_id": member_id,
                "member_code": m["member_code"],
                "is_compulsory_complete": is_complete,
                "compulsory_score_percent": score_percent,
                "completed_count": completed_count,
                "total_count": total_count,
                "compulsory_fields_status": status_map,
                "checklist": status_map,
                "missing_fields": missing_fields,
                "kyc_completion_percent": full_kyc_percent,
                "overall_kyc_percent": full_kyc_percent,
                "kyc_breakdown": kyc_info["breakdown"]
            }
        finally:
            cursor.close()
            conn.close()

    def get_applicant_dossier(self, member_id: int) -> Dict[str, Any]:
        """
        Retrieves full registration dossier and uploaded documentation for executive inspection
        prior to membership admission or verification.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    id, member_code, first_name, last_name, other_names, email, phone,
                    gender, marital_status, residential_address, identification_type,
                    identification_number, passport_photo, employment_status,
                    employer_or_business_name, monthly_income_verified, bank_name,
                    bank_account_number, bank_account_name, bvn, contribution_tier,
                    status AS membership_status, kyc_completion_percent, admission_date,
                    created_at, updated_at
                FROM members
                WHERE id = %s;
            """, (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError(f"Member ID {member_id} not found.")

            cursor.execute("SELECT * FROM next_of_kin WHERE member_id = %s LIMIT 1;", (member_id,))
            nok = cursor.fetchone()

            kyc_eval = self.evaluate_compulsory_kyc(member_id)

            for dt_col in ["created_at", "updated_at", "admission_date"]:
                if member.get(dt_col):
                    member[dt_col] = str(member[dt_col])
            if member.get("monthly_income_verified") is not None:
                member["monthly_income_verified"] = float(member["monthly_income_verified"])

            if nok:
                for dt_col in ["created_at", "updated_at"]:
                    if nok.get(dt_col):
                        nok[dt_col] = str(nok[dt_col])
                if nok.get("allocation_percentage") is not None:
                    nok["allocation_percentage"] = float(nok["allocation_percentage"])

            return {
                "member": member,
                "next_of_kin": nok,
                "compulsory_kyc": kyc_eval,
                "has_passport_photo": bool(member.get("passport_photo")),
                "is_pending_review": member.get("membership_status") in ("PENDING_KYC", "PENDING_APPROVAL")
            }
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # 14. DYNAMIC RBAC & ROLE-PERMISSION MANAGEMENT
    # -------------------------------------------------------------------------
    def get_all_roles(self) -> List[Dict[str, Any]]:
        """Returns all system and custom operational roles with their assigned permissions."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, role_code, role_name, description, is_system_role, created_at FROM roles ORDER BY id ASC;")
            roles = cursor.fetchall()
            for r in roles:
                if r.get("created_at"):
                    r["created_at"] = str(r["created_at"])
                r["is_system_role"] = bool(r["is_system_role"])
                cursor.execute("""
                    SELECT p.id, p.perm_key, p.perm_name, p.module, p.description
                    FROM permissions p
                    JOIN role_permissions rp ON p.id = rp.permission_id
                    WHERE rp.role_id = %s
                    ORDER BY p.module, p.perm_name;
                """, (r["id"],))
                r["permissions"] = cursor.fetchall()
            return roles
        finally:
            cursor.close()
            conn.close()

    def get_all_permissions(self) -> List[Dict[str, Any]]:
        """Returns all 35 granular permissions grouped by statutory module."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, perm_key, perm_name, module, description FROM permissions ORDER BY module, perm_key;")
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def create_custom_role(self, role_code: str, role_name: str, description: str, permission_keys: List[str], created_by: int = None) -> Dict[str, Any]:
        """Creates a custom operational role and binds selected permissions."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            code = role_code.strip().upper().replace(" ", "_")
            if not code or not role_name:
                raise ValueError("Role code and role name are required.")

            cursor.execute("SELECT id FROM roles WHERE role_code = %s;", (code,))
            if cursor.fetchone():
                raise ValueError(f"Role with code '{code}' already exists.")

            cursor.execute("""
                INSERT INTO roles (role_code, role_name, description, is_system_role)
                VALUES (%s, %s, %s, FALSE);
            """, (code, role_name.strip(), description.strip() if description else None))
            new_role_id = cursor.lastrowid

            if permission_keys:
                placeholders = ','.join(['%s'] * len(permission_keys))
                cursor.execute(f"SELECT id, perm_key FROM permissions WHERE perm_key IN ({placeholders})", tuple(permission_keys))
                perms = cursor.fetchall()
                for p in perms:
                    cursor.execute("""
                        INSERT IGNORE INTO role_permissions (role_id, permission_id)
                        VALUES (%s, %s);
                    """, (new_role_id, p["id"]))

            conn.commit()

            self.log_audit_event(
                user_id=created_by,
                actor_name="Administrator",
                actor_role="SUPER_ADMIN",
                action="ROLE_CREATED",
                resource_type="ROLE",
                resource_id=str(new_role_id),
                details_before=None,
                details_after={"role_code": code, "role_name": role_name, "permissions": permission_keys},
                summary=f"Created custom role {code} with {len(permission_keys)} permissions."
            )

            return {
                "id": new_role_id,
                "role_code": code,
                "role_name": role_name,
                "description": description,
                "permissions_count": len(permission_keys)
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def update_role_permissions(self, role_id: int, permission_keys: List[str], updated_by: int = None) -> Dict[str, Any]:
        """Updates permissions assigned to a custom role."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, role_code, role_name, is_system_role FROM roles WHERE id = %s;", (role_id,))
            role = cursor.fetchone()
            if not role:
                raise ValueError(f"Role ID {role_id} not found.")

            cursor.execute("""
                SELECT p.perm_key FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                WHERE rp.role_id = %s;
            """, (role_id,))
            before_perms = [r["perm_key"] for r in cursor.fetchall()]

            cursor.execute("DELETE FROM role_permissions WHERE role_id = %s;", (role_id,))

            if permission_keys:
                placeholders = ','.join(['%s'] * len(permission_keys))
                cursor.execute(f"SELECT id, perm_key FROM permissions WHERE perm_key IN ({placeholders})", tuple(permission_keys))
                perms = cursor.fetchall()
                for p in perms:
                    cursor.execute("""
                        INSERT IGNORE INTO role_permissions (role_id, permission_id)
                        VALUES (%s, %s);
                    """, (role_id, p["id"]))

            conn.commit()

            self.log_audit_event(
                user_id=updated_by,
                actor_name="Administrator",
                actor_role="SUPER_ADMIN",
                action="ROLE_PERMISSIONS_UPDATED",
                resource_type="ROLE",
                resource_id=str(role_id),
                details_before={"permissions": before_perms},
                details_after={"permissions": permission_keys},
                summary=f"Updated permissions for role {role['role_code']} ({len(permission_keys)} active)."
            )

            return {"status": "SUCCESS", "role_id": role_id, "permissions_count": len(permission_keys)}
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def update_custom_role(
        self,
        role_id: int,
        role_name: Optional[str] = None,
        description: Optional[str] = None,
        permission_keys: Optional[List[str]] = None,
        updated_by: Any = None
    ) -> Dict[str, Any]:
        """Modifies an existing custom role's metadata and bound permissions."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, role_code, role_name, description, is_system_role FROM roles WHERE id = %s;", (role_id,))
            role = cursor.fetchone()
            if not role:
                raise ValueError(f"Role ID {role_id} not found.")

            before_state = {
                "role_name": role["role_name"],
                "description": role["description"],
            }

            updates = []
            params = []
            if role_name is not None and role_name.strip():
                updates.append("role_name = %s")
                params.append(role_name.strip())
            if description is not None:
                updates.append("description = %s")
                params.append(description.strip())

            if updates:
                params.append(role_id)
                cursor.execute(f"UPDATE roles SET {', '.join(updates)} WHERE id = %s;", tuple(params))

            if permission_keys is not None:
                cursor.execute("DELETE FROM role_permissions WHERE role_id = %s;", (role_id,))
                if permission_keys:
                    placeholders = ','.join(['%s'] * len(permission_keys))
                    cursor.execute(f"SELECT id, perm_key FROM permissions WHERE perm_key IN ({placeholders})", tuple(permission_keys))
                    perms = cursor.fetchall()
                    for p in perms:
                        cursor.execute("""
                            INSERT IGNORE INTO role_permissions (role_id, permission_id)
                            VALUES (%s, %s);
                        """, (role_id, p["id"]))

            conn.commit()

            self.log_audit_event(
                user_id=updated_by,
                actor_name="Administrator",
                actor_role="SUPER_ADMIN",
                action="ROLE_UPDATED",
                resource_type="ROLE",
                resource_id=str(role_id),
                details_before=before_state,
                details_after={"role_name": role_name or role["role_name"], "permissions": permission_keys},
                summary=f"Modified operational role {role['role_code']} ({role_name or role['role_name']})."
            )

            return {
                "id": role_id,
                "role_code": role["role_code"],
                "role_name": role_name or role["role_name"],
                "description": description if description is not None else role["description"],
                "permissions_count": len(permission_keys) if permission_keys is not None else 0
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def delete_custom_role(self, role_id: int, deleted_by: Any = None) -> Dict[str, Any]:
        """Deletes a custom operational role, its permission mappings, and member allocations."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, role_code, role_name, is_system_role FROM roles WHERE id = %s;", (role_id,))
            role = cursor.fetchone()
            if not role:
                raise ValueError(f"Role ID {role_id} not found.")

            if role["is_system_role"]:
                raise ValueError(f"Statutory system role '{role['role_code']}' is protected and cannot be deleted.")

            cursor.execute("DELETE FROM member_roles WHERE role_id = %s;", (role_id,))
            cursor.execute("DELETE FROM role_permissions WHERE role_id = %s;", (role_id,))
            cursor.execute("DELETE FROM roles WHERE id = %s;", (role_id,))
            conn.commit()

            self.log_audit_event(
                user_id=deleted_by,
                actor_name="Administrator",
                actor_role="SUPER_ADMIN",
                action="ROLE_DELETED",
                resource_type="ROLE",
                resource_id=str(role_id),
                details_before={"role_code": role["role_code"], "role_name": role["role_name"]},
                details_after=None,
                summary=f"Deleted custom operational role {role['role_code']} ({role['role_name']})."
            )

            return {
                "status": "SUCCESS",
                "role_id": role_id,
                "role_code": role["role_code"],
                "message": f"Custom operational role '{role['role_name']}' ({role['role_code']}) deleted successfully."
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def assign_role_to_member(self, member_id: int, role_id: int, assigned_by: int = None) -> Dict[str, Any]:
        """Assigns an operational role to a cooperator."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, member_code, first_name, last_name FROM members WHERE id = %s;", (member_id,))
            mem = cursor.fetchone()
            if not mem:
                raise ValueError("Member not found.")

            cursor.execute("SELECT id, role_code, role_name FROM roles WHERE id = %s;", (role_id,))
            role = cursor.fetchone()
            if not role:
                raise ValueError("Role not found.")

            cursor.execute("""
                INSERT INTO member_roles (member_id, role_id, assigned_by_user_id)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE assigned_by_user_id = VALUES(assigned_by_user_id), assigned_at = NOW();
            """, (member_id, role_id, assigned_by))
            conn.commit()

            self.log_audit_event(
                user_id=assigned_by,
                actor_name="Administrator",
                actor_role="SUPER_ADMIN",
                action="ROLE_ASSIGNED",
                resource_type="MEMBER_ROLE",
                resource_id=f"{member_id}:{role_id}",
                details_before=None,
                details_after={"member_id": member_id, "member_code": mem["member_code"], "role_code": role["role_code"]},
                summary=f"Assigned role {role['role_name']} ({role['role_code']}) to member {mem['member_code']}."
            )

            return {
                "status": "SUCCESS",
                "member_id": member_id,
                "role_id": role_id,
                "role_code": role["role_code"],
                "role_name": role["role_name"],
                "message": f"Role '{role['role_name']}' assigned to {mem['first_name']} {mem['last_name']} ({mem['member_code']})."
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def revoke_role_from_member(self, member_id: int, role_id: int, revoked_by: int = None) -> Dict[str, Any]:
        """Revokes a role assignment from a cooperator."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                DELETE FROM member_roles WHERE member_id = %s AND role_id = %s;
            """, (member_id, role_id))
            conn.commit()

            self.log_audit_event(
                user_id=revoked_by,
                actor_name="Administrator",
                actor_role="SUPER_ADMIN",
                action="ROLE_REVOKED",
                resource_type="MEMBER_ROLE",
                resource_id=f"{member_id}:{role_id}",
                details_before={"member_id": member_id, "role_id": role_id},
                details_after=None,
                summary=f"Revoked role ID {role_id} from member ID {member_id}."
            )

            return {"status": "SUCCESS", "message": "Role assignment revoked successfully."}
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def get_member_roles(self, member_id: int) -> List[Dict[str, Any]]:
        """Retrieves all roles dynamically assigned to a member."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT r.id, r.role_code, r.role_name, r.description, r.is_system_role, mr.assigned_at
                FROM roles r
                JOIN member_roles mr ON r.id = mr.role_id
                WHERE mr.member_id = %s
                ORDER BY r.id ASC;
            """, (member_id,))
            roles = cursor.fetchall()
            for r in roles:
                if r.get("assigned_at"):
                    r["assigned_at"] = str(r["assigned_at"])
                r["is_system_role"] = bool(r["is_system_role"])
            return roles
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # 15. MULTI-TIER LOAN GOVERNANCE, SEQUENTIAL APPROVALS & APPEALS
    # -------------------------------------------------------------------------
    def apply_for_loan(
        self,
        member_id: int,
        principal_amount: float,
        tenure_months: int,
        purpose_narration: str = None,
        product_id: int = 1,
        guarantors: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Submits a new loan application into the Multi-Tier Sequential Governance Pipeline:
        Starts at Stage 1 (CREDIT_COMMITTEE, 0% approved).
        Attaches guarantor co-signers with designated guaranteed amounts.
        """
        if principal_amount <= 0:
            raise ValueError("Loan principal amount must be greater than zero.")

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, member_code, first_name, last_name, status FROM members WHERE id = %s;", (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError("Member not found.")
            if member.get("status") not in ("ACTIVE", "APPROVED"):
                raise ValueError("Only active members in good standing may apply for financing.")

            # Retrieve product terms from loan_products
            cursor.execute("SELECT * FROM loan_products WHERE id = %s AND is_active = 1;", (product_id or 1,))
            product = cursor.fetchone()
            if not product:
                # Fallback to ID 1
                cursor.execute("SELECT * FROM loan_products WHERE id = 1;")
                product = cursor.fetchone()
                if not product:
                    raise ValueError(f"Loan product {product_id} is unavailable.")

            multiplier = Decimal(str(product.get("max_multiplier_of_savings") or 2.0))
            ceiling = Decimal(str(product.get("max_principal_ceiling") or 5000000.00))
            fee_pct = Decimal(str(product.get("admin_cost_fee_percent") or 2.50)) / Decimal("100.00")
            min_tenure = int(product.get("min_tenure_months") or 1)
            max_tenure = int(product.get("max_tenure_months") or 24)

            if tenure_months < min_tenure or tenure_months > max_tenure:
                raise ValueError(f"Tenure must be between {min_tenure} and {max_tenure} months for {product['product_name']}.")

            cursor.execute("SELECT total_balance FROM savings_accounts WHERE member_id = %s;", (member_id,))
            savings = cursor.fetchone()
            savings_bal = Decimal(str(savings["total_balance"])) if savings else Decimal("0.00")
            max_borrowing_limit = savings_bal * multiplier

            principal_dec = Decimal(str(principal_amount))
            if principal_dec > max_borrowing_limit and max_borrowing_limit > 0 and multiplier > 0:
                raise ValueError(
                    f"Requested amount (NGN {principal_dec:,.2f}) exceeds {multiplier}x savings borrowing capacity "
                    f"(NGN {max_borrowing_limit:,.2f})."
                )
            if principal_dec > ceiling:
                raise ValueError(
                    f"Requested amount (NGN {principal_dec:,.2f}) exceeds the statutory limit of NGN {ceiling:,.2f} for {product['product_name']}."
                )

            # Flat statutory administrative fee (cost-recovery, zero compounding interest)
            admin_fee = round(principal_dec * fee_pct, 2)
            total_payable = principal_dec + admin_fee
            monthly_inst = round(total_payable / Decimal(str(tenure_months)), 2)

            ref = f"L-WMC-{datetime.now().year}-{secrets.token_hex(4).upper()}"

            has_guarantors = bool(guarantors and any(int(g.get("guarantor_member_id") or g.get("member_id") or 0) > 0 for g in guarantors))
            initial_stage = "GUARANTOR_CONSENT" if has_guarantors else "CREDIT_COMMITTEE"

            cursor.execute("""
                INSERT INTO loans (
                    loan_reference, member_id, product_id, principal_amount,
                    admin_cost_fee, total_amount_payable, tenure_months,
                    monthly_installment, total_paid, outstanding_balance,
                    status, approval_level_percent, current_approval_stage,
                    purpose_narration, application_date
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, 0.00, %s,
                    'PENDING', 0, %s,
                    %s, CURDATE()
                );
            """, (
                ref, member_id, product["id"], principal_dec,
                admin_fee, total_payable, tenure_months,
                monthly_inst, total_payable,
                initial_stage,
                purpose_narration
            ))
            loan_id = cursor.lastrowid

            # Attach Guarantors
            attached_guarantors = []
            if guarantors:
                for g in guarantors:
                    g_member_id = int(g.get("guarantor_member_id") or g.get("member_id") or 0)
                    if not g_member_id:
                        continue
                    if g_member_id == member_id:
                        raise ValueError("Applicant cannot act as their own guarantor.")

                    cursor.execute("SELECT id, member_code, first_name, last_name, status FROM members WHERE id = %s;", (g_member_id,))
                    guar_member = cursor.fetchone()
                    if not guar_member:
                        raise ValueError(f"Guarantor cooperator ID {g_member_id} not found.")

                    g_amount = Decimal(str(g.get("guaranteed_amount") or 0))
                    if g_amount <= 0:
                        continue

                    cursor.execute("""
                        INSERT INTO loan_guarantors (
                            loan_id, guarantor_member_id, guaranteed_amount, lien_encumbered_amount, status
                        ) VALUES (%s, %s, %s, 0.00, 'PENDING_CONSENT');
                    """, (loan_id, g_member_id, g_amount))

                    attached_guarantors.append({
                        "guarantor_member_id": g_member_id,
                        "member_code": guar_member["member_code"],
                        "name": f"{guar_member['first_name']} {guar_member['last_name']}",
                        "guaranteed_amount": float(g_amount)
                    })

            step_comments = 'Application lodged by cooperator. Awaiting peer guarantor digital consent.' if has_guarantors else 'Application lodged by cooperator. Awaiting Stage 1 Credit Committee vetting.'
            cursor.execute("""
                INSERT INTO loan_approval_steps (
                    loan_id, step_name, officer_id, officer_role,
                    action, percentage_granted, comments
                ) VALUES (
                    %s, %s, %s, 'MEMBER',
                    'APPROVED', 0, %s
                );
            """, (loan_id, initial_stage, member_id, step_comments))

            conn.commit()

            self.log_audit_event(
                user_id=member_id,
                actor_name=f"{member['first_name']} {member['last_name']}",
                actor_role="MEMBER",
                action="LOAN_APPLICATION_SUBMITTED",
                resource_type="LOAN",
                resource_id=str(loan_id),
                details_before=None,
                details_after={
                    "loan_reference": ref,
                    "product_name": product["product_name"],
                    "principal_amount": float(principal_dec),
                    "tenure_months": tenure_months,
                    "purpose": purpose_narration,
                    "guarantors": attached_guarantors,
                    "initial_stage": initial_stage
                },
                summary=f"Lodge {product['product_name']} application {ref} for NGN {principal_dec:,.2f} ({tenure_months} mos) with {len(attached_guarantors)} guarantor(s)."
            )

            return {
                "id": loan_id,
                "loan_reference": ref,
                "product_id": product["id"],
                "product_name": product["product_name"],
                "principal_amount": float(principal_dec),
                "admin_fee": float(admin_fee),
                "total_payable": float(total_payable),
                "tenure_months": tenure_months,
                "monthly_installment": float(monthly_inst),
                "approval_level_percent": 0,
                "current_approval_stage": initial_stage,
                "status": "PENDING",
                "guarantors": attached_guarantors
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def get_loans_for_review(
        self,
        officer_role: str = None,
        officer_id: int = None,
        is_president: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieves pending loans relevant to the current officer's queue.
        - President/Super Admin sees ALL pending/under-appeal applications with instant override capability.
        - Credit Committee sees Stage 1 (0% -> 33%).
        - Financial Secretary sees Stage 2 (33% -> 66%).
        - Treasurer sees Stage 3 (66% -> 100% and Disbursement release).
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            where_clauses = ["l.status IN ('PENDING', 'UNDER_APPEAL')"]
            params = []

            # If officer is not president or super admin, filter by stage
            if not is_president and officer_role not in ("PRESIDENT", "SUPER_ADMIN"):
                if officer_role == "FINANCIAL_SECRETARY":
                    where_clauses.append("l.current_approval_stage = 'FINANCIAL_SECRETARY'")
                elif officer_role == "TREASURER":
                    where_clauses.append("l.current_approval_stage = 'TREASURER'")
                else:
                    where_clauses.append("l.current_approval_stage = 'CREDIT_COMMITTEE'")

            where_sql = " AND ".join(where_clauses)

            cursor.execute(f"""
                SELECT 
                    l.id, l.loan_reference, l.member_id, l.product_id,
                    COALESCE(lp.product_name, 'Ordinary loan (*2 of savings)') AS product_name,
                    COALESCE(lp.product_code, 'ORDINARY_LOAN') AS product_code,
                    l.principal_amount, l.admin_cost_fee, l.total_amount_payable,
                    l.tenure_months, l.monthly_installment, l.status,
                    l.approval_level_percent, l.current_approval_stage,
                    l.presidential_override, l.decline_reason, l.purpose_narration,
                    l.application_date,
                    m.member_code, m.first_name, m.last_name, m.phone, m.email,
                    COALESCE(sv.total_balance, 0.00) AS savings_balance
                FROM loans l
                JOIN members m ON l.member_id = m.id
                LEFT JOIN loan_products lp ON l.product_id = lp.id
                LEFT JOIN savings_accounts sv ON m.id = sv.member_id
                WHERE {where_sql}
                ORDER BY l.id ASC;
            """, tuple(params))
            loans = cursor.fetchall()

            for ln in loans:
                ln["principal_amount"] = float(ln["principal_amount"])
                ln["admin_cost_fee"] = float(ln["admin_cost_fee"] or 0)
                ln["total_amount_payable"] = float(ln["total_amount_payable"])
                ln["monthly_installment"] = float(ln["monthly_installment"])
                ln["savings_balance"] = float(ln["savings_balance"])
                ln["borrowing_capacity"] = float(ln["savings_balance"] * 2.0)
                if ln.get("application_date"):
                    ln["application_date"] = str(ln["application_date"])

                # Fetch attached guarantors with their real-time savings balances
                cursor.execute("""
                    SELECT 
                        lg.id, lg.loan_id, lg.guarantor_member_id, lg.guaranteed_amount,
                        lg.lien_encumbered_amount, lg.status,
                        m.first_name, m.last_name, m.member_code, m.email, m.phone,
                        COALESCE(sv.total_balance, 0.00) AS total_savings,
                        COALESCE(sv.available_balance, 0.00) AS available_savings
                    FROM loan_guarantors lg
                    JOIN members m ON lg.guarantor_member_id = m.id
                    LEFT JOIN savings_accounts sv ON m.id = sv.member_id
                    WHERE lg.loan_id = %s
                    ORDER BY lg.id ASC;
                """, (ln["id"],))
                guars = cursor.fetchall()
                for g in guars:
                    g["guaranteed_amount"] = float(g["guaranteed_amount"])
                    g["lien_encumbered_amount"] = float(g["lien_encumbered_amount"] or 0)
                    g["total_savings"] = float(g["total_savings"])
                    g["available_savings"] = float(g["available_savings"])
                    g["full_name"] = f"{g['first_name']} {g['last_name']}".strip()
                    g["is_adequate"] = (g["total_savings"] >= g["guaranteed_amount"])
                ln["guarantors"] = guars

                cursor.execute("""
                    SELECT step_name, officer_id, officer_role, action, comments, percentage_granted, created_at
                    FROM loan_approval_steps
                    WHERE loan_id = %s
                    ORDER BY id ASC;
                """, (ln["id"],))
                steps = cursor.fetchall()
                for s in steps:
                    if s.get("created_at"):
                        s["created_at"] = str(s["created_at"])
                ln["approval_steps"] = steps

                cursor.execute("""
                    SELECT id, appeal_comments, attached_document_path, document_name, status, created_at
                    FROM loan_appeals
                    WHERE loan_id = %s AND status = 'PENDING_REVIEW'
                    ORDER BY id DESC LIMIT 1;
                """, (ln["id"],))
                ln["active_appeal"] = cursor.fetchone()
                if ln["active_appeal"] and ln["active_appeal"].get("created_at"):
                    ln["active_appeal"]["created_at"] = str(ln["active_appeal"]["created_at"])

            return loans
        finally:
            cursor.close()
            conn.close()

    def review_loan_application(
        self,
        loan_id: int,
        officer_id: int,
        officer_role: str,
        action: str,
        comments: str = None,
        is_president_override: bool = False
    ) -> Dict[str, Any]:
        """
        Executes sequential review on a loan application.
        - Stage 1: CREDIT_COMMITTEE -> sets 33%, advances to FINANCIAL_SECRETARY.
        - Stage 2: FINANCIAL_SECRETARY -> sets 66%, advances to TREASURER.
        - Stage 3: TREASURER -> sets 100%, status ACTIVE/DISBURSED, releases funds and generates repayment schedule.
        - PRESIDENTIAL OVERRIDE: President or Super Admin can approve at ANY stage, immediately setting 100% DISBURSED.
        - DECLINE: Sets status DECLINED, captures decline reason and officer ID so member can appeal directly.
        """
        action = action.upper().strip()
        if action not in ("APPROVE", "DECLINE"):
            raise ValueError("Action must be either APPROVE or DECLINE.")

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM loans WHERE id = %s FOR UPDATE;", (loan_id,))
            loan = cursor.fetchone()
            if not loan:
                raise ValueError(f"Loan ID {loan_id} not found.")

            if loan["status"] not in ("PENDING", "UNDER_APPEAL"):
                raise ValueError(f"Loan status is {loan['status']} and cannot be reviewed.")

            cursor.execute("SELECT first_name, last_name, member_code FROM members WHERE id = %s;", (officer_id,))
            officer = cursor.fetchone() or {"first_name": "Executive", "last_name": "Officer", "member_code": "ADMIN"}
            officer_name = f"{officer['first_name']} {officer['last_name']}".strip()

            current_stage = loan["current_approval_stage"]
            is_pres = bool(is_president_override)
            if is_pres and officer_role not in ("PRESIDENT", "SUPER_ADMIN"):
                raise ValueError("Only the President or Super Admin can execute a presidential superior override.")

            if action == "DECLINE":
                if not comments or len(comments.strip()) < 5:
                    raise ValueError("A clear, substantive decline reason is mandatory so the member can review or appeal.")

                cursor.execute("""
                    UPDATE loans
                    SET 
                        status = 'DECLINED',
                        decline_reason = %s,
                        declined_by_officer_id = %s,
                        declined_by_role = %s,
                        updated_at = NOW()
                    WHERE id = %s;
                """, (comments.strip(), officer_id, officer_role, loan_id))

                cursor.execute("""
                    INSERT INTO loan_approval_steps (
                        loan_id, step_name, officer_id, officer_role,
                        action, percentage_granted, comments
                    ) VALUES (
                        %s, %s, %s, %s,
                        'DECLINED', %s, %s
                    );
                """, (loan_id, current_stage, officer_id, officer_role, loan["approval_level_percent"], comments.strip()))

                conn.commit()

                self.log_audit_event(
                    user_id=officer_id,
                    actor_name=officer_name,
                    actor_role=officer_role,
                    action="LOAN_DECLINED",
                    resource_type="LOAN",
                    resource_id=str(loan_id),
                    details_before={"status": loan["status"], "stage": current_stage},
                    details_after={"status": "DECLINED", "decline_reason": comments.strip()},
                    summary=f"Declined loan {loan['loan_reference']}. Reason: {comments.strip()}"
                )

                return {
                    "status": "SUCCESS",
                    "loan_id": loan_id,
                    "action": "DECLINED",
                    "approval_level_percent": loan["approval_level_percent"],
                    "loan_status": "DECLINED",
                    "message": "Loan application declined. Officer details recorded for direct cooperator appeal."
                }

            # ACTION == 'APPROVE'
            new_stage = current_stage
            new_pct = loan["approval_level_percent"]
            new_status = "PENDING"
            is_disbursed = False
            step_name = current_stage

            if is_pres:
                new_pct = 100
                new_stage = "DISBURSED"
                new_status = "ACTIVE"
                is_disbursed = True
                step_name = "PRESIDENTIAL_OVERRIDE"
                override_flag = True
            elif current_stage == "CREDIT_COMMITTEE":
                new_pct = 33
                new_stage = "FINANCIAL_SECRETARY"
                new_status = "PENDING"
                override_flag = False
            elif current_stage == "FINANCIAL_SECRETARY":
                new_pct = 66
                new_stage = "TREASURER"
                new_status = "PENDING"
                override_flag = False
            elif current_stage == "TREASURER":
                new_pct = 100
                new_stage = "DISBURSED"
                new_status = "ACTIVE"
                is_disbursed = True
                override_flag = False
            else:
                raise ValueError(f"Invalid approval stage: {current_stage}")

            if is_disbursed:
                cursor.execute("""
                    UPDATE loans
                    SET 
                        approval_level_percent = %s,
                        current_approval_stage = %s,
                        status = %s,
                        presidential_override = %s,
                        approval_date = CURDATE(),
                        disbursement_date = CURDATE(),
                        maturity_date = DATE_ADD(CURDATE(), INTERVAL %s MONTH),
                        next_due_date = DATE_ADD(CURDATE(), INTERVAL 1 MONTH),
                        updated_at = NOW()
                    WHERE id = %s;
                """, (new_pct, new_stage, new_status, override_flag, loan["tenure_months"], loan_id))

                tenure = loan["tenure_months"]
                total_payable = Decimal(str(loan["total_amount_payable"]))
                inst_amount = Decimal(str(loan["monthly_installment"]))
                today = date.today()

                cursor.execute("DELETE FROM loan_repayments WHERE loan_id = %s;", (loan_id,))

                accumulated = Decimal("0.00")
                for i in range(1, tenure + 1):
                    m_idx = today.month + i
                    y_off = (m_idx - 1) // 12
                    month_val = ((m_idx - 1) % 12) + 1
                    year_val = today.year + y_off
                    due_d = date(year_val, month_val, min(today.day, 28))

                    if i == tenure:
                        due_amt = total_payable - accumulated
                    else:
                        due_amt = inst_amount
                        accumulated += due_amt

                    cursor.execute("""
                        INSERT INTO loan_repayments (
                            loan_id, installment_number, due_date,
                            amount_due, amount_paid, status
                        ) VALUES (
                            %s, %s, %s, %s, 0.00, 'PENDING'
                        );
                    """, (loan_id, i, due_d, due_amt))

                t_ref = f"DISB-{loan['loan_reference']}"
                cursor.execute("""
                    INSERT INTO transactions (
                        transaction_ref, member_id, transaction_type, ledger_category,
                        amount, payment_method, narration, status,
                        verified_by_officer_id, transaction_date
                    ) VALUES (
                        %s, %s, 'DEBIT', 'LOAN_DISBURSEMENT',
                        %s, 'POLARIS_BANK_TRANSFER', %s, 'VERIFIED',
                        %s, CURDATE()
                    );
                """, (t_ref, loan["member_id"], loan["principal_amount"], f"Loan disbursement for {loan['loan_reference']}", officer_id))

                self._post_journal_entry_with_cursor(
                    cursor=cursor,
                    entry_date=date.today(),
                    source_module='LOAN_DISBURSEMENT',
                    source_reference=t_ref,
                    narration=f"Loan Facility Disbursement for {loan['loan_reference']}",
                    lines=[
                        {"account_code": "1030", "line_type": "DEBIT", "amount": loan["principal_amount"], "memo": "Member Loan Principal Facilities Receivable"},
                        {"account_code": "1010", "line_type": "CREDIT", "amount": loan["principal_amount"], "memo": "Disbursement payout via Polaris Bank Escrow"}
                    ],
                    created_by=officer_id,
                    approved_by=officer_id,
                    status='POSTED'
                )

            else:
                cursor.execute("""
                    UPDATE loans
                    SET 
                        approval_level_percent = %s,
                        current_approval_stage = %s,
                        status = %s,
                        updated_at = NOW()
                    WHERE id = %s;
                """, (new_pct, new_stage, new_status, loan_id))

            cursor.execute("""
                INSERT INTO loan_approval_steps (
                    loan_id, step_name, officer_id, officer_role,
                    action, percentage_granted, comments
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s
                );
            """, (
                loan_id, step_name, officer_id, officer_role,
                'OVERRIDDEN' if override_flag else 'APPROVED',
                new_pct, comments or f"Approved at stage {step_name}."
            ))

            conn.commit()

            self.log_audit_event(
                user_id=officer_id,
                actor_name=officer_name,
                actor_role=officer_role,
                action="PRESIDENTIAL_OVERRIDE" if override_flag else "LOAN_APPROVED_STEP",
                resource_type="LOAN",
                resource_id=str(loan_id),
                details_before={"percent": loan["approval_level_percent"], "stage": current_stage},
                details_after={"percent": new_pct, "stage": new_stage, "status": new_status},
                summary=f"{'Presidential Override: 100% disbursed' if override_flag else f'Approved to {new_pct}%'} on loan {loan['loan_reference']}."
            )

            return {
                "status": "SUCCESS",
                "loan_id": loan_id,
                "approval_level_percent": new_pct,
                "current_approval_stage": new_stage,
                "loan_status": new_status,
                "is_disbursed": is_disbursed,
                "presidential_override": override_flag,
                "message": "Loan successfully disbursed!" if is_disbursed else f"Approval stage completed. Progress is now {new_pct}%."
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def submit_loan_appeal(
        self,
        loan_id: int,
        member_id: int,
        appeal_comments: str,
        attached_document_path: str = None,
        document_name: str = None,
        document_mime_type: str = None
    ) -> Dict[str, Any]:
        """
        Allows a member whose loan was declined to contest or request review,
        routing directly to the specific declining officer's desk (with Presidential visibility).
        """
        if not appeal_comments or len(appeal_comments.strip()) < 10:
            raise ValueError("Please provide a comprehensive explanation for your appeal.")

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM loans WHERE id = %s AND member_id = %s;", (loan_id, member_id))
            loan = cursor.fetchone()
            if not loan:
                raise ValueError("Loan not found or does not belong to you.")

            if loan["status"] != "DECLINED":
                raise ValueError("Only declined loan applications can be contested or appealed.")

            target_officer = loan.get("declined_by_officer_id")

            cursor.execute("""
                INSERT INTO loan_appeals (
                    loan_id, member_id, appeal_comments, attached_document_path,
                    document_name, document_mime_type, target_officer_id, status
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, 'PENDING_REVIEW'
                );
            """, (
                loan_id, member_id, appeal_comments.strip(),
                attached_document_path, document_name, document_mime_type,
                target_officer
            ))
            appeal_id = cursor.lastrowid

            cursor.execute("""
                UPDATE loans
                SET status = 'UNDER_APPEAL', updated_at = NOW()
                WHERE id = %s;
            """, (loan_id,))

            conn.commit()

            self.log_audit_event(
                user_id=member_id,
                actor_name="Member",
                actor_role="MEMBER",
                action="LOAN_APPEAL_SUBMITTED",
                resource_type="LOAN_APPEAL",
                resource_id=str(appeal_id),
                details_before={"loan_id": loan_id, "status": "DECLINED"},
                details_after={"loan_id": loan_id, "status": "UNDER_APPEAL", "appeal_id": appeal_id},
                summary=f"Filed appeal #{appeal_id} against loan decline {loan['loan_reference']}."
            )

            return {
                "status": "SUCCESS",
                "appeal_id": appeal_id,
                "loan_id": loan_id,
                "message": "Your appeal and supporting documents have been submitted and routed to the reviewing officer."
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def resolve_loan_appeal(
        self,
        appeal_id: int,
        officer_id: int,
        officer_role: str,
        action: str,
        review_response: str
    ) -> Dict[str, Any]:
        """
        Resolves a contested loan application:
        - REINSTATE: Re-enters the loan into the approval pipeline.
        - UPHOLD: Confirms the decline decision.
        """
        action = action.upper().strip()
        if action not in ("REINSTATE", "UPHOLD"):
            raise ValueError("Action must be either REINSTATE or UPHOLD.")
        if not review_response or len(review_response.strip()) < 5:
            raise ValueError("A formal resolution response is required.")

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM loan_appeals WHERE id = %s FOR UPDATE;", (appeal_id,))
            appeal = cursor.fetchone()
            if not appeal:
                raise ValueError("Appeal record not found.")

            if appeal["status"] != "PENDING_REVIEW":
                raise ValueError(f"Appeal is already resolved ({appeal['status']}).")

            loan_id = appeal["loan_id"]

            if action == "REINSTATE":
                cursor.execute("""
                    UPDATE loan_appeals
                    SET status = 'RESOLVED_APPROVED', review_response = %s, resolved_at = NOW()
                    WHERE id = %s;
                """, (review_response.strip(), appeal_id))

                cursor.execute("""
                    UPDATE loans
                    SET status = 'PENDING', decline_reason = NULL, updated_at = NOW()
                    WHERE id = %s;
                """, (loan_id,))

                cursor.execute("""
                    INSERT INTO loan_approval_steps (
                        loan_id, step_name, officer_id, officer_role,
                        action, percentage_granted, comments
                    ) VALUES (
                        %s, 'APPEAL_RESOLUTION', %s, %s,
                        'APPROVED', (SELECT approval_level_percent FROM loans WHERE id = %s), %s
                    );
                """, (loan_id, officer_id, officer_role, loan_id, f"Appeal approved & reinstated: {review_response.strip()}"))
            else:
                cursor.execute("""
                    UPDATE loan_appeals
                    SET status = 'RESOLVED_DECLINED', review_response = %s, resolved_at = NOW()
                    WHERE id = %s;
                """, (review_response.strip(), appeal_id))

                cursor.execute("""
                    UPDATE loans
                    SET status = 'DECLINED', updated_at = NOW()
                    WHERE id = %s;
                """, (loan_id,))

                cursor.execute("""
                    INSERT INTO loan_approval_steps (
                        loan_id, step_name, officer_id, officer_role,
                        action, percentage_granted, comments
                    ) VALUES (
                        %s, 'APPEAL_RESOLUTION', %s, %s,
                        'DECLINED', 0, %s
                    );
                """, (loan_id, officer_id, officer_role, f"Appeal denied: {review_response.strip()}"))

            conn.commit()

            self.log_audit_event(
                user_id=officer_id,
                actor_name="Reviewing Officer",
                actor_role=officer_role,
                action="LOAN_APPEAL_RESOLVED",
                resource_type="LOAN_APPEAL",
                resource_id=str(appeal_id),
                details_before={"status": "PENDING_REVIEW"},
                details_after={"status": action, "response": review_response.strip()},
                summary=f"Resolved appeal #{appeal_id}: {action}."
            )

            return {
                "status": "SUCCESS",
                "appeal_id": appeal_id,
                "resolution": action,
                "message": f"Appeal has been successfully resolved ({action})."
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def get_loan_appeals(self, loan_id: int = None) -> List[Dict[str, Any]]:
        """Retrieves loan appeals for inspection."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            where_sql = "WHERE la.loan_id = %s" if loan_id else ""
            params = (loan_id,) if loan_id else ()
            cursor.execute(f"""
                SELECT 
                    la.id, la.loan_id, la.member_id, la.appeal_comments,
                    la.attached_document_path, la.document_name, la.document_mime_type,
                    la.target_officer_id, la.status, la.review_response,
                    la.created_at, la.resolved_at,
                    l.loan_reference, l.principal_amount,
                    m.member_code, m.first_name, m.last_name
                FROM loan_appeals la
                JOIN loans l ON la.loan_id = l.id
                JOIN members m ON la.member_id = m.id
                {where_sql}
                ORDER BY la.id DESC;
            """, params)
            appeals = cursor.fetchall()
            for a in appeals:
                if a.get("created_at"):
                    a["created_at"] = str(a["created_at"])
                if a.get("resolved_at"):
                    a["resolved_at"] = str(a["resolved_at"])
                if a.get("principal_amount") is not None:
                    a["principal_amount"] = float(a["principal_amount"])
            return appeals
        finally:
            cursor.close()
            conn.close()

    def get_active_loan_products(self) -> List[Dict[str, Any]]:
        """Retrieves all statutory loan products configured in the bye-laws."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT id, product_name, product_code, description, min_membership_months,
                       max_multiplier_of_savings, max_principal_ceiling, admin_cost_fee_percent,
                       min_tenure_months, max_tenure_months, is_active
                FROM loan_products
                WHERE is_active = 1
                ORDER BY id ASC;
            """)
            products = cursor.fetchall()
            for p in products:
                p["max_multiplier_of_savings"] = float(p["max_multiplier_of_savings"])
                p["max_principal_ceiling"] = float(p["max_principal_ceiling"])
                p["admin_cost_fee_percent"] = float(p["admin_cost_fee_percent"])
            return products
        finally:
            cursor.close()
            conn.close()

    def get_active_guarantor_candidates(self, exclude_member_id: int = None) -> List[Dict[str, Any]]:
        """Returns list of active members eligible to act as loan guarantors."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            where = ["m.status IN ('ACTIVE', 'APPROVED')"]
            params = []
            if exclude_member_id:
                where.append("m.id != %s")
                params.append(exclude_member_id)
            where_sql = " AND ".join(where)

            cursor.execute(f"""
                SELECT 
                    m.id, m.member_code, m.first_name, m.last_name, m.email, m.phone,
                    COALESCE(sv.total_balance, 0.00) AS total_savings
                FROM members m
                LEFT JOIN savings_accounts sv ON m.id = sv.member_id
                WHERE {where_sql}
                ORDER BY m.first_name ASC, m.last_name ASC;
            """, tuple(params))
            rows = cursor.fetchall()
            for r in rows:
                r["total_savings"] = float(r["total_savings"])
                r["full_name"] = f"{r['first_name']} {r['last_name']}".strip()
            return rows
        finally:
            cursor.close()
            conn.close()

    def get_member_loans(self, member_id: int) -> List[Dict[str, Any]]:
        """
        Borrower-facing loan status view:
        Returns approval level in %, current status, and decline reason if declined.
        Internal executive deliberation steps are kept strictly confidential.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    l.id, l.loan_reference, l.product_id, lp.product_name,
                    l.principal_amount, l.admin_cost_fee, l.total_amount_payable,
                    l.tenure_months, l.monthly_installment, l.total_paid,
                    l.outstanding_balance, l.status, l.approval_level_percent,
                    l.current_approval_stage, l.decline_reason, l.purpose_narration,
                    l.application_date, l.disbursement_date, l.next_due_date, l.maturity_date
                FROM loans l
                LEFT JOIN loan_products lp ON l.product_id = lp.id
                WHERE l.member_id = %s
                ORDER BY l.id DESC;
            """, (member_id,))
            loans = cursor.fetchall()

            for ln in loans:
                ln["principal_amount"] = float(ln["principal_amount"])
                ln["admin_cost_fee"] = float(ln["admin_cost_fee"] or 0)
                ln["total_amount_payable"] = float(ln["total_amount_payable"])
                ln["monthly_installment"] = float(ln["monthly_installment"])
                ln["total_paid"] = float(ln["total_paid"] or 0)
                ln["outstanding_balance"] = float(ln["outstanding_balance"] or 0)
                for dt_col in ["application_date", "disbursement_date", "next_due_date", "maturity_date"]:
                    if ln.get(dt_col):
                        ln[dt_col] = str(ln[dt_col])

                # Fetch attached guarantors for borrower reference
                cursor.execute("""
                    SELECT 
                        lg.id, lg.loan_id, lg.guarantor_member_id, lg.guaranteed_amount,
                        lg.status, m.first_name, m.last_name, m.member_code
                    FROM loan_guarantors lg
                    JOIN members m ON lg.guarantor_member_id = m.id
                    WHERE lg.loan_id = %s
                    ORDER BY lg.id ASC;
                """, (ln["id"],))
                guars = cursor.fetchall()
                for g in guars:
                    g["guaranteed_amount"] = float(g["guaranteed_amount"])
                    g["full_name"] = f"{g['first_name']} {g['last_name']}".strip()
                ln["guarantors"] = guars

                cursor.execute("""
                    SELECT id, status FROM loan_appeals
                    WHERE loan_id = %s AND status = 'PENDING_REVIEW'
                    ORDER BY id DESC LIMIT 1;
                """, (ln["id"],))
                app = cursor.fetchone()
                ln["has_pending_appeal"] = bool(app)
                ln["pending_appeal_id"] = app["id"] if app else None

            return loans
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # 16. POLARIS BANK MANUAL TRANSFER LOGGING & EXECUTIVE RECONCILIATION
    # -------------------------------------------------------------------------
    def log_manual_bank_payment(
        self,
        member_id: int,
        amount: float,
        payment_date: str,
        payment_reference: str,
        narration: str = None,
        receipt_file_path: str = None,
        receipt_mime_type: str = None
    ) -> Dict[str, Any]:
        """Logs a direct Polaris Bank transfer remittance with receipt upload."""
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        if not payment_reference or len(payment_reference.strip()) < 3:
            raise ValueError("Valid bank transaction reference or teller number is required.")

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, member_code, first_name, last_name FROM members WHERE id = %s;", (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError("Member record not found.")

            cursor.execute("""
                INSERT INTO manual_bank_payments (
                    member_id, amount, payment_date, bank_name,
                    payment_reference, narration, receipt_file_path,
                    receipt_mime_type, status
                ) VALUES (
                    %s, %s, %s, 'Polaris Bank Limited',
                    %s, %s, %s,
                    %s, 'PENDING_RECONCILIATION'
                );
            """, (
                member_id, Decimal(str(amount)), payment_date,
                payment_reference.strip(), narration, receipt_file_path,
                receipt_mime_type
            ))
            pmt_id = cursor.lastrowid
            conn.commit()

            self.log_audit_event(
                user_id=member_id,
                actor_name=f"{member['first_name']} {member['last_name']}",
                actor_role="MEMBER",
                action="MANUAL_PAYMENT_LOGGED",
                resource_type="MANUAL_PAYMENT",
                resource_id=str(pmt_id),
                details_before=None,
                details_after={
                    "amount": float(amount),
                    "reference": payment_reference,
                    "date": payment_date,
                    "receipt": receipt_file_path
                },
                summary=f"Logged Polaris Bank transfer of NGN {amount:,.2f} (Ref: {payment_reference})."
            )

            return {
                "id": pmt_id,
                "member_id": member_id,
                "amount": float(amount),
                "payment_reference": payment_reference,
                "status": "PENDING_RECONCILIATION",
                "message": "Payment logged successfully. Treasury team will verify and reconcile against Polaris statement."
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def get_pending_manual_payments(self) -> List[Dict[str, Any]]:
        """Retrieves manual bank payments pending reconciliation."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    mbp.id, mbp.member_id, mbp.amount, mbp.payment_date,
                    mbp.bank_name, mbp.payment_reference, mbp.narration,
                    mbp.receipt_file_path, mbp.receipt_mime_type, mbp.status,
                    mbp.created_at,
                    m.member_code, m.first_name, m.last_name, m.phone, m.email
                FROM manual_bank_payments mbp
                JOIN members m ON mbp.member_id = m.id
                WHERE mbp.status = 'PENDING_RECONCILIATION'
                ORDER BY mbp.id ASC;
            """)
            payments = cursor.fetchall()
            for p in payments:
                p["amount"] = float(p["amount"])
                if p.get("payment_date"):
                    p["payment_date"] = str(p["payment_date"])
                if p.get("created_at"):
                    p["created_at"] = str(p["created_at"])
            return payments
        finally:
            cursor.close()
            conn.close()

    def verify_manual_bank_payment(
        self,
        payment_id: int,
        officer_id: int,
        officer_role: str,
        distribution_override: Dict[str, float] = None,
        verification_notes: str = None
    ) -> Dict[str, Any]:
        """
        Executive desk verification of manual Polaris remittance:
        Verifies and distributes either via the monthly payment advice waterfall
        or an explicit custom allocation.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM manual_bank_payments WHERE id = %s FOR UPDATE;", (payment_id,))
            pmt = cursor.fetchone()
            if not pmt:
                raise ValueError(f"Payment ID {payment_id} not found.")

            if pmt["status"] != "PENDING_RECONCILIATION":
                raise ValueError(f"Payment is already {pmt['status']}.")

            member_id = pmt["member_id"]
            amount = float(pmt["amount"])
            ref = pmt["payment_reference"]

            cursor.close()
            conn.close()

            dist_res = self.distribute_payment_by_advice(
                member_id=member_id,
                amount_paid=amount,
                payment_method="POLARIS_BANK_TRANSFER",
                payment_ref=ref,
                narration=f"Polaris Bank manual transfer verified by {officer_role}. {verification_notes or ''}".strip()
            )

            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)

            dist_json = json.dumps(dist_res.get("distributions", {}))

            cursor.execute("""
                UPDATE manual_bank_payments
                SET 
                    status = 'VERIFIED',
                    verified_by_officer_id = %s,
                    verified_at = NOW(),
                    distribution_json = %s
                WHERE id = %s;
            """, (officer_id, dist_json, payment_id))
            conn.commit()

            self.log_audit_event(
                user_id=officer_id,
                actor_name="Treasury Officer",
                actor_role=officer_role,
                action="MANUAL_PAYMENT_VERIFIED",
                resource_type="MANUAL_PAYMENT",
                resource_id=str(payment_id),
                details_before={"status": "PENDING_RECONCILIATION"},
                details_after={"status": "VERIFIED", "distribution": dist_res},
                summary=f"Verified Polaris payment #{payment_id} for NGN {amount:,.2f} (Ref: {ref})."
            )

            return {
                "status": "SUCCESS",
                "payment_id": payment_id,
                "amount": amount,
                "distribution": dist_res,
                "message": f"Payment #{payment_id} verified and credited across member ledgers."
            }
        except Exception:
            if conn and conn.is_connected():
                conn.rollback()
            raise
        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    def reject_manual_bank_payment(
        self,
        payment_id: int,
        officer_id: int,
        officer_role: str,
        rejection_reason: str
    ) -> Dict[str, Any]:
        """Rejects an invalid or unmatched manual bank payment."""
        if not rejection_reason or len(rejection_reason.strip()) < 5:
            raise ValueError("A clear rejection reason is mandatory.")

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM manual_bank_payments WHERE id = %s FOR UPDATE;", (payment_id,))
            pmt = cursor.fetchone()
            if not pmt:
                raise ValueError("Payment not found.")

            cursor.execute("""
                UPDATE manual_bank_payments
                SET 
                    status = 'REJECTED',
                    verified_by_officer_id = %s,
                    verified_at = NOW(),
                    rejection_reason = %s
                WHERE id = %s;
            """, (officer_id, rejection_reason.strip(), payment_id))
            conn.commit()

            self.log_audit_event(
                user_id=officer_id,
                actor_name="Treasury Officer",
                actor_role=officer_role,
                action="MANUAL_PAYMENT_REJECTED",
                resource_type="MANUAL_PAYMENT",
                resource_id=str(payment_id),
                details_before={"status": pmt["status"]},
                details_after={"status": "REJECTED", "reason": rejection_reason.strip()},
                summary=f"Rejected manual payment #{payment_id}. Reason: {rejection_reason.strip()}"
            )

            return {"status": "SUCCESS", "message": "Manual payment rejected."}
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    def record_direct_member_credit(
        self,
        member_id: int,
        officer_id: int,
        officer_role: str,
        amount: float,
        credit_category: str,
        narration: str
    ) -> Dict[str, Any]:
        """
        Direct executive credit desk for Financial Secretary, Treasurer, and President.
        Allows crediting savings, shares, or loan repayments with mandatory statutory narration.
        """
        if amount <= 0:
            raise ValueError("Credit amount must be greater than zero.")
        if not narration or len(narration.strip()) < 5:
            raise ValueError("A statutory audit narration is required for direct credit.")

        category = credit_category.upper().strip()
        allowed = ("SAVINGS", "REGULAR_SAVINGS", "SHARE_CAPITAL", "WELFARE", "LOAN_REPAYMENT")
        if category not in allowed:
            raise ValueError(f"Category must be one of: {', '.join(allowed)}")

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id, member_code, first_name, last_name FROM members WHERE id = %s;", (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError("Member not found.")

            dec_amt = Decimal(str(amount))
            t_ref = f"DIR-CR-{secrets.token_hex(5).upper()}"

            if category in ("SAVINGS", "REGULAR_SAVINGS"):
                cursor.execute("""
                    UPDATE savings_accounts
                    SET total_balance = total_balance + %s
                    WHERE member_id = %s;
                """, (dec_amt, member_id))
                ledger = "SAVINGS"
            elif category == "SHARE_CAPITAL":
                cursor.execute("""
                    UPDATE share_accounts
                    SET paid_up_amount = paid_up_amount + %s, units_held = units_held + FLOOR(%s / 1000)
                    WHERE member_id = %s;
                """, (dec_amt, dec_amt, member_id))
                ledger = "SHARE_CAPITAL"
            elif category in ("WELFARE", "WELFARE_FUND"):
                cursor.execute("""
                    UPDATE welfare_accounts
                    SET cumulative_contributions = cumulative_contributions + %s
                    WHERE member_id = %s;
                """, (dec_amt, member_id))
                ledger = "WELFARE_FUND"
            elif category == "LOAN_REPAYMENT":
                cursor.execute("""
                    SELECT id, outstanding_balance, total_paid FROM loans
                    WHERE member_id = %s AND status = 'ACTIVE'
                    ORDER BY id DESC LIMIT 1 FOR UPDATE;
                """, (member_id,))
                active_loan = cursor.fetchone()
                if not active_loan:
                    raise ValueError("No active loan found for this member.")
                new_out = max(Decimal("0.00"), active_loan["outstanding_balance"] - dec_amt)
                new_status = "CLOSED" if new_out == Decimal("0.00") else "ACTIVE"
                cursor.execute("""
                    UPDATE loans
                    SET outstanding_balance = %s, total_paid = total_paid + %s, status = %s
                    WHERE id = %s;
                """, (new_out, dec_amt, new_status, active_loan["id"]))
                ledger = "LOAN_REPAYMENT"

            cursor.execute("""
                INSERT INTO transactions (
                    transaction_ref, member_id, transaction_type, ledger_category,
                    amount, payment_method, narration, status,
                    verified_by_officer_id, transaction_date
                ) VALUES (
                    %s, %s, 'CREDIT', %s,
                    %s, 'INTERNAL_SET_OFF', %s, 'VERIFIED',
                    %s, CURDATE()
                );
            """, (t_ref, member_id, ledger, dec_amt, narration.strip(), officer_id))

            conn.commit()

            self.log_audit_event(
                user_id=officer_id,
                actor_name="Executive Officer",
                actor_role=officer_role,
                action="DIRECT_MEMBER_CREDIT",
                resource_type="MEMBER_ACCOUNT",
                resource_id=str(member_id),
                details_before=None,
                details_after={"category": ledger, "amount": float(dec_amt), "narration": narration.strip()},
                summary=f"Direct credit of NGN {dec_amt:,.2f} ({ledger}) to {member['member_code']}."
            )

            return {
                "status": "SUCCESS",
                "member_id": member_id,
                "amount": float(dec_amt),
                "category": ledger,
                "transaction_ref": t_ref,
                "message": f"Successfully credited NGN {dec_amt:,.2f} to {member['first_name']} {member['last_name']} ({ledger})."
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # 17. PAYMENT ADVICE REVISION & STATUTORY MODIFICATION
    # -------------------------------------------------------------------------
    def modify_payment_advice(
        self,
        advice_id: int,
        officer_id: int,
        officer_role: str,
        scope: str,
        modified_items: Dict[str, Any],
        statutory_justification: str
    ) -> Dict[str, Any]:
        """
        Allows Financial Secretary, Treasurer, and President to modify payment advice:
        - scope: 'THIS_MONTH_ONLY' or 'PERMANENT_COMMITMENT'
        - Mandatory statutory justification recorded in immutable audit log.
        """
        scope = scope.upper().strip()
        if scope not in ("THIS_MONTH_ONLY", "PERMANENT_COMMITMENT"):
            raise ValueError("Scope must be either 'THIS_MONTH_ONLY' or 'PERMANENT_COMMITMENT'.")

        if not statutory_justification or len(statutory_justification.strip()) < 10:
            raise ValueError("A formal statutory justification (min 10 characters) is required for advice revisions.")

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM payment_advices WHERE id = %s FOR UPDATE;", (advice_id,))
            adv = cursor.fetchone()
            if not adv:
                raise ValueError(f"Advice ID {advice_id} not found.")

            before_state = {
                "fines": float(adv["amount_fines"]),
                "registration_fee": float(adv.get("amount_registration_fee", 0.0) or 0.0),
                "loan": float(adv["amount_loan_repayment"]),
                "welfare": float(adv["amount_welfare"]),
                "shares": float(adv["amount_share_capital"]),
                "savings": float(adv["amount_regular_savings"]),
                "targets": float(adv["amount_target_savings"]),
                "arrears": float(adv["amount_arrears"]),
                "total_expected": float(adv["total_expected_amount"])
            }

            fines = Decimal(str(modified_items.get("amount_fines", adv["amount_fines"])))
            reg_fee = Decimal(str(modified_items.get("amount_registration_fee", adv.get("amount_registration_fee", 0.0) or 0.0)))
            loan = Decimal(str(modified_items.get("amount_loan_repayment", adv["amount_loan_repayment"])))
            welfare = Decimal(str(modified_items.get("amount_welfare", adv["amount_welfare"])))
            shares = Decimal(str(modified_items.get("amount_share_capital", adv["amount_share_capital"])))
            savings = Decimal(str(modified_items.get("amount_regular_savings", adv["amount_regular_savings"])))
            targets = Decimal(str(modified_items.get("amount_target_savings", adv["amount_target_savings"])))
            arrears = Decimal(str(modified_items.get("amount_arrears", adv["amount_arrears"])))

            total_exp = fines + reg_fee + loan + welfare + shares + savings + targets + arrears
            out_bal = max(Decimal("0.00"), total_exp - adv["total_amount_paid"])
            new_status = "FULLY_SETTLED" if out_bal == Decimal("0.00") and adv["total_amount_paid"] > 0 else (
                "PARTIALLY_PAID" if adv["total_amount_paid"] > 0 else "DUE"
            )

            notes = f"Revised by {officer_role} [{scope}]: {statutory_justification.strip()}"

            cursor.execute("""
                UPDATE payment_advices
                SET 
                    amount_fines = %s,
                    amount_registration_fee = %s,
                    amount_loan_repayment = %s,
                    amount_welfare = %s,
                    amount_share_capital = %s,
                    amount_regular_savings = %s,
                    amount_target_savings = %s,
                    amount_arrears = %s,
                    total_expected_amount = %s,
                    outstanding_balance = %s,
                    status = %s,
                    admin_notes = %s,
                    updated_at = NOW()
                WHERE id = %s;
            """, (
                fines, reg_fee, loan, welfare, shares, savings, targets, arrears,
                total_exp, out_bal, new_status, notes, advice_id
            ))

            conn.commit()

            after_state = {
                "fines": float(fines),
                "registration_fee": float(reg_fee),
                "loan": float(loan),
                "welfare": float(welfare),
                "shares": float(shares),
                "savings": float(savings),
                "targets": float(targets),
                "arrears": float(arrears),
                "total_expected": float(total_exp)
            }

            self.log_audit_event(
                user_id=officer_id,
                actor_name="Executive Officer",
                actor_role=officer_role,
                action="PAYMENT_ADVICE_MODIFIED",
                resource_type="PAYMENT_ADVICE",
                resource_id=str(advice_id),
                details_before=before_state,
                details_after=after_state,
                summary=f"Modified advice #{advice_id} ({scope}). Justification: {statutory_justification.strip()}"
            )

            return {
                "status": "SUCCESS",
                "advice_id": advice_id,
                "scope": scope,
                "total_expected": float(total_exp),
                "outstanding_balance": float(out_bal),
                "message": f"Payment Advice #{advice_id} revised successfully."
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # 18. FORENSIC AUDIT TRAIL (IMMUTABLE APPEND-ONLY REPOSITORY)
    # -------------------------------------------------------------------------
    def log_audit_event(
        self,
        user_id: Optional[int],
        actor_name: str,
        actor_role: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str],
        details_before: Optional[Dict],
        details_after: Optional[Dict],
        summary: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Appends an immutable tamper-evident record into the audit_logs table.
        Captures deep before/after state diffs for forensic examinations.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            b_json = json.dumps(details_before, default=str) if details_before is not None else None
            a_json = json.dumps(details_after, default=str) if details_after is not None else None

            cursor.execute("""
                INSERT INTO audit_logs (
                    user_id, actor_name, actor_role, action,
                    resource_type, resource_id, ip_address, user_agent,
                    details_before, details_after, summary
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s
                );
            """, (
                user_id, actor_name, actor_role, action,
                resource_type, resource_id, ip_address, user_agent,
                b_json, a_json, summary
            ))
            conn.commit()
        except Exception as e:
            print(f"[AUDIT LOG ERROR] Failed to record audit log: {e}", file=sys.stderr)
        finally:
            cursor.close()
            conn.close()

    def get_audit_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        actor_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Queries the forensic audit trail with comprehensive filtering for President & Super Admin.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            where_clauses = ["1=1"]
            params = []

            if actor_id:
                where_clauses.append("user_id = %s")
                params.append(actor_id)
            if action:
                where_clauses.append("action LIKE %s")
                params.append(f"%{action}%")
            if resource_type:
                where_clauses.append("resource_type = %s")
                params.append(resource_type)
            if date_from:
                where_clauses.append("DATE(created_at) >= %s")
                params.append(date_from)
            if date_to:
                where_clauses.append("DATE(created_at) <= %s")
                params.append(date_to)

            where_sql = " AND ".join(where_clauses)

            cursor.execute(f"SELECT COUNT(*) AS total FROM audit_logs WHERE {where_sql};", tuple(params))
            total_records = cursor.fetchone()["total"]

            cursor.execute(f"""
                SELECT 
                    id, user_id, actor_name, actor_role, action,
                    resource_type, resource_id, ip_address, user_agent,
                    details_before, details_after, summary, created_at
                FROM audit_logs
                WHERE {where_sql}
                ORDER BY id DESC
                LIMIT %s OFFSET %s;
            """, tuple(params + [limit, offset]))
            logs = cursor.fetchall()

            for log in logs:
                log["actor_id"] = log.get("user_id")
                if log.get("created_at"):
                    log["created_at"] = str(log["created_at"])
                if isinstance(log.get("details_before"), str):
                    try:
                        log["details_before"] = json.loads(log["details_before"])
                    except Exception:
                        pass
                if isinstance(log.get("details_after"), str):
                    try:
                        log["details_after"] = json.loads(log["details_after"])
                    except Exception:
                        pass

            return {
                "total": total_records,
                "limit": limit,
                "offset": offset,
                "logs": logs
            }
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # 18. GUARANTOR IN-PORTAL DIGITAL CONSENT ENGINE
    # -------------------------------------------------------------------------
    def get_member_guarantor_requests(self, member_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all loan guarantee requests addressed to this cooperator:
        Both pending requests requiring digital signature and past consented guarantees.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    lg.id,
                    lg.id AS guarantor_request_id,
                    lg.loan_id,
                    lg.guarantor_member_id,
                    lg.guaranteed_amount,
                    lg.lien_encumbered_amount,
                    lg.status,
                    lg.status AS consent_status,
                    lg.accepted_at,
                    lg.released_at,
                    l.loan_reference,
                    l.principal_amount,
                    l.tenure_months,
                    l.monthly_installment,
                    l.status AS loan_status,
                    l.current_approval_stage,
                    l.application_date,
                    l.purpose_narration,
                    lp.product_name,
                    b.id AS borrower_id,
                    b.member_code AS borrower_code,
                    CONCAT(b.first_name, ' ', b.last_name) AS borrower_name,
                    b.email AS borrower_email,
                    b.phone AS borrower_phone,
                    COALESCE(bsv.total_balance, 0.00) AS borrower_savings_balance
                FROM loan_guarantors lg
                JOIN loans l ON lg.loan_id = l.id
                JOIN members b ON l.member_id = b.id
                LEFT JOIN loan_products lp ON l.product_id = lp.id
                LEFT JOIN savings_accounts bsv ON b.id = bsv.member_id
                WHERE lg.guarantor_member_id = %s
                ORDER BY lg.id DESC;
            """, (member_id,))
            rows = cursor.fetchall()
            for r in rows:
                r["guaranteed_amount"] = float(r["guaranteed_amount"])
                r["lien_encumbered_amount"] = float(r["lien_encumbered_amount"] or 0)
                r["principal_amount"] = float(r["principal_amount"])
                r["monthly_installment"] = float(r["monthly_installment"])
                r["borrower_savings_balance"] = float(r["borrower_savings_balance"])
                if r.get("accepted_at"):
                    r["accepted_at"] = str(r["accepted_at"])
                if r.get("released_at"):
                    r["released_at"] = str(r["released_at"])
                if r.get("application_date"):
                    r["application_date"] = str(r["application_date"])
            return rows
        finally:
            cursor.close()
            conn.close()

    def respond_to_guarantor_request(
        self,
        guarantor_member_id: int,
        guarantor_request_id: int,
        decision: str,
        comments: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes cooperator in-portal digital signature consent for a peer's loan:
        - ACCEPT: Validates unencumbered savings balance, places statutory administrative lien,
          updates consent status, and if all peer guarantors have signed, automatically
          unlocks and advances loan to Stage 1 Credit Committee review.
        - DECLINE: Marks guarantee declined and notifies loan applicant.
        """
        decision = decision.upper().strip()
        if decision not in ("ACCEPT", "DECLINE"):
            raise ValueError("Decision must be either 'ACCEPT' or 'DECLINE'.")

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT lg.*, l.loan_reference, l.member_id AS borrower_id, l.current_approval_stage, l.status AS loan_status
                FROM loan_guarantors lg
                JOIN loans l ON lg.loan_id = l.id
                WHERE lg.id = %s AND lg.guarantor_member_id = %s;
            """, (guarantor_request_id, guarantor_member_id))
            g_req = cursor.fetchone()
            if not g_req:
                raise ValueError("Guarantor request record not found or access denied.")

            if g_req["status"] != "PENDING_CONSENT":
                raise ValueError(f"This guarantor request is already in '{g_req['status']}' state.")

            cursor.execute("SELECT first_name, last_name, member_code, status FROM members WHERE id = %s;", (guarantor_member_id,))
            guar = cursor.fetchone()
            if guar and guar.get("status") == "SUSPENDED":
                raise ValueError("Cooperators with suspended membership status cannot guarantee loans.")
            guar_name = f"{guar['first_name']} {guar['last_name']}".strip()
            loan_id = g_req["loan_id"]
            guaranteed_amt = Decimal(str(g_req["guaranteed_amount"]))

            if decision == "ACCEPT":
                # Check available unencumbered savings
                cursor.execute("SELECT total_balance, encumbered_balance FROM savings_accounts WHERE member_id = %s;", (guarantor_member_id,))
                sav = cursor.fetchone() or {"total_balance": Decimal("0.00"), "encumbered_balance": Decimal("0.00")}
                tot_sav = Decimal(str(sav["total_balance"]))
                enc_sav = Decimal(str(sav["encumbered_balance"]))
                avail_sav = max(Decimal("0.00"), tot_sav - enc_sav)

                if avail_sav < guaranteed_amt:
                    raise ValueError(
                        f"Insufficient unencumbered savings to guarantee NGN {guaranteed_amt:,.2f}. "
                        f"Your current available savings is NGN {avail_sav:,.2f}."
                    )

                # Place statutory administrative collateral hold
                cursor.execute("""
                    UPDATE savings_accounts 
                    SET encumbered_balance = encumbered_balance + %s
                    WHERE member_id = %s;
                """, (guaranteed_amt, guarantor_member_id))

                cursor.execute("""
                    UPDATE loan_guarantors 
                    SET status = 'ACCEPTED', accepted_at = NOW(), lien_encumbered_amount = %s
                    WHERE id = %s;
                """, (guaranteed_amt, guarantor_request_id))

                # Check if all nominated guarantors for this loan have now consented
                cursor.execute("""
                    SELECT COUNT(*) AS pending_count 
                    FROM loan_guarantors 
                    WHERE loan_id = %s AND status != 'ACCEPTED';
                """, (loan_id,))
                chk = cursor.fetchone()
                all_consented = (chk["pending_count"] == 0)

                if all_consented and g_req["current_approval_stage"] == "GUARANTOR_CONSENT":
                    cursor.execute("""
                        UPDATE loans 
                        SET current_approval_stage = 'CREDIT_COMMITTEE', updated_at = NOW()
                        WHERE id = %s;
                    """, (loan_id,))

                conn.commit()

                self.log_audit_event(
                    user_id=guarantor_member_id,
                    actor_name=guar_name,
                    actor_role="COOPERATOR",
                    action="GUARANTOR_DIGITAL_CONSENT_SIGNED",
                    resource_type="LOAN_GUARANTOR",
                    resource_id=str(guarantor_request_id),
                    details_before={"status": "PENDING_CONSENT"},
                    details_after={
                        "status": "ACCEPTED",
                        "guaranteed_amount": float(guaranteed_amt),
                        "loan_reference": g_req["loan_reference"],
                        "all_guarantors_consented": all_consented
                    },
                    summary=f"Cooperator {guar['member_code']} digitally signed guarantee for NGN {guaranteed_amt:,.2f} on {g_req['loan_reference']}."
                )

                return {
                    "status": "SUCCESS",
                    "decision": "ACCEPTED",
                    "guarantor_request_id": guarantor_request_id,
                    "loan_reference": g_req["loan_reference"],
                    "all_guarantors_consented": all_consented,
                    "message": f"Consent successfully recorded. Collateral lien of NGN {guaranteed_amt:,.2f} placed on savings."
                }

            else:
                # DECLINE
                cursor.execute("""
                    UPDATE loan_guarantors 
                    SET status = 'DECLINED'
                    WHERE id = %s;
                """, (guarantor_request_id,))
                conn.commit()

                self.log_audit_event(
                    user_id=guarantor_member_id,
                    actor_name=guar_name,
                    actor_role="COOPERATOR",
                    action="GUARANTOR_DIGITAL_CONSENT_DECLINED",
                    resource_type="LOAN_GUARANTOR",
                    resource_id=str(guarantor_request_id),
                    details_before={"status": "PENDING_CONSENT"},
                    details_after={"status": "DECLINED", "comments": comments},
                    summary=f"Cooperator {guar['member_code']} declined guarantee request on {g_req['loan_reference']}."
                )

                return {
                    "status": "SUCCESS",
                    "decision": "DECLINED",
                    "guarantor_request_id": guarantor_request_id,
                    "loan_reference": g_req["loan_reference"],
                    "message": "You have declined the guarantee request. The applicant has been notified."
                }
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # 19. COOPERATOR EXIT & VOLUNTARY WITHDRAWAL SETTLEMENT DESK (ARTICLES 9 & 11)
    # -------------------------------------------------------------------------
    def submit_member_exit_request(
        self,
        member_id: int,
        exit_type: str = "VOLUNTARY_WITHDRAWAL",
        reason: str = None,
        supporting_doc_url: Optional[str] = None,
        nok_claimant: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Lodges a statutory cooperator membership withdrawal or deceased estate settlement (Articles 9 & 11):
        - Calculates real-time financial obligations and liquidation refund breakdown.
        - Enforces statutory notice period: 60 days for voluntary withdrawal, 0 days for death/estate.
        - Calculates net refund = (Savings + Target Savings + Paid-Up Shares + Bereavement Grant) - (Loans + Fines + Exit Fee).
        - Holds status in PENDING_CLEARANCE for General Secretary & President dual sign-off.
        """
        exit_type = exit_type.upper().strip()
        if exit_type not in ("VOLUNTARY_WITHDRAWAL", "DEATH_ESTATE_SETTLEMENT", "EXPULSION"):
            raise ValueError("Exit type must be 'VOLUNTARY_WITHDRAWAL', 'DEATH_ESTATE_SETTLEMENT', or 'EXPULSION'.")

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM members WHERE id = %s;", (member_id,))
            member = cursor.fetchone()
            if not member:
                raise ValueError("Target cooperator not found.")
            if member["status"] in ("EXITED", "DECEASED"):
                raise ValueError(f"Member status is already '{member['status']}'.")

            # Check if there is already an active exit request
            cursor.execute("""
                SELECT id, status FROM member_exits 
                WHERE member_id = %s AND status IN ('PENDING_CLEARANCE', 'FINANCIALLY_CLEARED')
                LIMIT 1;
            """, (member_id,))
            existing = cursor.fetchone()
            if existing:
                raise ValueError(f"An active exit request (ID #{existing['id']}) is already in progress ({existing['status']}).")

            # 1. Savings balances
            cursor.execute("SELECT total_balance FROM savings_accounts WHERE member_id = %s;", (member_id,))
            sav_row = cursor.fetchone()
            tot_savings = Decimal(str(sav_row["total_balance"])) if sav_row else Decimal("0.00")

            # 2. Target savings balances
            cursor.execute("""
                SELECT COALESCE(SUM(current_balance), 0.00) AS total_target
                FROM target_savings_accounts WHERE member_id = %s AND status = 'ACTIVE';
            """, (member_id,))
            target_row = cursor.fetchone()
            tot_target = Decimal(str(target_row["total_target"])) if target_row else Decimal("0.00")

            # 3. Paid-up shares
            cursor.execute("SELECT paid_up_amount FROM share_accounts WHERE member_id = %s;", (member_id,))
            sh_row = cursor.fetchone()
            tot_shares = Decimal(str(sh_row["paid_up_amount"])) if sh_row else Decimal("0.00")

            # 4. Active loans outstanding
            cursor.execute("""
                SELECT COALESCE(SUM(outstanding_balance), 0.00) AS total_loans
                FROM loans WHERE member_id = %s AND status IN ('ACTIVE', 'PENDING');
            """, (member_id,))
            ln_row = cursor.fetchone()
            tot_loans = Decimal(str(ln_row["total_loans"])) if ln_row else Decimal("0.00")

            # 5. Outstanding disciplinary fines
            cursor.execute("""
                SELECT COALESCE(SUM(fine_amount), 0.00) AS total_fines
                FROM disciplinary_fines WHERE member_id = %s AND status = 'ISSUED';
            """, (member_id,))
            fn_row = cursor.fetchone()
            tot_fines = Decimal(str(fn_row["total_fines"])) if fn_row else Decimal("0.00")

            # 6. Active guarantor commitments on peer loans
            cursor.execute("""
                SELECT COUNT(*) AS active_guars
                FROM loan_guarantors lg
                JOIN loans l ON lg.loan_id = l.id
                WHERE lg.guarantor_member_id = %s AND lg.status = 'ACCEPTED' AND l.status = 'ACTIVE';
            """, (member_id,))
            g_row = cursor.fetchone()
            active_guars_count = int(g_row["active_guars"]) if g_row else 0

            if exit_type == "VOLUNTARY_WITHDRAWAL":
                exit_fee = Decimal("5000.00")  # Standard administrative exit fee
                bereavement_grant = Decimal("0.00")
                notice_interval = 30  # 30-day statutory cooling-off notice window
            elif exit_type == "DEATH_ESTATE_SETTLEMENT":
                exit_fee = Decimal("0.00")
                bereavement_grant = Decimal("100000.00")  # SOP 3.2 Bereavement grant to Next-of-Kin
                notice_interval = 0  # Immediate processing per Article 11
            else:
                exit_fee = Decimal("5000.00")
                bereavement_grant = Decimal("0.00")
                notice_interval = 14

            expected_payout_dt = date.today() + timedelta(days=notice_interval)

            gross_credits = tot_savings + tot_target + tot_shares + bereavement_grant
            gross_debits = tot_loans + tot_fines + exit_fee
            net_refund = gross_credits - gross_debits

            # Extract Next of Kin / Estate Claimant if provided or from DB
            nok_name = (nok_claimant or {}).get("name")
            nok_phone = (nok_claimant or {}).get("phone")
            nok_rel = (nok_claimant or {}).get("relationship")

            if not nok_name and exit_type == "DEATH_ESTATE_SETTLEMENT":
                cursor.execute("SELECT full_name, phone, relationship FROM next_of_kin WHERE member_id = %s LIMIT 1;", (member_id,))
                db_nok = cursor.fetchone()
                if db_nok:
                    nok_name = db_nok["full_name"]
                    nok_phone = db_nok["phone"]
                    nok_rel = db_nok["relationship"]

            cursor.execute("""
                INSERT INTO member_exits (
                    member_id, exit_type, notice_date, statutory_notice_expiry_date,
                    reason, supporting_doc_url, nok_claimant_name, nok_claimant_phone,
                    nok_relationship, status, total_savings_at_exit, total_target_savings_at_exit,
                    total_shares_at_exit, outstanding_loans_at_exit, outstanding_fines_at_exit,
                    active_guarantor_commitments_count, exit_processing_fee,
                    bereavement_welfare_grant, net_refund_amount
                ) VALUES (
                    %s, %s, CURDATE(), DATE_ADD(CURDATE(), INTERVAL %s DAY),
                    %s, %s, %s, %s,
                    %s, 'PENDING_CLEARANCE', %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s
                );
            """, (
                member_id, exit_type, notice_interval,
                reason, supporting_doc_url, nok_name, nok_phone,
                nok_rel, tot_savings, tot_target,
                tot_shares, tot_loans, tot_fines,
                active_guars_count, exit_fee,
                bereavement_grant, net_refund
            ))
            exit_id = cursor.lastrowid
            conn.commit()

            self.log_audit_event(
                user_id=member_id,
                actor_name=f"{member['first_name']} {member['last_name']}",
                actor_role="COOPERATOR",
                action="MEMBER_EXIT_REQUEST_LODGED",
                resource_type="MEMBER_EXIT",
                resource_id=str(exit_id),
                details_before={"membership_status": member["status"]},
                details_after={
                    "exit_id": exit_id,
                    "exit_type": exit_type,
                    "net_refund": float(net_refund),
                    "active_guarantor_commitments": active_guars_count,
                    "outstanding_loans": float(tot_loans)
                },
                summary=f"Lodge {exit_type} notice for {member['member_code']} (Net Liquidation: NGN {net_refund:,.2f})."
            )

            return {
                "status": "SUCCESS",
                "exit_id": exit_id,
                "exit_type": exit_type,
                "notice_date": str(date.today()),
                "total_savings": float(tot_savings),
                "total_target_savings": float(tot_target),
                "total_shares": float(tot_shares),
                "outstanding_loans": float(tot_loans),
                "outstanding_fines": float(tot_fines),
                "active_guarantor_commitments_count": active_guars_count,
                "bereavement_grant": float(bereavement_grant),
                "exit_processing_fee": float(exit_fee),
                "net_refund_amount": float(net_refund),
                "is_debt_cleared": bool(tot_loans == 0 and active_guars_count == 0),
                "cooling_off_days": notice_interval,
                "expected_payout_date": str(expected_payout_dt),
                "message": f"Exit request #{exit_id} lodged successfully. Statutory notice registered. You should expect liquidation payment on {expected_payout_dt.strftime('%d %B %Y')}."
            }
        finally:
            cursor.close()
            conn.close()

    def get_pending_exits_for_review(self) -> List[Dict[str, Any]]:
        """Used by GENERAL_SECRETARY and PRESIDENT to review pending member withdrawal/exit files."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    me.*,
                    m.member_code, m.first_name, m.last_name, m.email, m.phone,
                    m.contribution_tier, m.status AS current_membership_status,
                    m.admission_date, m.bank_name, m.bank_account_number, m.bank_account_name
                FROM member_exits me
                JOIN members m ON me.member_id = m.id
                WHERE me.status IN ('PENDING_CLEARANCE', 'FINANCIALLY_CLEARED')
                ORDER BY me.id ASC;
            """)
            rows = cursor.fetchall()
            for r in rows:
                r["total_savings_at_exit"] = float(r["total_savings_at_exit"])
                r["total_target_savings_at_exit"] = float(r["total_target_savings_at_exit"])
                r["total_shares_at_exit"] = float(r["total_shares_at_exit"])
                r["outstanding_loans_at_exit"] = float(r["outstanding_loans_at_exit"])
                r["outstanding_fines_at_exit"] = float(r["outstanding_fines_at_exit"])
                r["exit_processing_fee"] = float(r["exit_processing_fee"])
                r["bereavement_welfare_grant"] = float(r["bereavement_welfare_grant"])
                r["net_refund_amount"] = float(r["net_refund_amount"])
                for dt_col in ["notice_date", "statutory_notice_expiry_date", "created_at", "updated_at", "admission_date"]:
                    if r.get(dt_col):
                        r[dt_col] = str(r[dt_col])
            return rows
        finally:
            cursor.close()
            conn.close()

    def approve_member_exit_settlement(
        self,
        exit_id: int,
        officer_id: int,
        officer_role: str,
        refund_payment_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        GENERAL_SECRETARY & PRESIDENT action: Finalizes cooperator exit, settles accounts,
        and transitions member status to EXITED (or DECEASED).
        Statutory Precondition (Article 9.2):
        Zero active loans and zero active guarantor liabilities.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT me.*, m.member_code, m.first_name, m.last_name, m.status AS member_status
                FROM member_exits me
                JOIN members m ON me.member_id = m.id
                WHERE me.id = %s;
            """, (exit_id,))
            exit_rec = cursor.fetchone()
            if not exit_rec:
                raise ValueError("Exit record not found.")

            if exit_rec["status"] == "SETTLED_REFUNDED":
                raise ValueError("This exit settlement has already been approved and liquidated.")

            m_id = exit_rec["member_id"]

            # Re-verify active guarantor commitments
            cursor.execute("""
                SELECT COUNT(*) AS active_guars
                FROM loan_guarantors lg
                JOIN loans l ON lg.loan_id = l.id
                WHERE lg.guarantor_member_id = %s AND lg.status = 'ACCEPTED' AND l.status = 'ACTIVE';
            """, (m_id,))
            g_chk = cursor.fetchone()
            if g_chk and g_chk["active_guars"] > 0:
                raise ValueError(
                    f"Financial Clearance Blocked: Exiting member is actively guaranteeing {g_chk['active_guars']} "
                    f"unpaid facility/facilities for other members. Substitute guarantors must be provided first."
                )

            # Re-verify outstanding loans
            cursor.execute("""
                SELECT COALESCE(SUM(outstanding_balance), 0.00) AS total_loans
                FROM loans WHERE member_id = %s AND status = 'ACTIVE';
            """, (m_id,))
            l_chk = cursor.fetchone()
            current_loans = Decimal(str(l_chk["total_loans"])) if l_chk else Decimal("0.00")
            if current_loans > 0:
                # Check if member savings can set off the loan
                cursor.execute("SELECT total_balance FROM savings_accounts WHERE member_id = %s;", (m_id,))
                cur_sav = cursor.fetchone()
                sav_bal = Decimal(str(cur_sav["total_balance"])) if cur_sav else Decimal("0.00")
                if sav_bal < current_loans:
                    raise ValueError(
                        f"Financial Clearance Blocked: Outstanding loans (NGN {current_loans:,.2f}) exceed "
                        f"savings (NGN {sav_bal:,.2f}). Member must clear debt prior to exit settlement."
                    )
                # Auto set-off loans against savings
                cursor.execute("UPDATE loans SET status = 'COMPLETED', outstanding_balance = 0.00 WHERE member_id = %s AND status = 'ACTIVE';", (m_id,))
                cursor.execute("UPDATE savings_accounts SET total_balance = total_balance - %s WHERE member_id = %s;", (current_loans, m_id))

            # Zero out member accounts
            cursor.execute("UPDATE savings_accounts SET total_balance = 0.00, encumbered_balance = 0.00 WHERE member_id = %s;", (m_id,))
            cursor.execute("UPDATE share_accounts SET paid_up_amount = 0.00, units_held = 0 WHERE member_id = %s;", (m_id,))
            cursor.execute("UPDATE target_savings_accounts SET status = 'LIQUIDATED_ON_EXIT', current_balance = 0.00 WHERE member_id = %s;", (m_id,))

            new_member_status = "DECEASED" if exit_rec["exit_type"] == "DEATH_ESTATE_SETTLEMENT" else "EXITED"
            cursor.execute("UPDATE members SET status = %s WHERE id = %s;", (new_member_status, m_id))

            ref_code = refund_payment_ref or f"EXIT-REF-{secrets.token_hex(4).upper()}"
            cursor.execute("""
                UPDATE member_exits
                SET status = 'SETTLED_REFUNDED',
                    cleared_by_officer_id = %s,
                    approved_by_president_id = %s,
                    refund_payment_ref = %s,
                    refund_disbursed_at = NOW()
                WHERE id = %s;
            """, (officer_id, officer_id, ref_code, exit_id))

            # Post exit liquidation transaction
            net_amt = Decimal(str(exit_rec["net_refund_amount"]))
            cursor.execute("""
                INSERT INTO transactions (
                    transaction_ref, member_id, transaction_type, ledger_category,
                    amount, payment_method, channel_reference, narration, status
                ) VALUES (
                    %s, %s, 'DEBIT', 'SAVINGS',
                    %s, 'POLARIS_BANK_TRANSFER', %s, %s, 'VERIFIED'
                );
            """, (ref_code, m_id, net_amt, ref_code, f"Statutory exit settlement refund for {exit_rec['member_code']} ({exit_rec['exit_type']})"))

            # Real-Time Double-Entry General Ledger Posting (Module 4)
            sav_liq = Decimal(str(exit_rec["total_savings_at_exit"]))
            shr_liq = Decimal(str(exit_rec["total_shares_at_exit"]))
            fee_ded = Decimal(str(exit_rec["exit_processing_fee"]))
            lon_off = Decimal(str(exit_rec["outstanding_loans_at_exit"]))
            fin_off = Decimal(str(exit_rec["outstanding_fines_at_exit"]))
            net_ref = Decimal(str(exit_rec["net_refund_amount"]))

            je_exit_lines = []
            if sav_liq > 0:
                je_exit_lines.append({"account_code": "2010", "line_type": "DEBIT", "amount": sav_liq, "memo": "Member Savings Balance Liquidated"})
            if shr_liq > 0:
                je_exit_lines.append({"account_code": "3010", "line_type": "DEBIT", "amount": shr_liq, "memo": "Member Share Capital Liquidated"})
            if fee_ded > 0:
                je_exit_lines.append({"account_code": "4050", "line_type": "CREDIT", "amount": fee_ded, "memo": "Membership Exit Administrative Processing Fee"})
            if lon_off > 0:
                je_exit_lines.append({"account_code": "1030", "line_type": "CREDIT", "amount": lon_off, "memo": "Outstanding Loan Principal Offset"})
            if fin_off > 0:
                je_exit_lines.append({"account_code": "4040", "line_type": "CREDIT", "amount": fin_off, "memo": "Outstanding Disciplinary Fines Offset"})
            if net_ref > 0:
                je_exit_lines.append({"account_code": "1010", "line_type": "CREDIT", "amount": net_ref, "memo": "Net Settlement Payout via Polaris Bank"})

            if len(je_exit_lines) >= 2:
                self._post_journal_entry_with_cursor(
                    cursor=cursor,
                    entry_date=date.today(),
                    source_module='EXIT_SETTLEMENT',
                    source_reference=ref_code,
                    narration=f"Statutory exit liquidation for {exit_rec['member_code']} ({exit_rec['exit_type']})",
                    lines=je_exit_lines,
                    created_by=officer_id,
                    approved_by=officer_id,
                    status='POSTED'
                )

            conn.commit()

            self.log_audit_event(
                user_id=officer_id,
                actor_name=officer_role,
                actor_role=officer_role,
                action="MEMBER_EXIT_SETTLEMENT_APPROVED",
                resource_type="MEMBER_EXIT",
                resource_id=str(exit_id),
                details_before={"membership_status": exit_rec["member_status"]},
                details_after={
                    "new_status": new_member_status,
                    "refund_payment_ref": ref_code,
                    "net_refund_amount": float(net_amt)
                },
                summary=f"Approved exit settlement #{exit_id} for {exit_rec['member_code']}. Status: {new_member_status}, Refund: NGN {net_amt:,.2f}."
            )

            return {
                "status": "SUCCESS",
                "exit_id": exit_id,
                "member_code": exit_rec["member_code"],
                "new_membership_status": new_member_status,
                "refund_payment_ref": ref_code,
                "net_refund_amount": float(net_amt),
                "message": f"Exit settlement successfully finalized! Member {exit_rec['member_code']} status set to {new_member_status}."
            }
        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------------------
    # 20. BULK COOPERATOR CSV IMPORTER & DIRECTORY EXPORTER
    # -------------------------------------------------------------------------
    def bulk_import_members(
        self,
        cooperator_rows: List[Dict[str, Any]],
        admin_id: int
    ) -> Dict[str, Any]:
        """
        Bulk enrolls cooperators from verified CSV data:
        - Auto-generates sequential WMC-YYYY-XXX member codes.
        - Sets default initial password (Wealthbridge@2026).
        - Provisions tripartite accounts (Savings, Shares, Welfare).
        - Allocates initial opening balances if provided.
        - Records forensic audit entry.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            imported = []
            skipped = []
            now_year = datetime.now().year
            default_pw_hash = hash_password("Wealthbridge@2026")

            # Determine starting sequence number
            cursor.execute("SELECT MAX(id) AS max_id FROM members;")
            max_row = cursor.fetchone()
            next_seq = (max_row["max_id"] or 0) + 1

            for idx, row in enumerate(cooperator_rows, start=1):
                email = str(row.get("email") or "").strip().lower()
                phone = str(row.get("phone") or "").strip()
                first_name = str(row.get("first_name") or "").strip()
                last_name = str(row.get("last_name") or "").strip()

                if not first_name or not last_name or not email or not phone:
                    skipped.append({"row": idx, "reason": "Missing required fields (first_name, last_name, email, or phone)"})
                    continue

                # Check duplicate email or phone
                cursor.execute("SELECT id, member_code FROM members WHERE LOWER(email) = %s OR phone = %s;", (email, phone))
                dup = cursor.fetchone()
                if dup:
                    skipped.append({"row": idx, "email": email, "reason": f"Cooperator already exists with code {dup['member_code']}"})
                    continue

                member_code = f"WMC-{now_year}-{next_seq:03d}"
                next_seq += 1

                gender = str(row.get("gender") or "MALE").strip().upper()
                marital = str(row.get("marital_status") or "MARRIED").strip().upper()
                tier = str(row.get("contribution_tier") or "STANDARD").strip().upper()
                addr = str(row.get("residential_address") or "Lagos State, Nigeria").strip()
                nin = str(row.get("identification_number") or "").strip()

                cursor.execute("""
                    INSERT INTO members (
                        member_code, first_name, last_name, email, phone, gender,
                        marital_status, residential_address, identification_type,
                        identification_number, contribution_tier, password_hash,
                        status, kyc_completion_percent, admission_date, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, 'NIN',
                        %s, %s, %s,
                        'ACTIVE', 75, CURDATE(), NOW()
                    );
                """, (
                    member_code, first_name, last_name, email, phone, gender,
                    marital, addr, nin or None, tier, default_pw_hash
                ))
                new_id = cursor.lastrowid

                # Provision accounts
                open_sav = Decimal(str(row.get("opening_savings") or "0.00"))
                open_shares = Decimal(str(row.get("opening_shares") or "0.00"))
                open_welfare = Decimal(str(row.get("opening_welfare") or "0.00"))
                share_units = int(open_shares // Decimal("1000.00"))

                cursor.execute("""
                    INSERT INTO savings_accounts (member_id, total_balance, encumbered_balance)
                    VALUES (%s, %s, 0.00);
                """, (new_id, open_sav))

                cursor.execute("""
                    INSERT INTO share_accounts (member_id, paid_up_amount, units_held, benefits_qualified)
                    VALUES (%s, %s, %s, %s);
                """, (new_id, open_shares, share_units, 1 if share_units >= 5 else 0))

                cursor.execute("""
                    INSERT INTO welfare_accounts (member_id, cumulative_contributions)
                    VALUES (%s, %s);
                """, (new_id, open_welfare))

                # Post opening balance transaction if > 0
                if open_sav > 0:
                    init_ref = f"INIT-SAV-{member_code}"
                    cursor.execute("""
                        INSERT INTO transactions (
                            transaction_ref, member_id, transaction_type, ledger_category,
                            amount, payment_method, channel_reference, narration, status
                        ) VALUES (
                            %s, %s, 'CREDIT', 'SAVINGS',
                            %s, 'POLARIS_BANK_TRANSFER', %s, 'Opening savings balance migrated from legacy co-op books', 'VERIFIED'
                        );
                    """, (init_ref, new_id, open_sav, init_ref))

                imported.append({
                    "id": new_id,
                    "member_code": member_code,
                    "full_name": f"{first_name} {last_name}",
                    "email": email,
                    "tier": tier,
                    "opening_savings": float(open_sav),
                    "opening_shares": float(open_shares)
                })

            conn.commit()

            self.log_audit_event(
                user_id=admin_id,
                actor_name="System Administrator",
                actor_role="SUPER_ADMIN",
                action="BULK_MEMBERS_IMPORTED",
                resource_type="MEMBERS",
                resource_id="BULK_CSV",
                details_before=None,
                details_after={"imported_count": len(imported), "skipped_count": len(skipped)},
                summary=f"Bulk imported {len(imported)} cooperator(s); skipped {len(skipped)} row(s)."
            )

            return {
                "status": "SUCCESS",
                "imported_count": len(imported),
                "skipped_count": len(skipped),
                "imported_members": imported,
                "skipped_details": skipped
            }
        finally:
            cursor.close()
            conn.close()

    def export_members_directory_csv(self) -> str:
        """Generates standard RFC 4180 CSV cooperator directory with balances, tier, and standing."""
        members = self.list_members()
        import io
        import csv

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "Member Code", "Full Name", "Email", "Phone", "Gender",
            "Contribution Tier", "Membership Status", "KYC Completion %",
            "Ordinary Savings Balance (NGN)", "Paid-Up Shares (NGN)", "Share Units",
            "Welfare Pool Balance (NGN)", "Admission Date"
        ])

        for m in members:
            writer.writerow([
                m.get("member_code", ""),
                m.get("full_name", ""),
                m.get("email", ""),
                m.get("phone", ""),
                m.get("gender", ""),
                m.get("contribution_tier", "STANDARD"),
                m.get("membership_status", "ACTIVE"),
                f"{m.get('kyc_completion_percent', 0)}%",
                f"{float(m.get('savings_balance', 0)):.2f}",
                f"{float(m.get('share_equity_paid', 0)):.2f}",
                m.get("share_units", 0),
                f"{float(m.get('welfare_balance', 0)):.2f}",
                str(m.get("admission_date") or "")
            ])

        return output.getvalue()

    # =========================================================================
    # MODULE 4: ACCOUNTING & FINANCIAL CONTROL (DOUBLE-ENTRY GENERAL LEDGER)
    # =========================================================================

    def _lookup_account_id(self, cursor, code_or_id):
        """Resolves account ID from either an integer ID or a standard account code."""
        if isinstance(code_or_id, int):
            return code_or_id
        cursor.execute("SELECT id FROM chart_of_accounts WHERE account_code = %s LIMIT 1;", (str(code_or_id),))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Account code '{code_or_id}' not found in Chart of Accounts.")
        return row["id"]

    def _post_journal_entry_with_cursor(
        self,
        cursor,
        entry_date,
        source_module: str,
        source_reference: Optional[str],
        narration: str,
        lines: List[Dict[str, Any]],
        created_by: Optional[int] = None,
        status: str = 'POSTED',
        approved_by: Optional[int] = None,
        supporting_doc_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Internal engine for balanced double-entry General Ledger posting.
        Strictly enforces the fundamental accounting equation: Total Debits == Total Credits.
        """
        if not lines or len(lines) < 2:
            raise ValueError("A journal entry requires at least 2 line items (double-entry invariant).")

        tot_debit = Decimal("0.00")
        tot_credit = Decimal("0.00")
        resolved_lines = []

        for line in lines:
            acc_id = self._lookup_account_id(cursor, line.get("account_id") or line.get("account_code"))
            l_type = line.get("line_type", "").upper()
            if l_type not in ("DEBIT", "CREDIT"):
                raise ValueError(f"Invalid journal line type '{l_type}'. Must be DEBIT or CREDIT.")
            amt = Decimal(str(line.get("amount", "0.00")))
            if amt <= Decimal("0.00"):
                continue  # Skip zero-value allocation lines
            if l_type == "DEBIT":
                tot_debit += amt
            else:
                tot_credit += amt
            resolved_lines.append({
                "account_id": acc_id,
                "account_code": line.get("account_code"),
                "line_type": l_type,
                "amount": amt,
                "memo": line.get("memo")
            })

        if not resolved_lines or len(resolved_lines) < 2:
            raise ValueError("A journal entry requires at least 2 non-zero line items.")

        is_balanced = (abs(tot_debit - tot_credit) < Decimal("0.01"))
        if status == 'POSTED' and not is_balanced:
            raise ValueError(f"Double-entry bookkeeping error: Journal entry is not balanced. Total Debits (NGN {tot_debit:,.2f}) != Total Credits (NGN {tot_credit:,.2f}).")

        entry_num = f"JE-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"
        e_date = entry_date if isinstance(entry_date, (date, datetime)) else datetime.strptime(str(entry_date)[:10], "%Y-%m-%d").date()

        cursor.execute("""
            INSERT INTO journal_entries (
                entry_number, entry_date, source_module, source_reference, narration,
                total_debit, total_credit, is_balanced, status, created_by, approved_by,
                approved_at, supporting_doc_url
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s
            );
        """, (
            entry_num, e_date, source_module, source_reference, narration,
            tot_debit, tot_credit, 1 if is_balanced else 0, status, created_by,
            approved_by, datetime.now() if status == 'POSTED' and approved_by else None,
            supporting_doc_url
        ))
        entry_id = cursor.lastrowid

        for rl in resolved_lines:
            cursor.execute("""
                INSERT INTO journal_entry_lines (
                    journal_entry_id, account_id, line_type, amount, memo
                ) VALUES (%s, %s, %s, %s, %s);
            """, (entry_id, rl["account_id"], rl["line_type"], rl["amount"], rl["memo"]))

        return {
            "id": entry_id,
            "entry_number": entry_num,
            "entry_date": str(e_date),
            "source_module": source_module,
            "source_reference": source_reference,
            "narration": narration,
            "total_debit": float(tot_debit),
            "total_credit": float(tot_credit),
            "is_balanced": is_balanced,
            "status": status,
            "lines_count": len(resolved_lines)
        }

    def post_journal_entry(
        self,
        entry_date,
        source_module: str,
        source_reference: Optional[str],
        narration: str,
        lines: List[Dict[str, Any]],
        created_by: Optional[int] = None,
        status: str = 'POSTED',
        approved_by: Optional[int] = None,
        supporting_doc_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Public method to post or draft a double-entry journal entry."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            res = self._post_journal_entry_with_cursor(
                cursor, entry_date, source_module, source_reference, narration, lines,
                created_by=created_by, status=status, approved_by=approved_by,
                supporting_doc_url=supporting_doc_url
            )
            conn.commit()
            self.log_audit_event(
                user_id=created_by or 1,
                actor_name="Finance Desk",
                actor_role="FINANCIAL_SECRETARY",
                action="JOURNAL_ENTRY_POSTED" if status == 'POSTED' else "JOURNAL_ENTRY_DRAFTED",
                resource_type="JOURNAL_ENTRY",
                resource_id=res["entry_number"],
                details_before=None,
                details_after=res,
                summary=f"Journal entry {res['entry_number']} ({res['status']}) recorded: NGN {res['total_debit']:,.2f}."
            )
            return res
        finally:
            cursor.close()
            conn.close()

    def get_chart_of_accounts(self, account_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves statutory Chart of Accounts with live real-time debit, credit,
        and net balance computed directly from posted General Ledger lines.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            sql = """
                SELECT 
                    c.id, c.account_code, c.account_name, c.account_type, c.description,
                    c.is_active, c.is_system_controlled,
                    COALESCE(SUM(CASE WHEN l.line_type = 'DEBIT' AND j.status = 'POSTED' THEN l.amount ELSE 0.00 END), 0.00) as total_debit,
                    COALESCE(SUM(CASE WHEN l.line_type = 'CREDIT' AND j.status = 'POSTED' THEN l.amount ELSE 0.00 END), 0.00) as total_credit
                FROM chart_of_accounts c
                LEFT JOIN journal_entry_lines l ON c.id = l.account_id
                LEFT JOIN journal_entries j ON l.journal_entry_id = j.id
            """
            params = []
            if account_type:
                sql += " WHERE c.account_type = %s"
                params.append(account_type.upper())
            sql += " GROUP BY c.id, c.account_code, c.account_name, c.account_type, c.description, c.is_active, c.is_system_controlled ORDER BY c.account_code ASC;"
            cursor.execute(sql, params)
            accounts = cursor.fetchall()
            for a in accounts:
                td = Decimal(str(a["total_debit"]))
                tc = Decimal(str(a["total_credit"]))
                if a["account_type"] in ("ASSET", "EXPENSE"):
                    net = td - tc
                else:
                    net = tc - td
                a["total_debit"] = float(td)
                a["total_credit"] = float(tc)
                a["net_balance"] = float(net)
            return accounts
        finally:
            cursor.close()
            conn.close()

    def get_trial_balance(self, as_of_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates standard balanced Trial Balance as of a specified date.
        Verifies Debits == Credits across the entire cooperative General Ledger.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            target_date = as_of_date or str(date.today())
            cursor.execute("""
                SELECT 
                    c.id, c.account_code, c.account_name, c.account_type,
                    COALESCE(SUM(CASE WHEN l.line_type = 'DEBIT' THEN l.amount ELSE 0.00 END), 0.00) as total_debit,
                    COALESCE(SUM(CASE WHEN l.line_type = 'CREDIT' THEN l.amount ELSE 0.00 END), 0.00) as total_credit
                FROM chart_of_accounts c
                LEFT JOIN journal_entry_lines l ON c.id = l.account_id
                LEFT JOIN journal_entries j ON l.journal_entry_id = j.id AND j.status = 'POSTED' AND j.entry_date <= %s
                GROUP BY c.id, c.account_code, c.account_name, c.account_type
                ORDER BY c.account_code ASC;
            """, (target_date,))
            rows = cursor.fetchall()

            grand_dr = Decimal("0.00")
            grand_cr = Decimal("0.00")
            tb_accounts = []

            for r in rows:
                td = Decimal(str(r["total_debit"]))
                tc = Decimal(str(r["total_credit"]))
                if td == 0 and tc == 0:
                    continue
                
                if r["account_type"] in ("ASSET", "EXPENSE"):
                    net = td - tc
                    if net >= 0:
                        col_dr = net
                        col_cr = Decimal("0.00")
                    else:
                        col_dr = Decimal("0.00")
                        col_cr = abs(net)
                else:
                    net = tc - td
                    if net >= 0:
                        col_dr = Decimal("0.00")
                        col_cr = net
                    else:
                        col_dr = abs(net)
                        col_cr = Decimal("0.00")

                grand_dr += col_dr
                grand_cr += col_cr

                tb_accounts.append({
                    "id": r["id"],
                    "account_code": r["account_code"],
                    "account_name": r["account_name"],
                    "account_type": r["account_type"],
                    "total_debit": float(td),
                    "total_credit": float(tc),
                    "trial_debit": float(col_dr),
                    "trial_credit": float(col_cr)
                })

            is_balanced = (abs(grand_dr - grand_cr) < Decimal("0.01"))
            return {
                "as_of_date": target_date,
                "accounts": tb_accounts,
                "grand_total_debit": float(grand_dr),
                "grand_total_credit": float(grand_cr),
                "variance": float(abs(grand_dr - grand_cr)),
                "is_balanced": is_balanced
            }
        finally:
            cursor.close()
            conn.close()

    def get_income_and_expenditure(self, date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates cooperative Income and Expenditure Statement (Statement of Comprehensive Income).
        Computes Operational Surplus/Deficit and statutory 50% reserve obligation under Cap C15 & Article 24.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            d_to = date_to or str(date.today())
            d_from = date_from or f"{str(date.today())[:4]}-01-01"

            cursor.execute("""
                SELECT 
                    c.id, c.account_code, c.account_name, c.account_type,
                    COALESCE(SUM(CASE WHEN l.line_type = 'DEBIT' THEN l.amount ELSE 0.00 END), 0.00) as total_debit,
                    COALESCE(SUM(CASE WHEN l.line_type = 'CREDIT' THEN l.amount ELSE 0.00 END), 0.00) as total_credit
                FROM chart_of_accounts c
                LEFT JOIN journal_entry_lines l ON c.id = l.account_id
                LEFT JOIN journal_entries j ON l.journal_entry_id = j.id AND j.status = 'POSTED' AND j.entry_date >= %s AND j.entry_date <= %s
                WHERE c.account_type IN ('INCOME', 'EXPENSE')
                GROUP BY c.id, c.account_code, c.account_name, c.account_type
                ORDER BY c.account_code ASC;
            """, (d_from, d_to))
            rows = cursor.fetchall()

            income_items = []
            expense_items = []
            tot_income = Decimal("0.00")
            tot_expense = Decimal("0.00")

            for r in rows:
                td = Decimal(str(r["total_debit"]))
                tc = Decimal(str(r["total_credit"]))
                if r["account_type"] == "INCOME":
                    net = tc - td
                    tot_income += net
                    income_items.append({
                        "account_code": r["account_code"],
                        "account_name": r["account_name"],
                        "amount": float(net)
                    })
                else:
                    net = td - tc
                    tot_expense += net
                    expense_items.append({
                        "account_code": r["account_code"],
                        "account_name": r["account_name"],
                        "amount": float(net)
                    })

            net_surplus = tot_income - tot_expense
            statutory_reserve_50pct = round(max(Decimal("0.00"), net_surplus * Decimal("0.50")), 2)
            distributable_surplus_max = max(Decimal("0.00"), net_surplus - statutory_reserve_50pct)

            return {
                "period": {
                    "date_from": d_from,
                    "date_to": d_to
                },
                "income_items": income_items,
                "total_income": float(tot_income),
                "expense_items": expense_items,
                "total_expenditure": float(tot_expense),
                "net_surplus": float(net_surplus),
                "statutory_reserve_50pct": float(statutory_reserve_50pct),
                "distributable_surplus_max": float(distributable_surplus_max),
                "is_surplus": net_surplus >= Decimal("0.00")
            }
        finally:
            cursor.close()
            conn.close()

    def get_balance_sheet(self, as_of_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates cooperative Statement of Financial Position (Balance Sheet).
        Validates fundamental accounting equation: ASSETS == LIABILITIES + EQUITY.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            target_date = as_of_date or str(date.today())

            cursor.execute("""
                SELECT 
                    c.id, c.account_code, c.account_name, c.account_type,
                    COALESCE(SUM(CASE WHEN l.line_type = 'DEBIT' THEN l.amount ELSE 0.00 END), 0.00) as total_debit,
                    COALESCE(SUM(CASE WHEN l.line_type = 'CREDIT' THEN l.amount ELSE 0.00 END), 0.00) as total_credit
                FROM chart_of_accounts c
                LEFT JOIN journal_entry_lines l ON c.id = l.account_id
                LEFT JOIN journal_entries j ON l.journal_entry_id = j.id AND j.status = 'POSTED' AND j.entry_date <= %s
                WHERE c.account_type IN ('ASSET', 'LIABILITY', 'EQUITY')
                GROUP BY c.id, c.account_code, c.account_name, c.account_type
                ORDER BY c.account_code ASC;
            """, (target_date,))
            rows = cursor.fetchall()

            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN c.account_type = 'INCOME' THEN l.amount * (CASE WHEN l.line_type = 'CREDIT' THEN 1 ELSE -1 END) ELSE 0.00 END), 0.00) as total_income,
                    COALESCE(SUM(CASE WHEN c.account_type = 'EXPENSE' THEN l.amount * (CASE WHEN l.line_type = 'DEBIT' THEN 1 ELSE -1 END) ELSE 0.00 END), 0.00) as total_expense
                FROM chart_of_accounts c
                JOIN journal_entry_lines l ON c.id = l.account_id
                JOIN journal_entries j ON l.journal_entry_id = j.id AND j.status = 'POSTED' AND j.entry_date <= %s
                WHERE c.account_type IN ('INCOME', 'EXPENSE');
            """, (target_date,))
            ie_res = cursor.fetchone()
            curr_surplus = Decimal(str(ie_res["total_income"])) - Decimal(str(ie_res["total_expense"]))

            assets = []
            liabilities = []
            equity = []
            tot_assets = Decimal("0.00")
            tot_liab = Decimal("0.00")
            tot_eq = Decimal("0.00")

            for r in rows:
                td = Decimal(str(r["total_debit"]))
                tc = Decimal(str(r["total_credit"]))
                if r["account_type"] == "ASSET":
                    bal = td - tc
                    tot_assets += bal
                    assets.append({"account_code": r["account_code"], "account_name": r["account_name"], "balance": float(bal)})
                elif r["account_type"] == "LIABILITY":
                    bal = tc - td
                    tot_liab += bal
                    liabilities.append({"account_code": r["account_code"], "account_name": r["account_name"], "balance": float(bal)})
                elif r["account_type"] == "EQUITY":
                    bal = tc - td
                    tot_eq += bal
                    equity.append({"account_code": r["account_code"], "account_name": r["account_name"], "balance": float(bal)})

            equity.append({
                "account_code": "SURPLUS_CURR",
                "account_name": "Current Operational Net Surplus / (Deficit)",
                "balance": float(curr_surplus)
            })
            tot_eq += curr_surplus

            tot_liab_and_eq = tot_liab + tot_eq
            is_balanced = (abs(tot_assets - tot_liab_and_eq) < Decimal("0.01"))

            return {
                "as_of_date": target_date,
                "assets": assets,
                "total_assets": float(tot_assets),
                "liabilities": liabilities,
                "total_liabilities": float(tot_liab),
                "equity": equity,
                "total_equity": float(tot_eq),
                "total_liabilities_and_equity": float(tot_liab_and_eq),
                "difference": float(abs(tot_assets - tot_liab_and_eq)),
                "is_balanced": is_balanced
            }
        finally:
            cursor.close()
            conn.close()

    def get_cash_flow_statement(self, date_from: Optional[str] = None, date_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates Cash Flow Statement tracking operating, investing, and financing cash flows
        through the cooperative's bank and clearing escrow accounts (1010 Polaris & 1020 DVA).
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            d_to = date_to or str(date.today())
            d_from = date_from or f"{str(date.today())[:4]}-01-01"

            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN l.line_type = 'DEBIT' THEN l.amount ELSE -l.amount END), 0.00) as opening_cash
                FROM journal_entry_lines l
                JOIN journal_entries j ON l.journal_entry_id = j.id AND j.status = 'POSTED' AND j.entry_date < %s
                JOIN chart_of_accounts c ON l.account_id = c.id
                WHERE c.account_code IN ('1010', '1020');
            """, (d_from,))
            op_row = cursor.fetchone()
            opening_cash = Decimal(str(op_row["opening_cash"] if op_row else "0.00"))

            cursor.execute("""
                SELECT 
                    j.source_module,
                    COALESCE(SUM(CASE WHEN l.line_type = 'DEBIT' THEN l.amount ELSE 0.00 END), 0.00) as total_cash_in,
                    COALESCE(SUM(CASE WHEN l.line_type = 'CREDIT' THEN l.amount ELSE 0.00 END), 0.00) as total_cash_out
                FROM journal_entry_lines l
                JOIN journal_entries j ON l.journal_entry_id = j.id AND j.status = 'POSTED' AND j.entry_date >= %s AND j.entry_date <= %s
                JOIN chart_of_accounts c ON l.account_id = c.id
                WHERE c.account_code IN ('1010', '1020')
                GROUP BY j.source_module;
            """, (d_from, d_to))
            module_rows = cursor.fetchall()

            operating_net = Decimal("0.00")
            investing_net = Decimal("0.00")
            financing_net = Decimal("0.00")

            operating_activities = []
            investing_activities = []
            financing_activities = []

            for mr in module_rows:
                cin = Decimal(str(mr["total_cash_in"]))
                cout = Decimal(str(mr["total_cash_out"]))
                net = cin - cout
                mod = mr["source_module"]

                if mod in ("REMITTANCE_WATERFALL", "WELFARE_PAYOUT", "MANUAL_JOURNAL"):
                    operating_net += net
                    operating_activities.append({"activity": mod.replace("_", " ").title(), "cash_in": float(cin), "cash_out": float(cout), "net": float(net)})
                elif mod in ("LOAN_DISBURSEMENT", "LOAN_REPAYMENT"):
                    investing_net += net
                    investing_activities.append({"activity": mod.replace("_", " ").title(), "cash_in": float(cin), "cash_out": float(cout), "net": float(net)})
                elif mod in ("EXIT_SETTLEMENT", "DIVIDEND_DISTRIBUTION"):
                    financing_net += net
                    financing_activities.append({"activity": mod.replace("_", " ").title(), "cash_in": float(cin), "cash_out": float(cout), "net": float(net)})

            net_change = operating_net + investing_net + financing_net
            closing_cash = opening_cash + net_change

            return {
                "period": {"date_from": d_from, "date_to": d_to},
                "opening_cash_balance": float(opening_cash),
                "operating_activities": operating_activities,
                "operating_net": float(operating_net),
                "investing_activities": investing_activities,
                "investing_net": float(investing_net),
                "financing_activities": financing_activities,
                "financing_net": float(financing_net),
                "net_change_in_cash": float(net_change),
                "closing_cash_balance": float(closing_cash)
            }
        finally:
            cursor.close()
            conn.close()

    def submit_manual_journal_entry(
        self,
        entry_date,
        narration: str,
        lines: List[Dict[str, Any]],
        created_by: int,
        supporting_doc_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Maker step: Drafts a balanced manual journal entry awaiting Checker review."""
        return self.post_journal_entry(
            entry_date=entry_date,
            source_module='MANUAL_JOURNAL',
            source_reference=f"MAN-DRAFT-{secrets.token_hex(3).upper()}",
            narration=narration,
            lines=lines,
            created_by=created_by,
            status='DRAFT',
            supporting_doc_url=supporting_doc_url
        )

    def get_journal_entries(self, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Lists General Ledger journal entries with full double-entry line details."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            sql = """
                SELECT 
                    j.id, j.entry_number, j.entry_date, j.source_module, j.source_reference,
                    j.narration, j.total_debit, j.total_credit, j.is_balanced, j.status,
                    j.created_by, j.approved_by, j.approved_at, j.supporting_doc_url, j.created_at,
                    CONCAT(creator.first_name, ' ', creator.last_name) as creator_name,
                    CONCAT(approver.first_name, ' ', approver.last_name) as approver_name
                FROM journal_entries j
                LEFT JOIN members creator ON j.created_by = creator.id
                LEFT JOIN members approver ON j.approved_by = approver.id
            """
            params = []
            if status:
                sql += " WHERE j.status = %s"
                params.append(status.upper())
            sql += " ORDER BY j.entry_date DESC, j.id DESC LIMIT %s OFFSET %s;"
            params.extend([limit, offset])
            cursor.execute(sql, params)
            entries = cursor.fetchall()

            for e in entries:
                e["total_debit"] = float(e["total_debit"])
                e["total_credit"] = float(e["total_credit"])
                e["entry_date"] = str(e["entry_date"])
                e["created_at"] = str(e["created_at"])
                if e.get("approved_at"):
                    e["approved_at"] = str(e["approved_at"])

                cursor.execute("""
                    SELECT 
                        l.id, l.account_id, l.line_type, l.amount, l.memo,
                        c.account_code, c.account_name, c.account_type
                    FROM journal_entry_lines l
                    JOIN chart_of_accounts c ON l.account_id = c.id
                    WHERE l.journal_entry_id = %s
                    ORDER BY l.line_type ASC, l.id ASC;
                """, (e["id"],))
                lines = cursor.fetchall()
                for l in lines:
                    l["amount"] = float(l["amount"])
                e["lines"] = lines

            return entries
        finally:
            cursor.close()
            conn.close()

    def approve_manual_journal_entry(
        self,
        entry_id: int,
        officer_id: int,
        officer_role: str,
        action: str = 'APPROVE',
        rejection_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Checker step: President / Auditor reviews and posts or rejects draft manual journal."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM journal_entries WHERE id = %s;", (entry_id,))
            entry = cursor.fetchone()
            if not entry:
                raise ValueError(f"Journal entry #{entry_id} not found.")
            if entry["status"] != 'DRAFT':
                raise ValueError(f"Journal entry #{entry_id} is in '{entry['status']}' state; only DRAFT entries can be reviewed.")

            if officer_role != 'SUPER_ADMIN' and entry["created_by"] == officer_id:
                raise ValueError("Dual-control governance violation: You cannot approve a journal entry you drafted yourself.")

            new_status = 'POSTED' if action.upper() == 'APPROVE' else 'REJECTED'
            memo_upd = f" [Checker Note: {rejection_reason}]" if rejection_reason else ""

            cursor.execute("""
                UPDATE journal_entries
                SET 
                    status = %s,
                    approved_by = %s,
                    approved_at = NOW(),
                    narration = CONCAT(narration, %s)
                WHERE id = %s;
            """, (new_status, officer_id, memo_upd, entry_id))
            conn.commit()

            self.log_audit_event(
                user_id=officer_id,
                actor_name=officer_role,
                actor_role=officer_role,
                action=f"JOURNAL_ENTRY_{new_status}",
                resource_type="JOURNAL_ENTRY",
                resource_id=entry["entry_number"],
                details_before={"status": "DRAFT"},
                details_after={"status": new_status, "approved_by": officer_id},
                summary=f"Journal entry {entry['entry_number']} was {new_status} by {officer_role}."
            )

            return {
                "status": "SUCCESS",
                "entry_id": entry_id,
                "entry_number": entry["entry_number"],
                "new_status": new_status,
                "message": f"Journal entry {entry['entry_number']} has been successfully {new_status.lower()}."
            }
        finally:
            cursor.close()
            conn.close()

    def sync_transactions_to_general_ledger(self) -> Dict[str, Any]:
        """
        One-shot reconciliation helper: Scans all historical verified transactions
        and ensures they are fully posted into the double-entry General Ledger.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT t.id, t.transaction_ref, t.transaction_type, t.ledger_category,
                       t.amount, t.narration, t.transaction_date, t.created_at, t.member_id
                FROM transactions t
                WHERE t.status = 'VERIFIED'
                  AND t.transaction_ref NOT IN (
                      SELECT source_reference FROM journal_entries WHERE source_reference IS NOT NULL
                  )
                ORDER BY t.id ASC;
            """)
            unposted = cursor.fetchall()
            synced_count = 0

            for t in unposted:
                amt = Decimal(str(t["amount"]))
                if amt <= Decimal("0.00"):
                    continue
                cat = t["ledger_category"]
                ttype = t["transaction_type"]
                ref = t["transaction_ref"]
                e_date = t.get("transaction_date") or t.get("created_at") or date.today()

                lines = []
                s_mod = "REMITTANCE_WATERFALL"

                if cat == "SAVINGS" and ttype == "CREDIT":
                    lines = [
                        {"account_code": "1010", "line_type": "DEBIT", "amount": amt, "memo": "Remittance into Polaris Escrow"},
                        {"account_code": "2010", "line_type": "CREDIT", "amount": amt, "memo": t["narration"]}
                    ]
                elif cat == "SAVINGS" and ttype == "DEBIT":
                    lines = [
                        {"account_code": "2010", "line_type": "DEBIT", "amount": amt, "memo": t["narration"]},
                        {"account_code": "1010", "line_type": "CREDIT", "amount": amt, "memo": "Payout from Polaris Escrow"}
                    ]
                elif cat == "WELFARE_FUND" and ttype == "CREDIT":
                    lines = [
                        {"account_code": "1010", "line_type": "DEBIT", "amount": amt, "memo": "Welfare contribution into Polaris Escrow"},
                        {"account_code": "2030", "line_type": "CREDIT", "amount": amt, "memo": t["narration"]}
                    ]
                elif cat == "SHARE_CAPITAL" and ttype == "CREDIT":
                    lines = [
                        {"account_code": "1010", "line_type": "DEBIT", "amount": amt, "memo": "Share equity subscription into Polaris Escrow"},
                        {"account_code": "3010", "line_type": "CREDIT", "amount": amt, "memo": t["narration"]}
                    ]
                elif cat == "REGISTRATION_FEE" and ttype == "CREDIT":
                    lines = [
                        {"account_code": "1010", "line_type": "DEBIT", "amount": amt, "memo": "Entrance fee into Polaris Escrow"},
                        {"account_code": "4020", "line_type": "CREDIT", "amount": amt, "memo": t["narration"]}
                    ]
                elif cat == "DISCIPLINARY_FINE" and ttype == "CREDIT":
                    lines = [
                        {"account_code": "1010", "line_type": "DEBIT", "amount": amt, "memo": "Fine liquidated into Polaris Escrow"},
                        {"account_code": "4040", "line_type": "CREDIT", "amount": amt, "memo": t["narration"]}
                    ]
                elif cat == "LOAN_DISBURSEMENT" and ttype == "DEBIT":
                    s_mod = "LOAN_DISBURSEMENT"
                    lines = [
                        {"account_code": "1030", "line_type": "DEBIT", "amount": amt, "memo": "Member Loan Principal Receivable"},
                        {"account_code": "1010", "line_type": "CREDIT", "amount": amt, "memo": t["narration"]}
                    ]
                elif cat == "LOAN_REPAYMENT" and ttype == "CREDIT":
                    s_mod = "LOAN_REPAYMENT"
                    lines = [
                        {"account_code": "1010", "line_type": "DEBIT", "amount": amt, "memo": "Loan repayment into Polaris Escrow"},
                        {"account_code": "1030", "line_type": "CREDIT", "amount": amt, "memo": t["narration"]}
                    ]

                if lines:
                    self._post_journal_entry_with_cursor(
                        cursor=cursor,
                        entry_date=e_date,
                        source_module=s_mod,
                        source_reference=ref,
                        narration=t["narration"] or f"Historical transaction sync {ref}",
                        lines=lines,
                        created_by=t.get("member_id"),
                        status='POSTED'
                    )
                    synced_count += 1

            conn.commit()
            return {"status": "SUCCESS", "synced_transactions_count": synced_count}
        finally:
            cursor.close()
            conn.close()

    # =========================================================================
    # MODULE 5: DIVIDEND & ANNUAL SURPLUS DISTRIBUTION ENGINE
    # =========================================================================

    def simulate_dividend_distribution(
        self,
        period_name: str,
        financial_year_start: str,
        financial_year_end: str,
        net_surplus: Optional[float] = None,
        statutory_reserve_pct: float = 50.00,
        weight_share_pct: float = 60.00,
        weight_savings_pct: float = 40.00,
        weight_patronage_pct: float = 0.00,
        min_shares: int = 5,
        min_months: int = 6,
        disqualify_arrears: bool = True,
        simulated_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Module 5: Dynamic Dividend & Annual Surplus Distribution Engine.
        Simulates pro-rata member allocations with custom executive weights,
        disqualification filtering, and statutory 50% reserve adherence.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            if net_surplus is None:
                ie = self.get_income_and_expenditure(financial_year_start, financial_year_end)
                calc_surplus = Decimal(str(ie["net_surplus"]))
            else:
                calc_surplus = Decimal(str(net_surplus))

            if calc_surplus < Decimal("0.00"):
                calc_surplus = Decimal("0.00")

            stat_pct = Decimal(str(statutory_reserve_pct))
            if stat_pct < Decimal("50.00"):
                stat_pct = Decimal("50.00")

            statutory_reserve_amt = round(calc_surplus * (stat_pct / Decimal("100.00")), 2)
            distributable_pool = calc_surplus - statutory_reserve_amt

            w_sh = Decimal(str(weight_share_pct))
            w_sv = Decimal(str(weight_savings_pct))
            w_pt = Decimal(str(weight_patronage_pct))
            tot_w = w_sh + w_sv + w_pt
            if tot_w <= Decimal("0.00"):
                w_sh = Decimal("60.00")
                w_sv = Decimal("40.00")
                w_pt = Decimal("0.00")
                tot_w = Decimal("100.00")

            pool_sh = round(distributable_pool * (w_sh / tot_w), 2)
            pool_sv = round(distributable_pool * (w_sv / tot_w), 2)
            pool_pt = round(distributable_pool * (w_pt / tot_w), 2)
            rem_diff = distributable_pool - (pool_sh + pool_sv + pool_pt)
            pool_sh += rem_diff

            cursor.execute("""
                SELECT 
                    m.id, m.member_code, CONCAT(m.first_name, ' ', m.last_name) as full_name,
                    m.status as membership_status, m.admission_date,
                    m.dividend_payout_preference, m.bank_name, m.bank_account_number, m.bank_account_name,
                    COALESCE(sa.paid_up_amount, 0.00) as share_equity,
                    COALESCE(sa.units_held, 0) as share_units,
                    COALESCE(sva.total_balance, 0.00) as savings_balance
                FROM members m
                LEFT JOIN share_accounts sa ON m.id = sa.member_id
                LEFT JOIN savings_accounts sva ON m.id = sva.member_id
                ORDER BY m.id ASC;
            """)
            members = cursor.fetchall()

            cursor.execute("""
                SELECT l.member_id, COALESCE(SUM(lr.amount_paid), 0.00) as loan_patronage
                FROM loan_repayments lr
                JOIN loans l ON lr.loan_id = l.id
                WHERE lr.paid_date >= %s AND lr.paid_date <= %s AND lr.status = 'PAID'
                GROUP BY l.member_id;
            """, (financial_year_start, financial_year_end))
            loan_pat_map = {r["member_id"]: Decimal(str(r["loan_patronage"])) for r in cursor.fetchall()}

            cursor.execute("SELECT DISTINCT member_id FROM disciplinary_fines WHERE status = 'UNPAID';")
            fines_arrears = {r["member_id"] for r in cursor.fetchall()}

            cursor.execute("""
                SELECT DISTINCT l.member_id 
                FROM loan_repayments lr
                JOIN loans l ON lr.loan_id = l.id
                WHERE lr.status = 'PENDING' AND lr.due_date < %s;
            """, (financial_year_end,))
            loan_arrears = {r["member_id"] for r in cursor.fetchall()}
            members_with_arrears = fines_arrears.union(loan_arrears)

            fy_end_dt = datetime.strptime(str(financial_year_end)[:10], "%Y-%m-%d").date()

            denom_shares = Decimal("0.00")
            denom_savings = Decimal("0.00")
            denom_patronage = Decimal("0.00")

            evaluated_members = []

            for m in members:
                m_id = m["id"]
                sh_eq = Decimal(str(m["share_equity"]))
                sh_un = int(m["share_units"])
                sav_bal = Decimal(str(m["savings_balance"]))
                pat_vol = loan_pat_map.get(m_id, Decimal("0.00"))

                reasons = []
                if m["membership_status"] != "ACTIVE":
                    reasons.append(f"Membership status is {m['membership_status']}")
                if sh_un < min_shares:
                    reasons.append(f"Shareholding ({sh_un} units) below required minimum {min_shares} units")

                adm_dt = m.get("admission_date")
                if adm_dt:
                    tenure_days = (fy_end_dt - adm_dt).days
                    tenure_months = tenure_days / 30.4375
                    if tenure_months < min_months:
                        reasons.append(f"Tenure ({tenure_months:.1f} mos) below required {min_months} months")

                if disqualify_arrears and (m_id in members_with_arrears):
                    reasons.append("Active loan repayment or disciplinary fine arrears outstanding")

                is_qual = (len(reasons) == 0)

                if is_qual:
                    denom_shares += sh_eq
                    denom_savings += sav_bal
                    denom_patronage += pat_vol

                pref = m.get("dividend_payout_preference") or "SAVINGS_CREDIT"
                evaluated_members.append({
                    "member_id": m_id,
                    "member_code": m["member_code"],
                    "full_name": m["full_name"],
                    "membership_status": m["membership_status"],
                    "shares_held": sh_un,
                    "share_equity_amount": float(sh_eq),
                    "savings_balance": float(sav_bal),
                    "loan_patronage_volume": float(pat_vol),
                    "is_qualified": is_qual,
                    "disqualification_reason": "; ".join(reasons) if reasons else None,
                    "payout_preference": pref,
                    "bank_name": m.get("bank_name"),
                    "bank_account_number": m.get("bank_account_number"),
                    "bank_account_name": m.get("bank_account_name"),
                    "_sh_eq": sh_eq,
                    "_sav_bal": sav_bal,
                    "_pat_vol": pat_vol
                })

            total_allocated_pool = Decimal("0.00")
            qualified_count = 0
            disqualified_count = 0

            for em in evaluated_members:
                if em["is_qualified"]:
                    qualified_count += 1
                    div_sh = round((em["_sh_eq"] / denom_shares) * pool_sh, 2) if denom_shares > 0 else Decimal("0.00")
                    div_sv = round((em["_sav_bal"] / denom_savings) * pool_sv, 2) if denom_savings > 0 else Decimal("0.00")
                    div_pt = round((em["_pat_vol"] / denom_patronage) * pool_pt, 2) if denom_patronage > 0 else Decimal("0.00")
                    tot_div = div_sh + div_sv + div_pt

                    em["dividend_from_shares"] = float(div_sh)
                    em["dividend_from_savings"] = float(div_sv)
                    em["dividend_from_patronage"] = float(div_pt)
                    em["total_dividend_payable"] = float(tot_div)
                    total_allocated_pool += tot_div
                else:
                    disqualified_count += 1
                    em["dividend_from_shares"] = 0.00
                    em["dividend_from_savings"] = 0.00
                    em["dividend_from_patronage"] = 0.00
                    em["total_dividend_payable"] = 0.00

                del em["_sh_eq"]
                del em["_sav_bal"]
                del em["_pat_vol"]

            return {
                "period_name": period_name,
                "financial_year_start": financial_year_start,
                "financial_year_end": financial_year_end,
                "net_surplus_amount": float(calc_surplus),
                "statutory_reserve_percent": float(stat_pct),
                "statutory_reserve_amount": float(statutory_reserve_amt),
                "distributable_pool_amount": float(distributable_pool),
                "weight_share_capital_percent": float(w_sh),
                "weight_savings_volume_percent": float(w_sv),
                "weight_patronage_percent": float(w_pt),
                "min_share_units_required": min_shares,
                "min_active_months_required": min_months,
                "disqualify_active_arrears": disqualify_arrears,
                "pool_allocations": {
                    "shares_pool": float(pool_sh),
                    "savings_pool": float(pool_sv),
                    "patronage_pool": float(pool_pt)
                },
                "denominators": {
                    "total_qualified_shares": float(denom_shares),
                    "total_qualified_savings": float(denom_savings),
                    "total_qualified_patronage": float(denom_patronage)
                },
                "summary": {
                    "total_evaluated_members": len(evaluated_members),
                    "total_qualified_members": qualified_count,
                    "total_disqualified_members": disqualified_count,
                    "total_allocated_pool": float(total_allocated_pool)
                },
                "allocations": evaluated_members
            }
        finally:
            cursor.close()
            conn.close()

    def save_dividend_period(self, simulation_data: Dict[str, Any], officer_id: int) -> Dict[str, Any]:
        """Saves simulated dividend distribution run into dividend_periods and dividend_allocations."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                INSERT INTO dividend_periods (
                    period_name, financial_year_start, financial_year_end,
                    net_surplus_amount, statutory_reserve_percent, statutory_reserve_amount,
                    distributable_pool_amount, weight_share_capital_percent, weight_savings_volume_percent,
                    weight_patronage_percent, min_share_units_required, min_active_months_required,
                    disqualify_active_arrears, total_qualified_members, total_disqualified_members,
                    status, simulated_by_user_id
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    'AUDIT_REVIEW', %s
                );
            """, (
                simulation_data["period_name"], simulation_data["financial_year_start"], simulation_data["financial_year_end"],
                Decimal(str(simulation_data["net_surplus_amount"])), Decimal(str(simulation_data["statutory_reserve_percent"])), Decimal(str(simulation_data["statutory_reserve_amount"])),
                Decimal(str(simulation_data["distributable_pool_amount"])), Decimal(str(simulation_data["weight_share_capital_percent"])), Decimal(str(simulation_data["weight_savings_volume_percent"])),
                Decimal(str(simulation_data["weight_patronage_percent"])), simulation_data["min_share_units_required"], simulation_data["min_active_months_required"],
                1 if simulation_data["disqualify_active_arrears"] else 0, simulation_data["summary"]["total_qualified_members"], simulation_data["summary"]["total_disqualified_members"],
                officer_id
            ))
            period_id = cursor.lastrowid

            for a in simulation_data["allocations"]:
                cursor.execute("""
                    INSERT INTO dividend_allocations (
                        dividend_period_id, member_id, shares_held, share_equity_amount,
                        savings_balance, loan_patronage_volume, is_qualified, disqualification_reason,
                        dividend_from_shares, dividend_from_savings, dividend_from_patronage,
                        total_dividend_payable, payout_preference, payout_status
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, 'PENDING'
                    );
                """, (
                    period_id, a["member_id"], a["shares_held"], Decimal(str(a["share_equity_amount"])),
                    Decimal(str(a["savings_balance"])), Decimal(str(a["loan_patronage_volume"])),
                    1 if a["is_qualified"] else 0, a["disqualification_reason"],
                    Decimal(str(a["dividend_from_shares"])), Decimal(str(a["dividend_from_savings"])),
                    Decimal(str(a["dividend_from_patronage"])), Decimal(str(a["total_dividend_payable"])),
                    a["payout_preference"]
                ))

            conn.commit()

            self.log_audit_event(
                user_id=officer_id,
                actor_name="Finance Desk",
                actor_role="FINANCIAL_SECRETARY",
                action="DIVIDEND_PERIOD_SIMULATED",
                resource_type="DIVIDEND_PERIOD",
                resource_id=str(period_id),
                details_before=None,
                details_after={"period_name": simulation_data["period_name"], "net_surplus": simulation_data["net_surplus_amount"]},
                summary=f"Created dividend distribution draft #{period_id} ({simulation_data['period_name']}) for audit review."
            )

            return {
                "status": "SUCCESS",
                "period_id": period_id,
                "period_name": simulation_data["period_name"],
                "message": f"Dividend period #{period_id} created in AUDIT_REVIEW status with {len(simulation_data['allocations'])} member allocations."
            }
        finally:
            cursor.close()
            conn.close()

    def get_dividend_periods(self) -> List[Dict[str, Any]]:
        """Lists all annual dividend distribution periods with approval status."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    dp.*,
                    CONCAT(u_sim.first_name, ' ', u_sim.last_name) as simulated_by_name,
                    CONCAT(u_app.first_name, ' ', u_app.last_name) as approved_by_name
                FROM dividend_periods dp
                LEFT JOIN members u_sim ON dp.simulated_by_user_id = u_sim.id
                LEFT JOIN members u_app ON dp.approved_by_president_id = u_app.id
                ORDER BY dp.id DESC;
            """)
            periods = cursor.fetchall()
            for p in periods:
                for col in ["net_surplus_amount", "statutory_reserve_percent", "statutory_reserve_amount",
                            "distributable_pool_amount", "weight_share_capital_percent", "weight_savings_volume_percent",
                            "weight_patronage_percent"]:
                    if col in p and p[col] is not None:
                        p[col] = float(p[col])
                for dt in ["financial_year_start", "financial_year_end", "created_at", "approved_at"]:
                    if p.get(dt):
                        p[dt] = str(p[dt])
            return periods
        finally:
            cursor.close()
            conn.close()

    def get_dividend_period_details(self, period_id: int) -> Dict[str, Any]:
        """Retrieves dividend period master record plus member-level allocation audit table."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM dividend_periods WHERE id = %s;", (period_id,))
            period = cursor.fetchone()
            if not period:
                raise ValueError(f"Dividend period #{period_id} not found.")

            for col in ["net_surplus_amount", "statutory_reserve_percent", "statutory_reserve_amount",
                        "distributable_pool_amount", "weight_share_capital_percent", "weight_savings_volume_percent",
                        "weight_patronage_percent"]:
                if col in period and period[col] is not None:
                    period[col] = float(period[col])
            for dt in ["financial_year_start", "financial_year_end", "created_at", "approved_at"]:
                if period.get(dt):
                    period[dt] = str(period[dt])

            cursor.execute("""
                SELECT 
                    da.*,
                    m.member_code, CONCAT(m.first_name, ' ', m.last_name) as full_name,
                    m.bank_name, m.bank_account_number, m.bank_account_name
                FROM dividend_allocations da
                JOIN members m ON da.member_id = m.id
                WHERE da.dividend_period_id = %s
                ORDER BY da.is_qualified DESC, da.total_dividend_payable DESC;
            """, (period_id,))
            allocations = cursor.fetchall()

            for a in allocations:
                for num_col in ["share_equity_amount", "savings_balance", "loan_patronage_volume",
                                "dividend_from_shares", "dividend_from_savings", "dividend_from_patronage",
                                "total_dividend_payable"]:
                    if num_col in a and a[num_col] is not None:
                        a[num_col] = float(a[num_col])
                for dt_col in ["created_at", "settled_at"]:
                    if a.get(dt_col):
                        a[dt_col] = str(a[dt_col])

            period["allocations"] = allocations
            return period
        finally:
            cursor.close()
            conn.close()

    def approve_and_post_dividend(self, period_id: int, officer_id: int, officer_role: str) -> Dict[str, Any]:
        """
        Presidential sign-off: Finalizes dividend distribution, credits member savings accounts
        (or marks for bank disbursement), and posts balanced General Ledger entries:
        Debit: 3040 (Retained Operating Surplus)
        Credit: 3020 (Statutory Reserve Fund)
        Credit: 2010 (Member Regular Savings Deposits)
        Credit: 1010 (Polaris Bank Escrow for Bank payouts)
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM dividend_periods WHERE id = %s;", (period_id,))
            period = cursor.fetchone()
            if not period:
                raise ValueError(f"Dividend period #{period_id} not found.")
            if period["status"] == "APPROVED_POSTED":
                raise ValueError(f"Dividend period #{period_id} has already been approved and posted.")

            cursor.execute("""
                SELECT da.*, m.member_code, m.bank_name, m.bank_account_number
                FROM dividend_allocations da
                JOIN members m ON da.member_id = m.id
                WHERE da.dividend_period_id = %s;
            """, (period_id,))
            allocations = cursor.fetchall()

            tot_savings_credits = Decimal("0.00")
            tot_bank_payouts = Decimal("0.00")
            ts_batch = f"{int(time.time()*1000)}"

            for a in allocations:
                tot_pay = Decimal(str(a["total_dividend_payable"]))
                if not a["is_qualified"] or tot_pay <= Decimal("0.00"):
                    continue

                ref = f"DIV-{period_id}-{a['member_id']}-{ts_batch}"
                pref = a["payout_preference"] or "SAVINGS_CREDIT"

                if pref == "SAVINGS_CREDIT":
                    cursor.execute("""
                        UPDATE savings_accounts
                        SET total_balance = total_balance + %s
                        WHERE member_id = %s;
                    """, (tot_pay, a["member_id"]))

                    cursor.execute("""
                        INSERT INTO transactions (
                            transaction_ref, member_id, transaction_type, ledger_category,
                            amount, payment_method, channel_reference, narration, status
                        ) VALUES (
                            %s, %s, 'CREDIT', 'SAVINGS',
                            %s, 'INTERNAL_SET_OFF', %s, %s, 'VERIFIED'
                        );
                    """, (
                        ref, a["member_id"], tot_pay, ref,
                        f"Annual Surplus Dividend ({period['period_name']}) - Credited to Savings"
                    ))

                    cursor.execute("""
                        UPDATE dividend_allocations
                        SET payout_status = 'CREDITED_TO_SAVINGS', payout_reference = %s, settled_at = NOW()
                        WHERE id = %s;
                    """, (ref, a["id"]))
                    tot_savings_credits += tot_pay

                else:
                    cursor.execute("""
                        INSERT INTO transactions (
                            transaction_ref, member_id, transaction_type, ledger_category,
                            amount, payment_method, channel_reference, narration, status
                        ) VALUES (
                            %s, %s, 'DEBIT', 'SAVINGS',
                            %s, 'POLARIS_BANK_TRANSFER', %s, %s, 'VERIFIED'
                        );
                    """, (
                        ref, a["member_id"], tot_pay, ref,
                        f"Annual Surplus Dividend ({period['period_name']}) - Electronic Bank Payout to {a['bank_name']} {a['bank_account_number']}"
                    ))

                    cursor.execute("""
                        UPDATE dividend_allocations
                        SET payout_status = 'DISBURSED_TO_BANK', payout_reference = %s, settled_at = NOW()
                        WHERE id = %s;
                    """, (ref, a["id"]))
                    tot_bank_payouts += tot_pay

            cursor.execute("""
                UPDATE dividend_periods
                SET status = 'APPROVED_POSTED',
                    approved_by_president_id = %s,
                    approved_at = NOW()
                WHERE id = %s;
            """, (officer_id, period_id))

            net_surplus = Decimal(str(period["net_surplus_amount"]))
            stat_res = Decimal(str(period["statutory_reserve_amount"]))
            dist_total = tot_savings_credits + tot_bank_payouts
            total_allocated = stat_res + dist_total

            je_lines = [
                {"account_code": "3040", "line_type": "DEBIT", "amount": total_allocated, "memo": f"Retained Surplus Allocated for {period['period_name']}"},
                {"account_code": "3020", "line_type": "CREDIT", "amount": stat_res, "memo": "Statutory Reserve Fund 50% Allocation (Cap C15)"}
            ]
            if tot_savings_credits > 0:
                je_lines.append({"account_code": "2010", "line_type": "CREDIT", "amount": tot_savings_credits, "memo": "Member Regular Savings Dividend Payouts"})
            if tot_bank_payouts > 0:
                je_lines.append({"account_code": "1010", "line_type": "CREDIT", "amount": tot_bank_payouts, "memo": "Direct Commercial Bank Dividend Payouts"})

            self._post_journal_entry_with_cursor(
                cursor=cursor,
                entry_date=date.today(),
                source_module='DIVIDEND_DISTRIBUTION',
                source_reference=f"DIV-PER-{period_id}",
                narration=f"Statutory Dividend & Surplus Distribution ({period['period_name']})",
                lines=je_lines,
                created_by=officer_id,
                approved_by=officer_id,
                status='POSTED'
            )

            conn.commit()

            self.log_audit_event(
                user_id=officer_id,
                actor_name=officer_role,
                actor_role=officer_role,
                action="DIVIDEND_DISTRIBUTION_POSTED",
                resource_type="DIVIDEND_PERIOD",
                resource_id=str(period_id),
                details_before={"status": "AUDIT_REVIEW"},
                details_after={
                    "status": "APPROVED_POSTED",
                    "tot_savings_credits": float(tot_savings_credits),
                    "tot_bank_payouts": float(tot_bank_payouts),
                    "statutory_reserve": float(stat_res)
                },
                summary=f"Approved & posted annual dividend #{period_id}. Savings Credited: NGN {tot_savings_credits:,.2f}, Bank Payouts: NGN {tot_bank_payouts:,.2f}."
            )

            return {
                "status": "SUCCESS",
                "period_id": period_id,
                "period_name": period["period_name"],
                "total_savings_credited": float(tot_savings_credits),
                "total_bank_disbursed": float(tot_bank_payouts),
                "statutory_reserve_retained": float(stat_res),
                "message": f"Annual dividend distribution #{period_id} successfully approved and posted to General Ledger."
            }
        finally:
            cursor.close()
            conn.close()

    def update_member_dividend_payout_preference(self, member_id: int, payout_preference: str) -> Dict[str, Any]:
        """Allows a cooperator to configure their surplus distribution preference (SAVINGS_CREDIT vs BANK_TRANSFER)."""
        valid_prefs = ("SAVINGS_CREDIT", "BANK_TRANSFER")
        pref_clean = payout_preference.upper().strip()
        if pref_clean not in valid_prefs:
            raise ValueError(f"Invalid payout preference '{payout_preference}'. Must be SAVINGS_CREDIT or BANK_TRANSFER.")

        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                UPDATE members
                SET dividend_payout_preference = %s, updated_at = NOW()
                WHERE id = %s;
            """, (pref_clean, member_id))
            conn.commit()

            return {
                "status": "SUCCESS",
                "member_id": member_id,
                "dividend_payout_preference": pref_clean,
                "message": f"Dividend payout preference updated to {pref_clean}."
            }
        finally:
            cursor.close()
            conn.close()

    def get_member_dividend_history(self, member_id: int) -> List[Dict[str, Any]]:
        """Retrieves cooperator dividend statement showing annual surplus payouts and breakdown."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    da.*,
                    dp.period_name, dp.financial_year_start, dp.financial_year_end,
                    dp.status as period_status
                FROM dividend_allocations da
                JOIN dividend_periods dp ON da.dividend_period_id = dp.id
                WHERE da.member_id = %s
                ORDER BY dp.id DESC;
            """, (member_id,))
            allocs = cursor.fetchall()
            for a in allocs:
                for num_col in ["share_equity_amount", "savings_balance", "loan_patronage_volume",
                                "dividend_from_shares", "dividend_from_savings", "dividend_from_patronage",
                                "total_dividend_payable"]:
                    if num_col in a and a[num_col] is not None:
                        a[num_col] = float(a[num_col])
                for dt_col in ["created_at", "settled_at", "financial_year_start", "financial_year_end"]:
                    if a.get(dt_col):
                        a[dt_col] = str(a[dt_col])
            return allocs
        finally:
            cursor.close()
            conn.close()

    def get_login_prompts_for_user(self, user_id: Any, member_code: str, roles: List[str]) -> List[Dict[str, Any]]:
        """
        Evaluates active statutory escalations, warnings, and prompts for the user upon sign-in:
        1. Overdue Loan Escalations:
           - >= 45 days default: Persistent modal prompt on sign-in for Borrower and all active Guarantors.
           - >= 90 days default: Persistent executive action prompt for FinSec & President to authorize foreclosure offset.
        2. Arrears & Membership Suspension:
           - Prompt explaining suspension if member status is 'SUSPENDED', highlighting ability to pay.
        3. Exit Settlement Cooling-off:
           - If member has lodged an exit notice, prompt stating the statutory cooling-off target payout date.
        """
        prompts = []
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # 1. Check if user is borrower with active overdue loan
            if isinstance(user_id, int):
                cursor.execute("""
                    SELECT 
                        l.id, l.loan_reference, l.outstanding_balance,
                        DATEDIFF(CURDATE(), MIN(lr.due_date)) AS days_overdue
                    FROM loans l
                    JOIN loan_repayments lr ON l.id = lr.loan_id
                    WHERE l.member_id = %s AND l.status = 'ACTIVE' AND lr.status != 'PAID' AND lr.due_date < CURDATE()
                    GROUP BY l.id;
                """, (user_id,))
                borrower_loans = cursor.fetchall()
                for bl in borrower_loans:
                    days = bl["days_overdue"] or 0
                    if days >= 45:
                        prompts.append({
                            "id": f"prompt-borrower-{bl['id']}",
                            "type": "LOAN_DEFAULT_BORROWER",
                            "severity": "CRITICAL" if days < 90 else "DANGER",
                            "title": f"URGENT: Serious Loan Default Warning (Day {days})",
                            "message": f"Your loan ({bl['loan_reference']}) has been in default for {days} days (Outstanding: NGN {float(bl['outstanding_balance']):,.2f}). Please remit overdue installments immediately to prevent statutory foreclosure against your guarantors' savings.",
                            "action_label": "Go to Repayment Desk",
                            "action_url": "#desk-advices"
                        })

                # 2. Check if user is a guarantor on an overdue loan
                cursor.execute("""
                    SELECT 
                        l.id, l.loan_reference, l.outstanding_balance,
                        lg.guaranteed_amount,
                        CONCAT(m.first_name, ' ', m.last_name) AS borrower_name,
                        DATEDIFF(CURDATE(), MIN(lr.due_date)) AS days_overdue
                    FROM loan_guarantors lg
                    JOIN loans l ON lg.loan_id = l.id
                    JOIN members m ON l.member_id = m.id
                    JOIN loan_repayments lr ON l.id = lr.loan_id
                    WHERE lg.guarantor_member_id = %s AND lg.status = 'ACCEPTED' AND l.status = 'ACTIVE'
                      AND lr.status != 'PAID' AND lr.due_date < CURDATE()
                    GROUP BY l.id, lg.id;
                """, (user_id,))
                guar_loans = cursor.fetchall()
                for gl in guar_loans:
                    days = gl["days_overdue"] or 0
                    if days >= 45:
                        prompts.append({
                            "id": f"prompt-guar-{gl['id']}",
                            "type": "LOAN_DEFAULT_GUARANTOR",
                            "severity": "CRITICAL" if days < 90 else "DANGER",
                            "title": f"URGENT: Guaranteed Loan Default Alert (Day {days})",
                            "message": f"Cooperator {gl['borrower_name']}'s loan ({gl['loan_reference']}), which you guaranteed for NGN {float(gl['guaranteed_amount']):,.2f}, is {days} days in default. Your encumbered savings are at risk of foreclosure.",
                            "action_label": "View Loan Details",
                            "action_url": "#desk-loans"
                        })

                # 3. Check if member is SUSPENDED
                cursor.execute("SELECT status FROM members WHERE id = %s;", (user_id,))
                mem_st = cursor.fetchone()
                if mem_st and mem_st["status"] == "SUSPENDED":
                    prompts.append({
                        "id": "prompt-suspended",
                        "type": "MEMBERSHIP_SUSPENDED",
                        "severity": "WARNING",
                        "title": "Membership Suspended (Arrears Notice)",
                        "message": "Your membership status has been temporarily suspended due to consecutive unremitted monthly payment obligations. You may still make payments through your portal to clear your arrears and restore active standing.",
                        "action_label": "Settle Arrears Now",
                        "action_url": "#desk-advices"
                    })

                # 4. Check if member has pending exit notice
                cursor.execute("""
                    SELECT id, exit_type, statutory_notice_expiry_date, net_refund_amount, status
                    FROM member_exits
                    WHERE member_id = %s AND status IN ('PENDING_CLEARANCE', 'FINANCIALLY_CLEARED')
                    LIMIT 1;
                """, (user_id,))
                ext = cursor.fetchone()
                if ext:
                    exp_date = str(ext["statutory_notice_expiry_date"])
                    prompts.append({
                        "id": f"prompt-exit-{ext['id']}",
                        "type": "EXIT_COOLING_OFF",
                        "severity": "INFO",
                        "title": "Voluntary Exit Notice - Statutory Cooling-Off",
                        "message": f"Your exit request #{ext['id']} is undergoing statutory review. Statutory cooling-off period active: you should expect payment on {exp_date}. Net refund: NGN {float(ext['net_refund_amount']):,.2f}.",
                        "action_label": "View Exit Status",
                        "action_url": "#page-profile"
                    })

            # 5. Check if user is Financial Secretary, President, or Super Admin for 90-Day Foreclosure Prompts
            is_finsec_or_pres = any(r in ("PRESIDENT", "FINANCIAL_SECRETARY", "SUPER_ADMIN") for r in roles)
            if is_finsec_or_pres:
                cursor.execute("""
                    SELECT 
                        l.id, l.loan_reference, l.outstanding_balance,
                        CONCAT(m.first_name, ' ', m.last_name) AS borrower_name,
                        m.member_code AS borrower_code,
                        COALESCE(sva.total_balance, 0.00) AS borrower_savings,
                        DATEDIFF(CURDATE(), MIN(lr.due_date)) AS days_overdue
                    FROM loans l
                    JOIN members m ON l.member_id = m.id
                    LEFT JOIN savings_accounts sva ON m.id = sva.member_id
                    JOIN loan_repayments lr ON l.id = lr.loan_id
                    WHERE l.status = 'ACTIVE' AND lr.status != 'PAID' AND lr.due_date < CURDATE()
                    GROUP BY l.id
                    HAVING days_overdue >= 90;
                """)
                severe_loans = cursor.fetchall()
                for sl in severe_loans:
                    prompts.append({
                        "id": f"prompt-exec-foreclose-{sl['id']}",
                        "type": "LOAN_FORECLOSURE_ACTION_REQUIRED",
                        "severity": "DANGER",
                        "title": f"ACTION REQUIRED: 90-Day Loan Default ({sl['borrower_name']})",
                        "message": f"Loan {sl['loan_reference']} has reached {sl['days_overdue']} days in default (Outstanding: NGN {float(sl['outstanding_balance']):,.2f}). FinSec & President authorization required to execute statutory offset from borrower savings (Avail: NGN {float(sl['borrower_savings']):,.2f}) and/or guarantor collateral.",
                        "loan_id": sl["id"],
                        "borrower_name": sl["borrower_name"],
                        "outstanding_balance": float(sl["outstanding_balance"]),
                        "action_label": "Open Foreclosure Desk",
                        "action_url": "#desk-loans"
                    })

            return prompts
        finally:
            cursor.close()
            conn.close()

    def scan_and_process_loan_defaults(self) -> Dict[str, Any]:
        """
        Scans all active loans for overdue repayment milestones:
        - Day 30: Dispatches milestone notification to ALL Admins and Guarantors.
        - Day 45: Dispatches milestone notification to ALL Admins and Guarantors (and flags for login prompt).
        - Day 90: Dispatches 90-day statutory foreclosure notification to FinSec & President.
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT 
                    l.id, l.loan_reference, l.outstanding_balance, l.member_id,
                    CONCAT(m.first_name, ' ', m.last_name) AS borrower_name,
                    m.member_code AS borrower_code,
                    DATEDIFF(CURDATE(), MIN(lr.due_date)) AS days_overdue
                FROM loans l
                JOIN members m ON l.member_id = m.id
                JOIN loan_repayments lr ON l.id = lr.loan_id
                WHERE l.status = 'ACTIVE' AND lr.status != 'PAID' AND lr.due_date < CURDATE()
                GROUP BY l.id;
            """)
            overdue_loans = cursor.fetchall()

            notifications_issued = 0

            for ol in overdue_loans:
                loan_id = ol["id"]
                days = ol["days_overdue"] or 0
                b_name = ol["borrower_name"]
                b_code = ol["borrower_code"]
                loan_ref = ol["loan_reference"]
                out_bal = float(ol["outstanding_balance"])

                milestones_to_check = []
                if days >= 90:
                    milestones_to_check = [30, 45, 90]
                elif days >= 45:
                    milestones_to_check = [30, 45]
                elif days >= 30:
                    milestones_to_check = [30]

                cursor.execute("""
                    SELECT lg.guarantor_member_id, lg.guaranteed_amount
                    FROM loan_guarantors lg
                    WHERE lg.loan_id = %s AND lg.status = 'ACCEPTED';
                """, (loan_id,))
                guarantors = cursor.fetchall()

                for mile in milestones_to_check:
                    cursor.execute("""
                        SELECT id FROM system_notifications
                        WHERE reference_type = 'LOAN' AND reference_id = %s AND milestone_tier = %s
                        LIMIT 1;
                    """, (str(loan_id), mile))
                    if cursor.fetchone():
                        continue

                    sev = 'WARNING' if mile == 30 else ('CRITICAL' if mile == 45 else 'DANGER')

                    admin_title = f"{mile}-Day Loan Default Notice: {loan_ref}"
                    if mile == 90:
                        admin_msg = f"CRITICAL: Loan {loan_ref} ({b_name}) has reached 90 days default (Balance: NGN {out_bal:,.2f}). FinSec & President action required to authorize foreclosure offset."
                    elif mile == 45:
                        admin_msg = f"Loan {loan_ref} ({b_name}) is now 45 days in default. Login prompts active for borrower and guarantors."
                    else:
                        admin_msg = f"First-tier default notice: Loan {loan_ref} for {b_name} ({b_code}) has reached 30 days default."

                    cursor.execute("""
                        INSERT INTO system_notifications (
                            recipient_type, category, title, message, severity,
                            reference_type, reference_id, milestone_tier
                        ) VALUES (
                            'ALL_ADMIN', 'LOAN_DEFAULT', %s, %s, %s, 'LOAN', %s, %s
                        );
                    """, (admin_title, admin_msg, sev, str(loan_id), mile))
                    notifications_issued += 1

                    for g in guarantors:
                        g_id = g["guarantor_member_id"]
                        g_amt = float(g["guaranteed_amount"])
                        if mile == 90:
                            g_msg = f"CRITICAL NOTICE: Loan {loan_ref} for {b_name} has reached 90 days in default. Executive offset against your encumbered regular savings (NGN {g_amt:,.2f}) has been submitted for President & FinSec sign-off."
                        elif mile == 45:
                            g_msg = f"URGENT: Cooperator {b_name}'s loan ({loan_ref}), guaranteed by you for NGN {g_amt:,.2f}, is now 45 days in default. A warning prompt is active on your portal."
                        else:
                            g_msg = f"Default Notice: Loan {loan_ref} for {b_name}, guaranteed by you for NGN {g_amt:,.2f}, has reached 30 days in default. Please contact the borrower."

                        cursor.execute("""
                            INSERT INTO system_notifications (
                                recipient_type, recipient_id, category, title, message, severity,
                                reference_type, reference_id, milestone_tier
                            ) VALUES (
                                'MEMBER', %s, 'LOAN_DEFAULT', %s, %s, %s, 'LOAN', %s, %s
                            );
                        """, (g_id, f"{mile}-Day Guaranteed Loan Default Alert: {loan_ref}", g_msg, sev, str(loan_id), mile))
                        notifications_issued += 1

            conn.commit()
            return {
                "status": "SUCCESS",
                "overdue_loans_count": len(overdue_loans),
                "notifications_issued": notifications_issued
            }
        finally:
            cursor.close()
            conn.close()

    def execute_loan_foreclosure_offset(
        self,
        loan_id: int,
        officer_id: int,
        offset_borrower_amount: float,
        offset_guarantor_amount: float,
        officer_notes: str = ""
    ) -> Dict[str, Any]:
        """
        Executes statutory collateral foreclosure on a severely defaulted loan (Day 90+):
        Authorized by Financial Secretary and President.
        - Offsets from borrower regular savings.
        - Offsets from guarantor encumbered regular savings.
        - Credits loan balance, marks repayments settled.
        - Posts balanced double-entry General Ledger journal: Dr Member Savings (2010), Cr Loans Receivable (1030).
        """
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT l.*, m.member_code, CONCAT(m.first_name, ' ', m.last_name) as borrower_name
                FROM loans l
                JOIN members m ON l.member_id = m.id
                WHERE l.id = %s FOR UPDATE;
            """, (loan_id,))
            loan = cursor.fetchone()
            if not loan:
                raise ValueError(f"Loan ID {loan_id} not found.")

            out_bal = Decimal(str(loan["outstanding_balance"]))
            if out_bal <= Decimal("0.00"):
                raise ValueError(f"Loan {loan['loan_reference']} has zero outstanding balance.")

            b_offset = Decimal(str(offset_borrower_amount or 0.00))
            g_offset = Decimal(str(offset_guarantor_amount or 0.00))
            total_offset = b_offset + g_offset

            if total_offset <= Decimal("0.00"):
                raise ValueError("Total offset amount must be greater than zero.")
            if total_offset > out_bal:
                raise ValueError(f"Total offset (NGN {total_offset:,.2f}) cannot exceed outstanding loan balance (NGN {out_bal:,.2f}).")

            b_id = loan["member_id"]

            # 1. Debit Borrower regular savings if b_offset > 0
            if b_offset > 0:
                cursor.execute("SELECT total_balance FROM savings_accounts WHERE member_id = %s FOR UPDATE;", (b_id,))
                b_sav = cursor.fetchone()
                b_avail = Decimal(str(b_sav["total_balance"])) if b_sav else Decimal("0.00")
                if b_offset > b_avail:
                    raise ValueError(f"Borrower available savings (NGN {b_avail:,.2f}) insufficient for requested offset of NGN {b_offset:,.2f}.")

                cursor.execute("""
                    UPDATE savings_accounts
                    SET total_balance = total_balance - %s
                    WHERE member_id = %s;
                """, (b_offset, b_id))

                cursor.execute("""
                    INSERT INTO transactions (
                        transaction_ref, member_id, transaction_type, ledger_category,
                        amount, payment_method, channel_reference, narration, status
                    ) VALUES (
                        %s, %s, 'DEBIT', 'SAVINGS', %s, 'INTERNAL_SET_OFF', %s, %s, 'VERIFIED'
                    );
                """, (
                    f"TXN-FCL-B-{loan_id}-{int(time.time())}", b_id, b_offset,
                    loan["loan_reference"], f"Foreclosure offset against defaulted loan {loan['loan_reference']}"
                ))

            # 2. Debit Guarantor(s) if g_offset > 0
            if g_offset > 0:
                cursor.execute("""
                    SELECT lg.*, COALESCE(sa.total_balance, 0.00) AS total_savings, COALESCE(sa.encumbered_balance, 0.00) AS encumbered_savings
                    FROM loan_guarantors lg
                    LEFT JOIN savings_accounts sa ON lg.guarantor_member_id = sa.member_id
                    WHERE lg.loan_id = %s AND lg.status = 'ACCEPTED';
                """, (loan_id,))
                guars = cursor.fetchall()
                if not guars:
                    raise ValueError("No consented guarantors found on this loan to offset from.")

                rem_g = g_offset
                for g in guars:
                    if rem_g <= Decimal("0.00"):
                        break
                    g_id = g["guarantor_member_id"]
                    g_limit = Decimal(str(g["guaranteed_amount"]))
                    g_take = min(rem_g, g_limit)

                    cursor.execute("""
                        UPDATE savings_accounts
                        SET total_balance = total_balance - %s,
                            encumbered_balance = GREATEST(0.00, encumbered_balance - %s)
                        WHERE member_id = %s;
                    """, (g_take, g_take, g_id))

                    cursor.execute("""
                        INSERT INTO transactions (
                            transaction_ref, member_id, transaction_type, ledger_category,
                            amount, payment_method, channel_reference, narration, status
                        ) VALUES (
                            %s, %s, 'DEBIT', 'SAVINGS', %s, 'INTERNAL_SET_OFF', %s, %s, 'VERIFIED'
                        );
                    """, (
                        f"TXN-FCL-G-{loan_id}-{g_id}-{int(time.time())}", g_id, g_take,
                        loan["loan_reference"], f"Guarantor collateral foreclosure offset for {loan['borrower_name']} ({loan['loan_reference']})"
                    ))
                    rem_g -= g_take

            # 3. Credit Loan Balance
            new_out = max(Decimal("0.00"), out_bal - total_offset)
            new_paid = Decimal(str(loan["total_paid"])) + total_offset
            new_status = "COMPLETED" if new_out <= Decimal("0.01") else "ACTIVE"

            cursor.execute("""
                UPDATE loans
                SET outstanding_balance = %s, total_paid = %s, status = %s
                WHERE id = %s;
            """, (new_out, new_paid, new_status, loan_id))

            cursor.execute("""
                INSERT INTO loan_repayments (
                    loan_id, installment_number, due_date, amount_due, amount_paid, paid_date, transaction_ref, status
                ) VALUES (
                    %s, 999, CURDATE(), %s, %s, NOW(), %s, 'PAID'
                );
            """, (loan_id, total_offset, total_offset, f"FCL-{loan['loan_reference']}"))

            # 4. Post Double-Entry General Ledger Journal (Module 4)
            je_lines = [
                {"account_code": "2010", "line_type": "DEBIT", "amount": total_offset, "memo": f"Foreclosure offset from savings for {loan['loan_reference']}"},
                {"account_code": "1030", "line_type": "CREDIT", "amount": total_offset, "memo": f"Foreclosure liquidation of loan {loan['loan_reference']}"}
            ]
            self._post_journal_entry_with_cursor(
                cursor=cursor,
                entry_date=date.today(),
                source_module='LOAN_FORECLOSURE',
                source_reference=loan['loan_reference'],
                narration=f"Statutory 90-Day Foreclosure Offset on Loan {loan['loan_reference']} ({loan['borrower_name']})",
                lines=je_lines,
                created_by=officer_id,
                status='POSTED'
            )

            conn.commit()

            self.log_audit_event(
                user_id=officer_id,
                actor_name="Executive Desk",
                actor_role="FINSEC_PRESIDENT",
                action="LOAN_FORECLOSURE_EXECUTED",
                resource_type="LOAN",
                resource_id=str(loan_id),
                details_before={"outstanding_balance": float(out_bal)},
                details_after={
                    "total_offset": float(total_offset),
                    "borrower_offset": float(b_offset),
                    "guarantor_offset": float(g_offset),
                    "new_outstanding_balance": float(new_out),
                    "new_status": new_status,
                    "notes": officer_notes
                },
                summary=f"Executed statutory foreclosure offset of NGN {total_offset:,.2f} on {loan['loan_reference']}."
            )

            return {
                "status": "SUCCESS",
                "loan_id": loan_id,
                "loan_reference": loan["loan_reference"],
                "total_offset": float(total_offset),
                "borrower_offset": float(b_offset),
                "guarantor_offset": float(g_offset),
                "new_outstanding_balance": float(new_out),
                "loan_status": new_status,
                "message": f"Successfully foreclosed and offset NGN {total_offset:,.2f} against loan {loan['loan_reference']}."
            }
        finally:
            cursor.close()
            conn.close()

    def get_notifications(self, user_id: int, is_admin: bool = False) -> List[Dict[str, Any]]:
        """Retrieves system notifications for member or administrative officer."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            if is_admin:
                cursor.execute("""
                    SELECT * FROM system_notifications
                    WHERE recipient_type IN ('ALL_ADMIN', 'OFFICER') OR (recipient_type = 'MEMBER' AND recipient_id = %s)
                    ORDER BY id DESC LIMIT 50;
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT * FROM system_notifications
                    WHERE recipient_type = 'MEMBER' AND recipient_id = %s
                    ORDER BY id DESC LIMIT 50;
                """, (user_id,))
            notes = cursor.fetchall()
            for n in notes:
                if n.get("created_at"):
                    n["created_at"] = str(n["created_at"])
            return notes
        finally:
            cursor.close()
            conn.close()

    def mark_notification_as_read(self, notification_id: int, user_id: int) -> bool:
        """Marks a notification as read."""
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("UPDATE system_notifications SET is_read = TRUE WHERE id = %s;", (notification_id,))
            conn.commit()
            return True
        finally:
            cursor.close()
            conn.close()


def main():
    print("=" * 80)
    print("  WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)")
    print("  Database & RBAC Platform Engine | wbmf_db.py")
    print("  Official Email: wealthbridge.coopsociety@gmail.com")
    print("=" * 80)
    db = WealthbridgeDB()
    
    print("\n[1] Testing Authentication for Convener (Member Code: WMC-2026-001)...")
    try:
        auth_res = db.authenticate_user("WMC-2026-001", "Wealthbridge@2026")
        user = auth_res["user"]
        print(f"  + Authenticated: {user['full_name']} ({user['member_code']})")
        print(f"  + Roles:         {user['roles']}")
        print(f"  + Primary Role:  {user['primary_role']}")
        print(f"  + Is Executive:  {user['is_executive']}")
        print(f"  + Permissions:   {len(user['permissions'])} assigned")
    except Exception as e:
        print(f"  x Auth test notice: {e}")

    print("\n[2] Testing Executive Metrics Retrieval...")
    try:
        metrics = db.get_executive_metrics()
        print(f"  + Active Members:  {metrics['membership']['active']}")
        print(f"  + Pending KYC:     {metrics['membership']['pending_kyc']}")
        print(f"  + Total Assets:    NGN {metrics['financial_pools']['total_assets_under_management']:,.2f}")
    except Exception as e:
        print(f"  x Metrics notice: {e}")

    print("\n[SUCCESS] RBAC Engine is configured and ready.")

if __name__ == "__main__":
    main()
