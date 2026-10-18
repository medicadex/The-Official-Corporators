"""
=============================================================================
WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
RESTful API SERVICE & RBAC GATEWAY (wbmf_api.py)
-----------------------------------------------------------------------------
Built with FastAPI & MySQL Connector
Statutory Jurisdiction: Lagos State Cooperative Societies Law (Cap C15)
Official Secretariat Contact: wealthbridge.coopsociety@gmail.com
Interactive Swagger Docs: http://127.0.0.1:8088/docs
=============================================================================
"""

import os
import secrets
import time
import shutil
import csv
import io
from threading import Lock
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, date
import requests
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from wbmf_db import WealthbridgeDB
from advice_pdf_service import AdvicePdfService
from report_pdf_service import ReportPdfService
from id_card_pdf_service import IdCardPdfService

app = FastAPI(
    title="Wealthbridge Cooperative API & RBAC Gateway (WMC)",
    description="Official Backend API & Governance Portal for Wealthbridge Multipurpose Cooperative Society Limited",
    version="1.2.0",
    contact={
        "name": "Wealthbridge Secretariat",
        "email": "wealthbridge.coopsociety@gmail.com"
    }
)

# Enable CORS for frontend web integration (supports file://, localhost, 127.0.0.1 and custom hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = WealthbridgeDB()
bearer_scheme = HTTPBearer(auto_error=False)
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "28800"))
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "900"))
_SESSIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wbmf_sessions.json")

def _load_sessions() -> Dict[str, Dict[str, Any]]:
    if os.path.exists(_SESSIONS_FILE):
        try:
            with open(_SESSIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                now = time.time()
                return {k: v for k, v in data.items() if v.get("expires_at", 0) > now}
        except Exception:
            return {}
    return {}

def _save_sessions() -> None:
    try:
        with open(_SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(_sessions, f)
    except Exception:
        pass

_sessions: Dict[str, Dict[str, Any]] = _load_sessions()
_login_attempts: Dict[str, List[float]] = {}
_auth_lock = Lock()

# -----------------------------------------------------------------------------
# VERIFYME NG INTEGRATION (Bank List & NUBAN Account Name Resolution)
# -----------------------------------------------------------------------------
VERIFYME_API_KEY = os.getenv("VERIFYME_API_KEY", "")
VERIFYME_BASE_URL = os.getenv("VERIFYME_BASE_URL", "https://vapi.verifyme.ng/v1")
VERIFYME_TIMEOUT = 30


def _verifyme_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {VERIFYME_API_KEY}",
        "Accept": "application/json",
    }


def _fetch_verifyme_banks() -> List[Dict[str, Any]]:
    """
    Fetches the comprehensive list of Nigerian banks & microfinance banks
    from VerifyMe. Merges both the /banks and /bvn-nuban/banks endpoints
    to ensure commercial banks AND microfinance banks are included, then
    returns them sorted alphabetically by name.
    """
    if not VERIFYME_API_KEY or VERIFYME_API_KEY == "your_verifyme_api_key_here":
        try:
            from paystack_service import PaystackService
            return PaystackService.get_banks()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment gateway bank list is currently unavailable.",
            )

    merged: Dict[str, Dict[str, Any]] = {}

    # 1. Primary bank list (commercial banks & active institutions)
    try:
        resp = requests.get(
            f"{VERIFYME_BASE_URL}/banks",
            headers=_verifyme_headers(),
            timeout=VERIFYME_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            for bank in data:
                code = str(bank.get("code", "")).strip()
                if not code:
                    continue
                merged[code] = {
                    "name": bank.get("name", ""),
                    "slug": bank.get("slug", ""),
                    "code": code,
                    "active": bank.get("active", True),
                    "type": "commercial",
                }
    except requests.RequestException as e:
        print(f"[VerifyMe] Warning: could not fetch /banks: {e}")

    # 2. NUBAN bank list (includes microfinance banks & other NUBAN-enabled institutions)
    try:
        resp = requests.get(
            f"{VERIFYME_BASE_URL}/bvn-nuban/banks",
            headers=_verifyme_headers(),
            timeout=VERIFYME_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            for bank in data:
                code = str(bank.get("code", "")).strip()
                if not code:
                    continue
                name = bank.get("name", "")
                is_mfb = "microfinance" in name.lower() or "mfb" in name.lower()
                if code in merged:
                    # Keep existing but upgrade type detection
                    existing = merged[code]
                    if is_mfb:
                        existing["type"] = "microfinance"
                else:
                    merged[code] = {
                        "name": name,
                        "slug": "",
                        "code": code,
                        "active": True,
                        "type": "microfinance" if is_mfb else "other",
                    }
    except requests.RequestException as e:
        print(f"[VerifyMe] Warning: could not fetch /bvn-nuban/banks: {e}")

    banks_list = list(merged.values())
    banks_list.sort(key=lambda b: b["name"].lower())
    return banks_list


def _fetch_verifyme_account_name(bank_code: str, account_number: str) -> Dict[str, Any]:
    """
    Resolves the account holder name for a given NUBAN account number
    and bank code via VerifyMe's account details endpoint.
    """
    if not VERIFYME_API_KEY or VERIFYME_API_KEY == "your_verifyme_api_key_here":
        try:
            from paystack_service import PaystackService
            res = PaystackService.resolve_account_number(account_number=account_number, bank_code=bank_code)
            return {
                "account_name": res.get("account_name", ""),
                "account_number": account_number,
                "firstname": "",
                "lastname": "",
                "middlename": "",
                "bank_code": bank_code,
            }
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    bank_code = str(bank_code).strip()
    account_number = str(account_number).strip()

    if not bank_code or not account_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both bank_code and account_number are required.",
        )

    if len(account_number) != 10 or not account_number.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account number must be exactly 10 digits.",
        )

    try:
        resp = requests.get(
            f"{VERIFYME_BASE_URL}/banks/{bank_code}/accounts/{account_number}",
            headers=_verifyme_headers(),
            timeout=VERIFYME_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            return {
                "account_name": data.get("accountName", ""),
                "account_number": data.get("accountNumber", account_number),
                "firstname": data.get("firstname", ""),
                "lastname": data.get("lastname", ""),
                "middlename": data.get("middlename", ""),
                "bank_code": bank_code,
            }
        elif resp.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found for the provided bank and account number.",
            )
        elif resp.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="VerifyMe API authentication failed. Check your API key.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"VerifyMe service error: {resp.status_code} - {resp.text[:200]}",
            )
    except HTTPException:
        raise
    except requests.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not reach VerifyMe service: {str(e)[:200]}",
        )


def _client_key(request: Request, identifier: str = "") -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{identifier.strip().lower()}"


def _enforce_login_rate_limit(request: Request, identifier: str) -> None:
    key = _client_key(request, identifier)
    now = time.time()
    with _auth_lock:
        attempts = [stamp for stamp in _login_attempts.get(key, []) if now - stamp < LOGIN_WINDOW_SECONDS]
        _login_attempts[key] = attempts
        if len(attempts) >= MAX_LOGIN_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many sign-in attempts. Please wait before trying again.",
            )


def _record_failed_login(request: Request, identifier: str) -> None:
    key = _client_key(request, identifier)
    with _auth_lock:
        _login_attempts.setdefault(key, []).append(time.time())


def _create_session(member_id: Any) -> str:
    token = secrets.token_urlsafe(48)
    with _auth_lock:
        _sessions[token] = {"member_id": member_id, "expires_at": time.time() + SESSION_TTL_SECONDS}
        _save_sessions()
    return token


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)) -> Dict[str, Any]:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")

    with _auth_lock:
        session = _sessions.get(credentials.credentials)
        if not session or session["expires_at"] <= time.time():
            _sessions.pop(credentials.credentials, None)
            _save_sessions()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Your session has expired. Please sign in again.")

    user = db.get_member_authorization_context(session["member_id"])
    if not user or user["membership_status"] not in ("ACTIVE", "SYSTEM_ADMINISTRATOR", "PENDING_KYC"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not active.")
    return user


def require_permission(permission: str) -> Callable:
    def dependency(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if permission not in user["permissions"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not authorized for this action.")
        return user
    return dependency

# -----------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# -----------------------------------------------------------------------------
class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Member Code (e.g. WMC-2026-001), Registered Email, or Phone")
    password: str = Field(..., description="Access Password")

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="Current Password")
    new_password: str = Field(..., min_length=12, description="New Secure Password (Min 12 chars)")

class RegistrationRequest(BaseModel):
    first_name: str = Field(..., min_length=2, description="First Name")
    last_name: str = Field(..., min_length=2, description="Last Name")
    other_names: Optional[str] = Field(default=None, description="Other Names / Middle Name")
    email: str = Field(..., min_length=5, description="Official or Personal Email Address")
    password: Optional[str] = Field(default="Wealthbridge@2026", description="Account Password")
    phone: str = Field(..., min_length=7, description="Active WhatsApp / Phone Number")
    gender: Optional[str] = Field(default="MALE", description="Gender (MALE or FEMALE)")
    residential_address: str = Field(..., min_length=2, description="Residential Address in Lagos State")
    employment_status: Optional[str] = Field(default="SALARY_EARNER", description="Employment Status")
    contribution_tier: Optional[str] = Field(default="STANDARD", description="Contribution Tier (STANDARD, PLUS, PREMIUM)")
    identification_type: Optional[str] = Field(default="NIN", description="Identification Document Type")
    identification_number: Optional[str] = Field(default=None, description="NIN or ID Number")

class ContributionRequest(BaseModel):
    total_amount: float = Field(..., ge=10000.0, description="Monthly remittance amount (Min NGN 10,000)")
    payment_method: str = Field(default="POLARIS_BANK_TRANSFER", description="Payment channel")
    channel_reference: str = Field(..., description="Bank transaction ref / teller number")

class OnboardingRequest(BaseModel):
    member_id: int = Field(..., description="Target Member ID in PENDING_KYC")
    payment_method: str = Field(default="POLARIS_BANK_TRANSFER")
    channel_reference: str = Field(..., description="Bank payment reference")
    pay_shares_upfront: bool = Field(default=True, description="Pay N5,000 minimum shares upfront")
    first_month_contribution: float = Field(default=10000.0, description="Optional Month 1 contribution")

class ApproveMemberRequest(BaseModel):
    member_id: int = Field(..., description="Member ID to approve")

class RejectMemberRequest(BaseModel):
    member_id: int = Field(..., description="Member ID to reject/suspend")
    reason: str = Field(..., description="Statutory or documentation reason for rejection")

class IssueFineRequest(BaseModel):
    member_id: int = Field(..., description="Member ID being fined")
    infraction_type: str = Field(..., description="Infraction code (e.g. LATE_MONTHLY_REMITTANCE)")
    fine_amount: float = Field(..., gt=0, description="Fine amount in NGN")
    reason: str = Field(..., description="Factual explanation and bye-law reference")

class NextOfKinSchema(BaseModel):
    full_name: str = Field(..., description="Full Name of Beneficiary")
    relationship: str = Field(default="SPOUSE", description="Relationship (e.g. SPOUSE, CHILD, PARENT, SIBLING)")
    phone: str = Field(..., description="Contact phone number")
    email: Optional[str] = Field(default=None, description="Email address")
    residential_address: str = Field(..., description="Residential address")
    allocation_percentage: float = Field(default=100.0, description="Inheritance/Benefit allocation percentage")

class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    other_names: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    date_of_birth: Optional[str] = None
    employment_status: Optional[str] = None
    employer_or_business_name: Optional[str] = None
    occupation: Optional[str] = None
    monthly_income_verified: Optional[float] = None
    identification_type: Optional[str] = None
    identification_number: Optional[str] = None
    national_id_nin: Optional[str] = None
    passport_photo: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_account_name: Optional[str] = None
    bvn: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    phone_number: Optional[str] = None
    residential_address: Optional[str] = None
    next_of_kin: Optional[NextOfKinSchema] = None
    next_of_kin_name: Optional[str] = None
    next_of_kin_relationship: Optional[str] = None
    next_of_kin_phone: Optional[str] = None
    next_of_kin_address: Optional[str] = None

class ApproveContactChangeRequest(BaseModel):
    member_id: int = Field(..., description="Member ID")

class RejectContactChangeRequest(BaseModel):
    member_id: int = Field(..., description="Member ID")
    reason: str = Field(default="Failed verification", description="Rejection reason")

class AdminCreateMemberRequest(BaseModel):
    first_name: str = Field(..., min_length=2, description="First Name")
    last_name: str = Field(..., min_length=2, description="Last Name")
    other_names: Optional[str] = Field(default=None, description="Middle / Other Names")
    email: str = Field(..., min_length=5, description="Email Address")
    phone: str = Field(..., min_length=9, description="Phone Number")
    gender: Optional[str] = Field(default="MALE", description="Gender")
    marital_status: Optional[str] = Field(default="SINGLE", description="Marital Status")
    residential_address: Optional[str] = Field(default="Lagos State, Nigeria", description="Residential Address")
    employment_status: Optional[str] = Field(default="SALARY_EARNER", description="Employment Status")
    employer_or_business_name: Optional[str] = Field(default=None, description="Employer or Business Name")
    contribution_tier: Optional[str] = Field(default="STANDARD", description="Contribution Tier")
    status: Optional[str] = Field(default="ACTIVE", description="Membership Status")
    identification_type: Optional[str] = Field(default="NIN", description="Identification Type")
    identification_number: Optional[str] = Field(default=None, description="NIN Number")
    bank_name: Optional[str] = Field(default=None, description="Bank Name")
    bank_account_number: Optional[str] = Field(default=None, description="Bank Account Number")
    bank_account_name: Optional[str] = Field(default=None, description="Bank Account Name")
    bvn: Optional[str] = Field(default=None, description="Bank Verification Number")
    nok_name: Optional[str] = Field(default=None, description="Next of Kin Full Name")
    nok_relationship: Optional[str] = Field(default=None, description="Next of Kin Relationship")
    nok_phone: Optional[str] = Field(default=None, description="Next of Kin Phone")
    nok_address: Optional[str] = Field(default=None, description="Next of Kin Residential Address")

class AdminUpdateBiodataRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    other_names: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    residential_address: Optional[str] = None
    employment_status: Optional[str] = None
    employer_or_business_name: Optional[str] = None
    contribution_tier: Optional[str] = None
    status: Optional[str] = None
    identification_type: Optional[str] = None
    identification_number: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_account_name: Optional[str] = None
    bvn: Optional[str] = None
    nok_name: Optional[str] = None
    nok_relationship: Optional[str] = None
    nok_phone: Optional[str] = None
    nok_address: Optional[str] = None

class CreateTargetSavingsRequest(BaseModel):
    target_type: str = Field(..., description="Target category: BIRTHDAY, CHRISTMAS, ILEYA, BUILDING, PILGRIMAGE, EDUCATION, OTHERS")
    title: Optional[str] = Field(default="", description="Descriptive label for the target savings ledger")
    target_amount: float = Field(..., gt=0, description="Financial goal target amount in NGN")
    maturity_date: str = Field(..., description="Proposed maturity date (YYYY-MM-DD)")
    initial_deposit: Optional[float] = Field(default=0.0, ge=0, description="Initial deposit top-up amount")
    auto_save_amount: Optional[float] = Field(default=0.0, ge=0, description="Optional monthly recurring allocation")
    payment_method: Optional[str] = Field(default="POLARIS_BANK_TRANSFER", description="Payment channel")

class DepositTargetSavingsRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to deposit into target ledger")
    payment_method: Optional[str] = Field(default="POLARIS_BANK_TRANSFER", description="Payment method")
    channel_reference: Optional[str] = Field(default=None, description="Bank / gateway reference")
    narration: Optional[str] = Field(default=None, description="Custom deposit narration")

class WithdrawTargetSavingsRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to withdraw upon maturity")
    bank_name: Optional[str] = Field(default=None, description="Destination commercial bank name")
    account_number: Optional[str] = Field(default=None, description="Destination 10-digit account number")
    account_name: Optional[str] = Field(default=None, description="Destination account holder name")

class InitializePaymentRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in Naira")
    purpose: str = Field(default="SAVINGS", description="Payment purpose: SAVINGS, TARGET_SAVINGS, SHARE_CAPITAL, LOAN_REPAYMENT")
    target_id: Optional[int] = Field(default=None, description="Target savings ID if purpose is TARGET_SAVINGS")
    callback_url: Optional[str] = Field(default=None, description="Redirect URL after payment")

class DistributePaymentRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in Naira to distribute")
    payment_method: Optional[str] = Field(default="POLARIS_BANK_TRANSFER", description="Payment channel")
    payment_reference: Optional[str] = Field(default=None, description="Bank / gateway payment reference")
    narration: Optional[str] = Field(default=None, description="Remittance narration")

class RevisePaymentAdviceRequest(BaseModel):
    amount_fines: Optional[float] = None
    amount_registration_fee: Optional[float] = None
    amount_loan_repayment: Optional[float] = None
    amount_welfare: Optional[float] = None
    amount_share_capital: Optional[float] = None
    amount_regular_savings: Optional[float] = None
    amount_target_savings: Optional[float] = None
    amount_arrears: Optional[float] = None
    admin_notes: Optional[str] = None

class UpdateSystemConfigRequest(BaseModel):
    config_value: str = Field(..., min_length=1, description="New value for statutory parameter")

class CreateRoleRequest(BaseModel):
    role_code: str = Field(..., min_length=2, description="Unique uppercase code for role (e.g. CREDIT_ANALYST)")
    role_name: str = Field(..., min_length=2, description="Human readable name")
    description: Optional[str] = Field(default=None, description="Role purpose and description")
    permission_keys: Optional[List[str]] = Field(default_factory=list, description="List of granular permission keys")
    permission_codes: Optional[List[str]] = Field(default=None, description="Alias for permission_keys")

class UpdateRolePermissionsRequest(BaseModel):
    permission_keys: List[str] = Field(..., description="List of granular permission keys to bind to this role")

class UpdateRoleRequest(BaseModel):
    role_name: Optional[str] = Field(default=None, description="Human readable name")
    description: Optional[str] = Field(default=None, description="Role purpose and description")
    permission_keys: Optional[List[str]] = Field(default=None, description="List of granular permission keys")
    permission_codes: Optional[List[str]] = Field(default=None, description="Alias for permission_keys")

class AssignRoleRequest(BaseModel):
    role_id: int = Field(..., description="Role ID to grant to member")
    appointment_notes: Optional[str] = Field(default=None, description="Appointment narration")
    assigned_by_id: Optional[Any] = Field(default=None, description="ID of appointing officer")

class GuarantorItem(BaseModel):
    guarantor_member_id: int = Field(..., description="Member ID of guarantor cooperator")
    guaranteed_amount: float = Field(..., gt=0, description="Amount guaranteed in NGN")

class ApplyLoanRequest(BaseModel):
    principal_amount: float = Field(..., gt=0, description="Principal loan amount in NGN")
    tenure_months: int = Field(..., ge=1, le=36, description="Tenure in months (1-36)")
    purpose_narration: Optional[str] = Field(default=None, description="Substantive business/welfare purpose")
    product_id: Optional[int] = Field(default=1, description="Loan product ID")
    guarantors: Optional[List[GuarantorItem]] = Field(default_factory=list, description="List of guarantor cooperators")

class ReviewLoanRequest(BaseModel):
    action: str = Field(..., description="Review action: APPROVE or DECLINE")
    comments: Optional[str] = Field(default=None, description="Officer notes or mandatory decline reason")
    is_president_override: Optional[bool] = Field(default=False, description="Presidential supreme override flag")

class SubmitLoanAppealRequest(BaseModel):
    appeal_comments: str = Field(..., min_length=10, description="Comprehensive appeal statement")
    attached_document_path: Optional[str] = Field(default=None, description="Path to uploaded supporting evidence")
    document_name: Optional[str] = Field(default=None, description="Original filename")
    document_mime_type: Optional[str] = Field(default=None, description="MIME type")

class ResolveLoanAppealRequest(BaseModel):
    action: str = Field(..., description="REINSTATE or UPHOLD")
    review_response: str = Field(..., min_length=5, description="Executive justification and finding")

class ManualBankPaymentRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount paid in NGN")
    payment_date: str = Field(..., description="Date of payment (YYYY-MM-DD)")
    payment_reference: str = Field(..., min_length=3, description="Bank reference or teller number")
    narration: Optional[str] = Field(default=None, description="Remittance narration")
    receipt_file_path: Optional[str] = Field(default=None, description="Path or URL to uploaded payment receipt")
    receipt_mime_type: Optional[str] = Field(default=None, description="Receipt MIME type")

class VerifyManualPaymentRequest(BaseModel):
    verification_notes: Optional[str] = Field(default=None, description="Reconciliation notes against bank statement")
    distribution_override: Optional[Dict[str, float]] = Field(default=None, description="Optional custom ledger allocation")

class RejectManualPaymentRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=5, description="Factual reason for rejection")

class DirectMemberCreditRequest(BaseModel):
    member_id: int = Field(..., description="Member ID to credit")
    amount: float = Field(..., gt=0, description="Amount in NGN")
    credit_category: str = Field(..., description="SAVINGS, SHARE_CAPITAL, WELFARE, or LOAN_REPAYMENT")
    narration: str = Field(..., min_length=5, description="Mandatory statutory justification")

class ModifyAdviceRequest(BaseModel):
    scope: str = Field(default="THIS_MONTH_ONLY", description="THIS_MONTH_ONLY or PERMANENT_COMMITMENT")
    statutory_justification: str = Field(..., min_length=10, description="Mandatory justification note")
    amount_fines: Optional[float] = None
    amount_registration_fee: Optional[float] = None
    amount_loan_repayment: Optional[float] = None
    amount_welfare: Optional[float] = None
    amount_share_capital: Optional[float] = None
    amount_regular_savings: Optional[float] = None
    amount_target_savings: Optional[float] = None
    amount_arrears: Optional[float] = None

class GuarantorConsentDecisionRequest(BaseModel):
    decision: str = Field(..., description="ACCEPT or DECLINE")
    comments: Optional[str] = Field(default=None, description="Cooperator consent comment or reason for decline")

class MemberExitRequestPayload(BaseModel):
    exit_type: str = Field(default="VOLUNTARY_WITHDRAWAL", description="VOLUNTARY_WITHDRAWAL, DEATH_ESTATE_SETTLEMENT, or EXPULSION")
    reason: Optional[str] = Field(default=None, description="Statutory reason for exit or notice details")
    supporting_doc_url: Optional[str] = Field(default=None, description="URL or path to uploaded notice letter or death certificate")
    nok_claimant: Optional[Dict[str, Any]] = Field(default=None, description="Next of kin claimant details for estate settlement")

class ApproveExitSettlementPayload(BaseModel):
    refund_payment_ref: Optional[str] = Field(default=None, description="Electronic payout reference or bank transfer ref")

class ForeclosureOffsetPayload(BaseModel):
    offset_borrower_amount: float = Field(default=0.0, ge=0, description="Amount to offset from borrower available regular savings")
    offset_guarantor_amount: float = Field(default=0.0, ge=0, description="Amount to offset from guarantor encumbered regular savings")
    officer_notes: Optional[str] = Field(default="", description="Executive justification and foreclosure authorization notes")

# Module 4 & 5 Accounting and Dividend Models
class JournalLinePayload(BaseModel):
    account_code: str = Field(..., description="Chart of Accounts code, e.g. 1010, 2010, 4020")
    line_type: str = Field(..., description="DEBIT or CREDIT")
    amount: float = Field(..., gt=0, description="Monetary line amount in NGN")
    memo: Optional[str] = Field(default=None, description="Optional line memorandum")

class SubmitJournalEntryPayload(BaseModel):
    entry_date: str = Field(..., description="Journal effective date (YYYY-MM-DD)")
    narration: str = Field(..., min_length=5, description="Full explanation and audit rationale")
    lines: List[JournalLinePayload] = Field(..., min_items=2, description="Balanced double-entry journal lines")
    supporting_doc_url: Optional[str] = Field(default=None, description="URL or path to uploaded voucher or statement")

class ApproveJournalEntryPayload(BaseModel):
    action: str = Field(default="APPROVE", description="APPROVE or REJECT")
    rejection_reason: Optional[str] = Field(default=None, description="Reason if rejected")

class SimulateDividendPayload(BaseModel):
    period_name: str = Field(..., min_length=3, description="Descriptive title of distribution period")
    financial_year_start: str = Field(..., description="Financial year start (YYYY-MM-DD)")
    financial_year_end: str = Field(..., description="Financial year end (YYYY-MM-DD)")
    net_surplus: Optional[float] = Field(default=None, description="Optional manual override of net surplus")
    statutory_reserve_pct: float = Field(default=50.00, ge=50.00, le=100.00, description="Mandatory min 50% statutory reserve deduction")
    weight_share_pct: float = Field(default=60.00, ge=0.00, le=100.00, description="Weighting allocated to Share Capital pool")
    weight_savings_pct: float = Field(default=40.00, ge=0.00, le=100.00, description="Weighting allocated to Regular Savings pool")
    weight_patronage_pct: float = Field(default=0.00, ge=0.00, le=100.00, description="Weighting allocated to Loan Patronage pool")
    min_shares: int = Field(default=5, ge=1, description="Minimum share units required to qualify (default 5)")
    min_months: int = Field(default=6, ge=0, description="Minimum months active membership tenure (default 6)")
    disqualify_arrears: bool = Field(default=True, description="Exclude members with overdue loans or unpaid fines from denominator")

class SaveDividendPayload(BaseModel):
    simulation_data: Dict[str, Any] = Field(..., description="Complete output from /api/dividends/simulate")

class UpdateDividendPreferencePayload(BaseModel):
    payout_preference: str = Field(..., description="SAVINGS_CREDIT or BANK_TRANSFER")



# -----------------------------------------------------------------------------
# 1. AUTHENTICATION & RBAC ENDPOINTS
# -----------------------------------------------------------------------------
@app.post("/api/auth/login")
def login(payload: LoginRequest, request: Request):
    """
    Authenticates a member or executive officer.
    Returns session token, full user profile, assigned RBAC roles, and granular permissions.
    """
    try:
        _enforce_login_rate_limit(request, payload.identifier)
        try:
            db.scan_and_process_loan_defaults()
        except Exception:
            pass
        auth_data = db.authenticate_user(payload.identifier, payload.password)
        auth_data["token"] = _create_session(auth_data["user"]["id"])
        auth_data["login_prompts"] = db.get_login_prompts_for_user(
            auth_data["user"]["id"],
            auth_data["user"]["member_code"],
            auth_data["user"].get("roles", [])
        )
        return {
            "status": "SUCCESS",
            "message": f"Welcome back, {auth_data['user']['full_name']}!",
            **auth_data
        }
    except ValueError as ve:
        _record_failed_login(request, payload.identifier)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Authentication service error: {str(e)}")

@app.post("/api/auth/change-password")
def change_password(payload: ChangePasswordRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """Updates password for an authenticated member."""
    try:
        return db.change_password(user["id"], payload.old_password, payload.new_password)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

# -----------------------------------------------------------------------------
# 2. GENERAL SECRETARY & ADMISSIONS (RBAC)
# -----------------------------------------------------------------------------
@app.get("/api/admin/pending-members")
def get_pending_members(_: Dict[str, Any] = Depends(require_permission("manage_members"))):
    """GENERAL_SECRETARY: Lists all applicants awaiting KYC admission."""
    try:
        return db.get_pending_members()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/approve-member")
def approve_member(payload: ApproveMemberRequest, user: Dict[str, Any] = Depends(require_permission("approve_kyc"))):
    """GENERAL_SECRETARY: Approves and activates a member into full standing."""
    try:
        return db.approve_member_kyc(payload.member_id, user["id"])
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/reject-member")
def reject_member(payload: RejectMemberRequest, user: Dict[str, Any] = Depends(require_permission("reject_kyc"))):
    """GENERAL_SECRETARY: Suspends or rejects an invalid applicant."""
    try:
        return db.reject_member_kyc(payload.member_id, user["id"], payload.reason)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# 3. PRESIDENT & EXECUTIVE COMMITTEE DASHBOARD (RBAC)
# -----------------------------------------------------------------------------
@app.get("/api/admin/executive-metrics")
def get_executive_metrics(_: Dict[str, Any] = Depends(require_permission("view_executive_console"))):
    """PRESIDENT / TREASURER / EXECUTIVE: Macro financial & membership KPIs."""
    try:
        return db.get_executive_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/fines/issue")
def issue_fine(payload: IssueFineRequest, _: Dict[str, Any] = Depends(require_permission("issue_fines"))):
    """FINANCIAL_SECRETARY / LEGAL: Issues a statutory disciplinary fine."""
    try:
        return db.issue_disciplinary_fine(
            member_id=payload.member_id,
            infraction_type=payload.infraction_type,
            fine_amount=payload.fine_amount,
            reason=payload.reason
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# 4. REGISTRATION & PUBLIC SERVICES
# -----------------------------------------------------------------------------
@app.post("/api/register")
def register_member(payload: RegistrationRequest):
    """
    Registers a new member into PENDING_KYC status.
    Validates incomplete entries and checks for duplicate emails or phone numbers.
    """
    try:
        data = payload.dict()
        if not data.get("password") or not str(data.get("password")).strip():
            data["password"] = "Wealthbridge@2026"
        result = db.register_new_member(data)
        pwd = result.get("default_password") or data["password"]
        return {
            "status": "SUCCESS",
            "member_id": result["member_id"],
            "member_code": result["member_code"],
            "full_name": result["full_name"],
            "default_password": pwd,
            "message": f"Registration successful! Member Code {result['member_code']} assigned. Default password: {pwd}."
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error during registration: {str(e)}")

@app.get("/")
def root():
    return FileResponse(os.path.join(os.path.dirname(__file__), "index.html"))

@app.get("/api/config")
def get_configuration(
    format: Optional[str] = Query(None, description="Set to 'full' for complete parameter objects")
):
    """Returns statutory system settings and regulatory constants."""
    try:
        if format == "full":
            return db.get_system_config_full()
        return db.get_system_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/admin/config/{config_key}")
def admin_update_system_config(
    config_key: str,
    payload: UpdateSystemConfigRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Allows Administrator, Executive Officers, or Technology Systems Lead
    to update statutory parameters in the MySQL system_config table.
    """
    has_perm = (
        user.get("is_admin_only") or 
        user.get("is_executive") or 
        "configure_system" in user.get("permissions", []) or
        "manage_members" in user.get("permissions", [])
    )
    if not has_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Administrative privileges required to modify statutory system parameters."
        )

    try:
        result = db.update_system_config_item(
            config_key=config_key,
            new_value=payload.config_value,
            updated_by_user_id=user["id"]
        )
        return {"status": "success", "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/members")
def get_members(_: Dict[str, Any] = Depends(require_permission("view_all_members"))):
    """Lists all registered members with their portfolios and standing."""
    try:
        return db.list_members()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/members")
def admin_create_member(payload: AdminCreateMemberRequest, user: Dict[str, Any] = Depends(require_permission("manage_members"))):
    """Enrolls a new cooperator, assigns sequential member code, and provisions tripartite accounts."""
    try:
        return db.admin_add_member(payload.dict(), user["id"])
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# BULK COOPERATOR CSV IMPORT & DIRECTORY EXPORT (MODULE 1)
# -----------------------------------------------------------------------------
@app.post("/api/admin/members/bulk-import")
async def bulk_import_members_csv(
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Bulk enrolls cooperators from verified CSV data:
    - Auto-generates sequential WMC-YYYY-XXX member codes.
    - Sets default initial password (Wealthbridge@2026).
    - Provisions tripartite accounts (Savings, Shares, Welfare).
    - Allocates initial opening balances if provided.
    - Records forensic audit trail.
    """
    is_authorized = (
        "manage_members" in user.get("permissions", []) or
        "SUPER_ADMIN" in user.get("roles", []) or
        "GENERAL_SECRETARY" in user.get("roles", []) or
        user.get("is_executive")
    )
    if not is_authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only General Secretary or Super Admin can bulk import cooperators.")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only standard CSV files (.csv) are supported.")

    try:
        contents = await file.read()
        text = contents.decode("utf-8-sig", errors="replace")
        csv_reader = csv.DictReader(io.StringIO(text))

        rows = []
        for r in csv_reader:
            clean_r = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in r.items() if k}
            rows.append(clean_r)

        if not rows:
            raise HTTPException(status_code=400, detail="CSV file contains no data rows.")

        result = db.bulk_import_members(cooperator_rows=rows, admin_id=user["id"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process CSV import: {str(e)}")


@app.get("/api/admin/members/template-csv")
def download_member_import_template(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Streams a standardized CSV template with instructions for bulk cooperator onboarding."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "first_name", "last_name", "email", "phone", "gender",
        "marital_status", "residential_address", "identification_number",
        "contribution_tier", "opening_savings", "opening_shares", "opening_welfare"
    ])
    writer.writerow([
        "Adebayo", "Ogunlesi", "adebayo.ogunlesi@example.com", "08012345678", "MALE",
        "MARRIED", "14 Victoria Island, Lagos", "12345678901",
        "STANDARD", "250000.00", "50000.00", "12000.00"
    ])
    writer.writerow([
        "Folake", "Solanke", "folake.solanke@example.com", "08098765432", "FEMALE",
        "SINGLE", "8 Ikeja GRA, Lagos", "98765432109",
        "PLUS", "500000.00", "100000.00", "12000.00"
    ])
    csv_text = output.getvalue()
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="Wealthbridge_Member_Import_Template.csv"'}
    )


@app.get("/api/admin/members/export-csv")
def export_members_directory(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Streams the official RFC 4180 CSV cooperator directory with portfolios and balances."""
    is_authorized = (
        "view_all_members" in user.get("permissions", []) or
        "manage_members" in user.get("permissions", []) or
        user.get("is_executive")
    )
    if not is_authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    try:
        csv_text = db.export_members_directory_csv()
        filename = f"Wealthbridge_Cooperators_Directory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/members/{member_id}")
def admin_get_member(member_id: int, user: Dict[str, Any] = Depends(require_permission("manage_members"))):
    """Fetches complete profile record including next of kin and balances for administrative editing."""
    try:
        return db.admin_get_member_full(member_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/admin/members/{member_id}/biodata")
def admin_update_member_biodata(member_id: int, payload: AdminUpdateBiodataRequest, user: Dict[str, Any] = Depends(require_permission("manage_members"))):
    """Directly updates a member's biodata, contact details, status, or banking."""
    try:
        return db.admin_update_member_biodata(member_id, payload.dict(exclude_unset=True), user["id"])
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/members/{member_id}/reset-password")
def admin_reset_member_password(member_id: int, user: Dict[str, Any] = Depends(require_permission("manage_members"))):
    """Resets a member's access password to the official default (Wealthbridge@2026)."""
    try:
        return db.admin_reset_member_password(member_id, user["id"])
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/members/{member_id}/statement")
def get_member_statement(member_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves 360-degree consolidated financial statement for a member."""
    if member_id != user["id"] and "view_all_members" not in user["permissions"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only view your own statement.")
    stmt = db.get_member_statement(member_id)
    if not stmt:
        raise HTTPException(status_code=404, detail=f"Member ID {member_id} not found.")
    return stmt

@app.post("/api/contributions")
def record_contribution(payload: ContributionRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Submits a monthly remittance.
    Automatically splits into Savings (collateral), Shares (10%), and Welfare (NGN 1,000).
    """
    res = db.process_monthly_contribution(
        member_id=user["id"],
        total_amount=payload.total_amount,
        payment_method=payload.payment_method,
        channel_ref=payload.channel_reference,
        officer_id=user["id"]
    )
    if res["status"] != "SUCCESS":
        raise HTTPException(status_code=400, detail=res["message"])
    return res

@app.post("/api/onboarding")
def process_onboarding(payload: OnboardingRequest, user: Dict[str, Any] = Depends(require_permission("manage_members"))):
    """
    Processes statutory new member onboarding payments:
    Entrance Fee (N5,000) + Passbook Fee (N2,000) + optional shares/first month.
    Activates member to ACTIVE status.
    """
    res = db.activate_member_onboarding(
        member_id=payload.member_id,
        payment_method=payload.payment_method,
        channel_ref=payload.channel_reference,
        pay_shares_upfront=payload.pay_shares_upfront,
        first_month_contribution=payload.first_month_contribution,
        officer_id=user["id"]
    )
    if res["status"] != "SUCCESS":
        raise HTTPException(status_code=400, detail=res["message"])
    return res

@app.get("/api/transactions")
def get_transactions(limit: int = Query(default=15, ge=1, le=100), _: Dict[str, Any] = Depends(require_permission("view_ledger_audit"))):
    """Retrieves latest double-entry ledger transactions."""
    try:
        return db.get_recent_transactions(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/members/{member_id}/profile")
def get_member_profile(member_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves full member profile, KYC progress breakdown, and next of kin."""
    try:
        if member_id != user["id"] and "view_all_members" not in user["permissions"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only view your own profile.")
        return db.get_member_profile(member_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/members/{member_id}/profile")
def update_member_profile(member_id: int, payload: ProfileUpdateRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Updates member profile, next of kin, banking, NIN, and passport photograph.
    STATUTORY GOVERNANCE: Address, phone number, and email are placed in PENDING_APPROVAL
    until signed off by the President and General Secretary.
    """
    try:
        if member_id != user["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only update your own profile.")
        data = payload.dict(exclude_unset=True)
        return db.update_member_profile(member_id, data)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/pending-contact-changes")
def get_pending_contact_changes(user: Dict[str, Any] = Depends(get_current_user)):
    """PRESIDENT / GENERAL_SECRETARY: Lists all contact detail modifications awaiting sign-off."""
    try:
        if not {"PRESIDENT", "GENERAL_SECRETARY"}.intersection(user["roles"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the President or General Secretary may review contact changes.")
        return db.get_pending_contact_changes()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/approve-contact-change")
def approve_contact_change(payload: ApproveContactChangeRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """PRESIDENT / GENERAL_SECRETARY: Approves queued contact modifications and promotes to live records."""
    try:
        return db.approve_contact_change(payload.member_id, user["id"], user["roles"])
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/reject-contact-change")
def reject_contact_change(payload: RejectContactChangeRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """PRESIDENT / GENERAL_SECRETARY: Rejects queued contact modifications."""
    try:
        if not {"PRESIDENT", "GENERAL_SECRETARY"}.intersection(user["roles"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the President or General Secretary may reject contact changes.")
        return db.reject_contact_change(payload.member_id, user["id"], payload.reason)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# DYNAMIC TARGET SAVINGS LEDGERS (VOLUNTARY GOAL SAVINGS)
# -----------------------------------------------------------------------------
@app.get("/api/members/{member_id}/target-savings")
def get_member_target_savings(member_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves all voluntary target savings ledgers, progress, and transactions for a member."""
    try:
        if member_id != user["id"] and "view_all_members" not in user["permissions"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only view your own target savings.")
        return db.get_member_target_savings(member_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/members/{member_id}/target-savings")
def create_target_savings(member_id: int, payload: CreateTargetSavingsRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """Creates a new voluntary target savings ledger chosen from standardized categories."""
    try:
        if member_id != user["id"] and "manage_members" not in user["permissions"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only create target savings for your own account.")
        return db.create_target_savings(member_id, payload.dict())
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/members/{member_id}/target-savings/{target_id}/deposit")
def deposit_target_savings(member_id: int, target_id: int, payload: DepositTargetSavingsRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """Deposits / tops up funds into an active or matured Target Savings Ledger."""
    try:
        if member_id != user["id"] and "manage_finances" not in user["permissions"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only top up your own target savings.")
        return db.deposit_target_savings(
            member_id=member_id,
            target_id=target_id,
            amount=payload.amount,
            payment_method=payload.payment_method or "POLARIS_BANK_TRANSFER",
            channel_ref=payload.channel_reference,
            narration=payload.narration
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/members/{member_id}/target-savings/{target_id}/withdraw")
def withdraw_target_savings(member_id: int, target_id: int, payload: WithdrawTargetSavingsRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Processes payout of matured Target Savings to member's commercial bank.
    Enforces maturity lock: cannot withdraw before proposed maturity date.
    """
    try:
        if member_id != user["id"] and "manage_finances" not in user["permissions"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only withdraw from your own target savings.")
        bank_details = {
            "bank_name": payload.bank_name,
            "account_number": payload.account_number,
            "account_name": payload.account_name
        }
        return db.withdraw_target_savings(
            member_id=member_id,
            target_id=target_id,
            amount=payload.amount,
            bank_details=bank_details
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/target-savings")
def get_all_target_savings(user: Dict[str, Any] = Depends(get_current_user)):
    """EXECUTIVE / AUDIT: Retrieves organization-wide target savings summary and all member ledgers."""
    try:
        if not ({"view_financial_reports", "view_ledger_audit", "manage_finances"}.intersection(user["permissions"]) or user.get("is_executive")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Requires executive or financial oversight permissions.")
        return db.get_all_target_savings_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# VERIFYME NG PROXY ENDPOINTS (Bank List & NUBAN Account Name Resolution)
# -----------------------------------------------------------------------------
@app.get("/api/verifyme/banks")
def get_nigerian_banks(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Returns the full list of Nigerian commercial banks and microfinance banks,
    merged from VerifyMe's /banks and /bvn-nuban/banks endpoints, sorted
    alphabetically by name. Used by the KYC bank selector.
    """
    try:
        banks = _fetch_verifyme_banks()
        return {"status": "success", "count": len(banks), "data": banks}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bank list: {str(e)[:200]}")


@app.get("/api/verifyme/account")
def verify_account_name(
    bank_code: str = Query(..., description="Bank code from the banks list"),
    account_number: str = Query(..., description="10-digit NUBAN account number"),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Resolves the account holder name for a given bank code and NUBAN account
    number via VerifyMe. Used in the KYC flow to auto-fill the correct account
    name and prevent payout errors.
    """
    try:
        result = _fetch_verifyme_account_name(bank_code, account_number)
        return {"status": "success", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Account verification failed: {str(e)[:200]}")


# -----------------------------------------------------------------------------
# PAYSTACK PAYMENT GATEWAY & DEDICATED VIRTUAL ACCOUNTS (DVA)
# -----------------------------------------------------------------------------
@app.get("/api/paystack/banks")
def get_paystack_banks(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Returns the comprehensive list of 280+ Nigerian commercial, microfinance,
    and digital banks directly from Paystack API (cached).
    """
    try:
        from paystack_service import PaystackService
        banks = PaystackService.get_banks()
        return {"status": "success", "count": len(banks), "data": banks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Paystack banks: {str(e)[:200]}")


@app.get("/api/paystack/resolve-account")
def resolve_paystack_account(
    bank_code: str = Query(..., description="Bank code from the banks list"),
    account_number: str = Query(..., description="10-digit NUBAN account number"),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Resolves the official registered account holder name for a given bank code and
    10-digit NUBAN via Paystack NIP name enquiry.
    """
    try:
        from paystack_service import PaystackService
        result = PaystackService.resolve_account_number(account_number=account_number, bank_code=bank_code)
        return {"status": "success", "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Paystack account resolution failed: {str(e)[:200]}")


@app.get("/api/members/{member_id}/dedicated-account")
def get_member_dedicated_virtual_account(member_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retrieves or generates a Dedicated Paystack Virtual Account (DVA) for a cooperator.
    Enables instant funding of member savings ledger via Nigerian bank transfer.
    GATED by 100% compulsory KYC completion.
    """
    try:
        if member_id != user["id"] and "manage_finances" not in user.get("permissions", []) and not user.get("is_executive"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. You can only access your own dedicated virtual account.")
        dva = db.get_or_create_member_dva(member_id=member_id)
        if dva.get("is_locked"):
            return {
                "status": "locked",
                "is_locked": True,
                "message": dva.get("reason"),
                "compulsory_kyc": dva.get("compulsory_kyc"),
                "data": dva
            }
        return {"status": "success", "is_locked": False, "data": dva}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/members/{member_id}/kyc-compulsory-status")
def get_member_kyc_compulsory_status(member_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    """Checks the 6 compulsory statutory KYC fields required to unlock DVA and full rights."""
    try:
        if member_id != user["id"] and "view_all_members" not in user.get("permissions", []) and not user.get("is_executive"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        return db.evaluate_compulsory_kyc(member_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/paystack/initialize")
def initialize_paystack_payment(payload: InitializePaymentRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Initializes a Paystack inline/standard checkout transaction for savings deposits,
    target savings funding, or cooperative fee payments.
    """
    try:
        from paystack_service import PaystackService
        email = user.get("email") or "wealthbridge.coopsociety@gmail.com"
        
        meta = {
            "member_id": user["id"],
            "member_code": user.get("member_code"),
            "purpose": payload.purpose,
            "target_id": payload.target_id
        }
        res = PaystackService.initialize_transaction(
            email=email,
            amount=payload.amount,
            callback_url=payload.callback_url,
            metadata=meta
        )
        return {"status": "success", "data": res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/paystack/webhook")
async def paystack_webhook(request: Request):
    """
    Receives automated real-time webhooks from Paystack (e.g. charge.success, dedicated_account.assign.success).
    Validates HMAC-SHA512 signature against PAYSTACK_SECRET_KEY, updates cooperative ledger,
    and logs event idempotently.
    """
    from paystack_service import PaystackService
    signature = request.headers.get("x-paystack-signature", "")
    body_bytes = await request.body()

    if not PaystackService.verify_webhook_signature(body_bytes, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Paystack signature.")

    try:
        import json
        payload = json.loads(body_bytes.decode("utf-8"))
        event = payload.get("event", "")
        data = payload.get("data", {})
        result = db.record_paystack_webhook_credit(event, data)
        return {"status": "success", "result": result}
    except Exception as e:
        print(f"[Paystack Webhook] Processing notice: {e}")
# -----------------------------------------------------------------------------
# MONTHLY PAYMENT ADVICE & WATERFALL AUTO-DISTRIBUTION ENDPOINTS
# -----------------------------------------------------------------------------
@app.get("/api/members/{member_id}/payment-advice/current")
def get_current_payment_advice(
    member_id: int,
    period: Optional[str] = Query(None, description="Billing period format YYYY-MM, e.g. 2026-10"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieves or compiles the active monthly Payment Advice for a cooperator,
    including the itemized breakdown, amounts paid, progress percentage, and outstanding balance.
    """
    try:
        if member_id != user["id"] and "manage_finances" not in user.get("permissions", []) and not user.get("is_executive"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. You may only view your own payment advice.")
        adv = db.generate_or_get_monthly_advice(member_id=member_id, billing_period=period)
        return {"status": "success", "data": adv}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/members/{member_id}/payment-advice/current/pdf")
def get_current_payment_advice_pdf(
    member_id: int,
    request: Request,
    period: Optional[str] = Query(None, description="Billing period e.g. 2026-10"),
    token: Optional[str] = Query(None)
):
    """
    Generates and returns the official monthly payment advice as a high-resolution PDF attachment.
    Accepts authentication via Authorization header or ?token= query parameter.
    """
    auth_token = None
    auth_hdr = request.headers.get("authorization", "")
    if auth_hdr.lower().startswith("bearer "):
        auth_token = auth_hdr[7:].strip()
    elif token:
        auth_token = token.strip()

    if not auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")

    with _auth_lock:
        session = _sessions.get(auth_token)
        if not session or session["expires_at"] <= time.time():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Your session has expired. Please sign in again.")

    user = db.get_member_authorization_context(session["member_id"])
    if not user or user["membership_status"] not in ("ACTIVE", "SYSTEM_ADMINISTRATOR", "PENDING_KYC"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not active.")

    if member_id != user["id"] and "manage_finances" not in user.get("permissions", []) and not user.get("is_executive"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. You may only download your own payment advice PDF.")

    adv = db.generate_or_get_monthly_advice(member_id=member_id, billing_period=period)
    member_rec = db.get_member_profile(member_id) or user
    dva_info = None
    try:
        dva_info = db.get_or_create_member_dva(member_id)
    except Exception:
        pass

    pdf_bytes = AdvicePdfService.generate_pdf(adv, member_rec, dva_info)
    adv_ref = adv.get("advice_reference") or f"WMC-ADV-{member_id}"
    filename = f"Wealthbridge_Payment_Advice_{adv_ref}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@app.get("/api/members/{member_id}/payment-advices")
def get_member_payment_advices(member_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves billing statement history of all payment advices for a cooperator."""
    try:
        if member_id != user["id"] and "manage_finances" not in user.get("permissions", []) and not user.get("is_executive"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. You may only view your own payment advice history.")
        advices = db.get_member_payment_advices(member_id=member_id)
        return {"status": "success", "count": len(advices), "data": advices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/members/{member_id}/payment-advice/distribute")
def distribute_payment(member_id: int, payload: DistributePaymentRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Executes Priority Waterfall auto-distribution against the member's current Payment Advice:
    1) Fines -> 2) Active Loan -> 3) Welfare -> 4) Shares -> 5) Regular Savings -> 6) Target Savings -> 7) Surplus into Savings.
    """
    try:
        if member_id != user["id"] and "manage_finances" not in user.get("permissions", []):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        result = db.distribute_payment_by_advice(
            member_id=member_id,
            amount_paid=payload.amount,
            payment_method=payload.payment_method or "POLARIS_BANK_TRANSFER",
            payment_ref=payload.payment_reference,
            narration=payload.narration
        )
        return {"status": "success", "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/admin/payment-advice/{advice_id}")
def admin_revise_payment_advice(advice_id: int, payload: RevisePaymentAdviceRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Allows Financial Secretary / Administrator to adjust or revise an advice
    (e.g., adding an agreed levy, adjusting an obligation, or granting loan relief).
    """
    try:
        if not ({"manage_finances", "manage_members"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Requires Financial Secretary or Executive privileges.")
        updates = payload.dict(exclude_unset=True)
        result = db.admin_revise_payment_advice(advice_id=advice_id, updates=updates)
        return {"status": "success", "data": result}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/payment-advices")
def get_all_payment_advices(
    period: Optional[str] = Query(None, description="Billing period format YYYY-MM, e.g. 2026-10"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """EXECUTIVE / AUDIT: Retrieves organization-wide payment advices summary, collection rates, and member breakdown."""
    try:
        if not ({"view_financial_reports", "manage_finances", "view_ledger_audit"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        summary = db.get_all_payment_advices_summary(billing_period=period)
        return {"status": "success", "data": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# COOPERATIVE MEMBER STATEMENTS & REPORTS API (CAP C15 COMPLIANT)
# -----------------------------------------------------------------------------

def _resolve_report_user(request: Request, token: Optional[str] = None) -> Dict[str, Any]:
    """Resolves authenticated cooperator from Authorization header or ?token= query parameter."""
    auth_token = None
    auth_hdr = request.headers.get("authorization", "")
    if auth_hdr.lower().startswith("bearer "):
        auth_token = auth_hdr[7:].strip()
    elif token:
        auth_token = token.strip()

    if not auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication is required.")

    with _auth_lock:
        session = _sessions.get(auth_token)
        if not session or session["expires_at"] <= time.time():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Your session has expired. Please sign in again.")

    user = db.get_member_authorization_context(session["member_id"])
    if not user or user["membership_status"] not in ("ACTIVE", "SYSTEM_ADMINISTRATOR", "PENDING_KYC"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This account is not active.")
    return user


@app.get("/api/members/{member_id}/reports/years")
def get_member_report_years(member_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves available financial calendar years for a member."""
    if member_id != user["id"] and "view_financial_reports" not in user.get("permissions", []) and not user.get("is_executive"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    years = db.get_member_report_years(member_id=member_id)
    return {"status": "success", "data": years}


@app.get("/api/members/{member_id}/reports/ledger")
def get_member_passbook_ledger_json(
    member_id: int,
    year: Optional[int] = Query(None, description="Financial Year (e.g. 2026) or empty for all-time"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves the statutory annual passbook ledger statement with tripartite breakdown."""
    if member_id != user["id"] and "view_financial_reports" not in user.get("permissions", []) and not user.get("is_executive"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    try:
        ledger = db.get_member_passbook_ledger(member_id=member_id, year=year)
        return {"status": "success", "data": ledger}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/members/{member_id}/reports/ledger/pdf")
def get_member_passbook_ledger_pdf(
    member_id: int,
    request: Request,
    year: Optional[int] = Query(None, description="Financial Year (e.g. 2026)"),
    token: Optional[str] = Query(None)
):
    """Downloads official statutory Passbook Ledger statement as publication-grade PDF."""
    user = _resolve_report_user(request, token)
    if member_id != user["id"] and "view_financial_reports" not in user.get("permissions", []) and not user.get("is_executive"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    try:
        ledger = db.get_member_passbook_ledger(member_id=member_id, year=year)
        pdf_bytes = ReportPdfService.generate_passbook_ledger_pdf(ledger)
        m_code = ledger.get("member", {}).get("member_code", f"WMC-{member_id}")
        yr_label = year if year else "All_Time"
        filename = f"Wealthbridge_Passbook_Ledger_{m_code}_{yr_label}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/members/{member_id}/reports/credits")
def get_member_credits_statement_json(
    member_id: int,
    year: Optional[int] = Query(None, description="Financial Year (e.g. 2026)"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves all inward remittances (credits) audit report for a member."""
    if member_id != user["id"] and "view_financial_reports" not in user.get("permissions", []) and not user.get("is_executive"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    try:
        credits = db.get_member_credits_statement(member_id=member_id, year=year)
        return {"status": "success", "data": credits}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/members/{member_id}/reports/credits/pdf")
def get_member_credits_statement_pdf(
    member_id: int,
    request: Request,
    year: Optional[int] = Query(None, description="Financial Year (e.g. 2026)"),
    token: Optional[str] = Query(None)
):
    """Downloads official Inward Remittances (Credits) audit statement as publication-grade PDF."""
    user = _resolve_report_user(request, token)
    if member_id != user["id"] and "view_financial_reports" not in user.get("permissions", []) and not user.get("is_executive"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    try:
        credits = db.get_member_credits_statement(member_id=member_id, year=year)
        pdf_bytes = ReportPdfService.generate_credits_statement_pdf(credits)
        m_code = credits.get("member", {}).get("member_code", f"WMC-{member_id}")
        yr_label = year if year else "All_Time"
        filename = f"Wealthbridge_Credits_Audit_{m_code}_{yr_label}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/members/{member_id}/reports/debits")
def get_member_debits_statement_json(
    member_id: int,
    year: Optional[int] = Query(None, description="Financial Year (e.g. 2026)"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves all outward disbursements and claims (debits) audit report for a member."""
    if member_id != user["id"] and "view_financial_reports" not in user.get("permissions", []) and not user.get("is_executive"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    try:
        debits = db.get_member_debits_statement(member_id=member_id, year=year)
        return {"status": "success", "data": debits}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/members/{member_id}/reports/debits/pdf")
def get_member_debits_statement_pdf(
    member_id: int,
    request: Request,
    year: Optional[int] = Query(None, description="Financial Year (e.g. 2026)"),
    token: Optional[str] = Query(None)
):
    """Downloads official Disbursements and Claims (Debits) audit statement as publication-grade PDF."""
    user = _resolve_report_user(request, token)
    if member_id != user["id"] and "view_financial_reports" not in user.get("permissions", []) and not user.get("is_executive"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    try:
        debits = db.get_member_debits_statement(member_id=member_id, year=year)
        pdf_bytes = ReportPdfService.generate_debits_statement_pdf(debits)
        m_code = debits.get("member", {}).get("member_code", f"WMC-{member_id}")
        yr_label = year if year else "All_Time"
        filename = f"Wealthbridge_Debits_Audit_{m_code}_{yr_label}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/members/{member_id}/reports/loans")
def get_member_loans_statement_json(member_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves loan facilities and amortization schedule statement for a member."""
    if member_id != user["id"] and "view_financial_reports" not in user.get("permissions", []) and not user.get("is_executive"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    try:
        loans = db.get_member_loans_statement(member_id=member_id)
        return {"status": "success", "data": loans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/members/{member_id}/reports/loans/pdf")
def get_member_loans_statement_pdf(
    member_id: int,
    request: Request,
    token: Optional[str] = Query(None)
):
    """Downloads official Loan Facilities and Amortization statement as publication-grade PDF."""
    user = _resolve_report_user(request, token)
    if member_id != user["id"] and "view_financial_reports" not in user.get("permissions", []) and not user.get("is_executive"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    try:
        loans = db.get_member_loans_statement(member_id=member_id)
        pdf_bytes = ReportPdfService.generate_loans_statement_pdf(loans)
        m_code = loans.get("member", {}).get("member_code", f"WMC-{member_id}")
        filename = f"Wealthbridge_Loans_Statement_{m_code}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/members/{member_id}/id-card")
def get_member_id_card_data(member_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retrieves official Electronic Membership ID card dataset, including
    passport photo, verification status, masked NIN, and signatory credentials.
    STATUTORY RULE: Accessible only after formal Secretariat approval (ACTIVE standing).
    """
    is_exec = bool(user.get("is_executive") or {"view_all_members", "manage_members", "approve_kyc"}.intersection(user.get("permissions", [])))
    if member_id != user["id"] and not is_exec:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. You may only view your own membership ID card.")

    prof = db.get_member_profile(member_id)
    if not prof:
        raise HTTPException(status_code=404, detail="Member record not found.")

    member = prof.get("member", {})
    kyc_pct = prof.get("kyc_completion_percent", member.get("kyc_completion_percent", 0))
    is_secretariat_approved = member.get("status") in ("ACTIVE", "SYSTEM_ADMINISTRATOR")

    # Invariant: ID card is visible only after secretariat approval
    if not is_secretariat_approved and not is_exec:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Official Electronic Membership ID Card is accessible only after formal Secretariat approval and admission into active Society standing."
        )

    m_id = member.get("id", member_id)
    m_code = member.get("member_code", f"WMC-{member_id}")
    full_name = member.get("full_name") or f"{member.get('first_name', '')} {member.get('last_name', '')}".strip() or "Cooperator"

    return {
        "status": "success",
        "eligible": is_secretariat_approved,
        "is_secretariat_approved": is_secretariat_approved,
        "data": {
            "member_id": m_id,
            "member_code": m_code,
            "full_name": full_name,
            "email": member.get("email"),
            "phone_number": member.get("phone") or member.get("phone_number"),
            "residential_address": member.get("residential_address"),
            "membership_status": member.get("status", "ACTIVE"),
            "contribution_tier": member.get("contribution_tier", "STANDARD"),
            "monthly_commitment": member.get("monthly_commitment", 10000.0),
            "date_of_admission": str(member.get("admission_date") or "2026-09-26"),
            "masked_nin": f"******{str(member.get('identification_number', '0000'))[-4:]}" if member.get("identification_number") else "******0000",
            "passport_photo": member.get("passport_photo"),
            "kyc_completion_percent": kyc_pct,
            "secretariat_contact": "wealthbridge.coopsociety@gmail.com",
            "signatories": [
                {"role": "General Secretary", "title": "Signatory 1", "status": "AUTHORIZED"},
                {"role": "President & Chairman", "title": "Signatory 2", "status": "AUTHORIZED"}
            ],
            "charter_reference": "Lagos State Cooperative Societies Law (Cap C15)"
        }
    }


@app.get("/api/members/{member_id}/id-card/pdf")
def get_member_id_card_pdf(
    member_id: int,
    request: Request,
    token: Optional[str] = Query(None)
):
    """
    Generates and downloads the official print-and-cut Electronic Membership ID Card
    (Front and Back CR80 size) as a publication-grade vector PDF.
    STATUTORY RULE: Downloadable strictly only after formal Secretariat approval (ACTIVE standing).
    """
    user = _resolve_report_user(request, token)
    is_exec = bool(user.get("is_executive") or {"view_all_members", "manage_members", "approve_kyc"}.intersection(user.get("permissions", [])))
    if member_id != user["id"] and not is_exec:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. You may only download your own ID card.")

    prof = db.get_member_profile(member_id)
    if not prof:
        raise HTTPException(status_code=404, detail="Member record not found.")

    member = prof.get("member", {})
    kyc_pct = prof.get("kyc_completion_percent", member.get("kyc_completion_percent", 0))
    is_secretariat_approved = member.get("status") in ("ACTIVE", "SYSTEM_ADMINISTRATOR")

    if not is_secretariat_approved and not is_exec:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Official Electronic Membership ID Card is downloadable only after formal Secretariat approval and admission into active Society standing."
        )

    try:
        config = db.get_system_config() if hasattr(db, "get_system_config") else None
        pdf_bytes = IdCardPdfService.generate_id_card_pdf(member, config)
        m_code = member.get("member_code", f"WMC-{member_id}")
        filename = f"Wealthbridge_ID_Card_{m_code}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate ID card PDF: {str(e)}")


# =============================================================================
# 12. COMPREHENSIVE GOVERNANCE SUITE ENDPOINTS
# =============================================================================

# --- A. FILE UPLOAD HANDLER (Receipts & Evidence Documents) ---
@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Uploads supporting documentation (PDF, JPG, PNG, DOCX, TXT) for
    loan appeals, manual bank payment receipts, or KYC verification.
    """
    allowed_extensions = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".docx", ".doc", ".txt"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(allowed_extensions)}"
        )

    upload_dir = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = f"wmc_{user['id']}_{int(time.time())}_{secrets.token_hex(4)}{ext}"
    dest_path = os.path.join(upload_dir, safe_name)

    with open(dest_path, "wb") as f_out:
        shutil.copyfileobj(file.file, f_out)

    rel_url = f"/uploads/{safe_name}"
    return {
        "status": "success",
        "file_url": rel_url,
        "filename": file.filename,
        "mime_type": file.content_type,
        "size": os.path.getsize(dest_path)
    }


# --- B. APPLICANT DOSSIER DRAWER (Secretariat & Executive Inspection) ---
@app.get("/api/admin/pending-members/{member_id}/dossier")
def get_applicant_dossier(
    member_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Retrieves full registration dossier and uploaded documentation for executive inspection
    before approving membership or verifying KYC.
    """
    if not ({"view_all_members", "manage_members", "approve_kyc"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required to inspect dossiers.")
    try:
        dossier = db.get_applicant_dossier(member_id)
        return {"status": "success", "data": dossier}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- C. DYNAMIC RBAC & ROLE MANAGEMENT ---
@app.get("/api/admin/roles")
def get_roles(user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves all statutory core and custom operational roles with assigned permissions."""
    if not ({"manage_officers", "configure_system", "manage_members"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required.")
    try:
        roles = db.get_all_roles()
        return {"status": "success", "data": roles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/roles")
def create_custom_role(
    payload: CreateRoleRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Creates a custom operational role and binds selected granular permissions."""
    if not ({"manage_officers", "configure_system"}.intersection(user.get("permissions", [])) or "SUPER_ADMIN" in user.get("roles", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admin or authorized officer can create roles.")
    try:
        keys = payload.permission_keys or payload.permission_codes or []
        role = db.create_custom_role(
            role_code=payload.role_code,
            role_name=payload.role_name,
            description=payload.description or "",
            permission_keys=keys,
            created_by=user["id"]
        )
        return {"status": "success", "data": role}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/admin/roles/{role_id}")
def update_custom_role(
    role_id: int,
    payload: UpdateRoleRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Modifies a custom operational role and updates its bound permissions."""
    if not ({"manage_officers", "configure_system"}.intersection(user.get("permissions", [])) or "SUPER_ADMIN" in user.get("roles", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admin or authorized officer can modify roles.")
    try:
        keys = payload.permission_keys if payload.permission_keys is not None else payload.permission_codes
        res = db.update_custom_role(
            role_id=role_id,
            role_name=payload.role_name,
            description=payload.description,
            permission_keys=keys,
            updated_by=user["id"]
        )
        return {"status": "success", "data": res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admin/roles/{role_id}")
def delete_custom_role(
    role_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Permanently deletes a custom operational role (statutory roles protected)."""
    if not ({"manage_officers", "configure_system"}.intersection(user.get("permissions", [])) or "SUPER_ADMIN" in user.get("roles", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admin or authorized officer can delete roles.")
    try:
        res = db.delete_custom_role(role_id=role_id, deleted_by=user["id"])
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/admin/roles/{role_id}/permissions")
def update_role_permissions(
    role_id: int,
    payload: UpdateRolePermissionsRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Updates permissions assigned to a role."""
    if not ({"manage_officers", "configure_system"}.intersection(user.get("permissions", [])) or "SUPER_ADMIN" in user.get("roles", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admin can edit role permissions.")
    try:
        res = db.update_role_permissions(role_id=role_id, permission_keys=payload.permission_keys, updated_by=user["id"])
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/permissions")
def get_permissions(user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves all 35 granular statutory permissions grouped by module."""
    if not ({"manage_officers", "configure_system", "view_executive_console"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    try:
        perms = db.get_all_permissions()
        return {"status": "success", "data": perms}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/members/{member_id}/roles")
def get_member_assigned_roles(
    member_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves all roles dynamically granted to a cooperator."""
    if member_id != user["id"] and not ({"manage_officers", "manage_members"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    try:
        roles = db.get_member_roles(member_id)
        return {"status": "success", "data": roles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/members/{member_id}/roles")
def assign_role_to_member(
    member_id: int,
    payload: AssignRoleRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Allocates an operational role to an existing cooperator."""
    if not ({"manage_officers", "manage_members"}.intersection(user.get("permissions", [])) or "SUPER_ADMIN" in user.get("roles", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin or Executive clearance required.")
    try:
        res = db.assign_role_to_member(member_id=member_id, role_id=payload.role_id, assigned_by=user["id"])
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/admin/members/{member_id}/roles/{role_id}")
def revoke_role_from_member(
    member_id: int,
    role_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Revokes a role assignment from a cooperator."""
    if not ({"manage_officers", "manage_members"}.intersection(user.get("permissions", [])) or "SUPER_ADMIN" in user.get("roles", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin or Executive clearance required.")
    try:
        res = db.revoke_role_from_member(member_id=member_id, role_id=role_id, revoked_by=user["id"])
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- D. MULTI-TIER LOAN GOVERNANCE & APPEALS ---
@app.get("/api/loan-products")
def get_loan_products():
    """Retrieves all statutory loan products configured in the bye-laws."""
    try:
        products = db.get_active_loan_products()
        return {"status": "success", "data": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/members/guarantor-candidates")
def get_guarantor_candidates(user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves active cooperators eligible to guarantee a loan."""
    try:
        candidates = db.get_active_guarantor_candidates(exclude_member_id=user["id"])
        return {"status": "success", "data": candidates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/members/{member_id}/loans")
def apply_for_loan(
    member_id: int,
    payload: ApplyLoanRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Submits a loan application into the Multi-Tier Sequential Governance Pipeline (Starts at Stage 1 / 0%)."""
    if member_id != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only apply for financing for your own account.")
    try:
        guarantors_data = [g.dict() if hasattr(g, 'dict') else g for g in (payload.guarantors or [])]
        loan = db.apply_for_loan(
            member_id=member_id,
            principal_amount=payload.principal_amount,
            tenure_months=payload.tenure_months,
            purpose_narration=payload.purpose_narration,
            product_id=payload.product_id or 1,
            guarantors=guarantors_data
        )
        return {"status": "success", "data": loan}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/members/{member_id}/loans")
def get_member_loans(
    member_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Borrower view: Returns approval level in %, status, and decline reason if declined.
    Internal executive committee deliberations remain confidential.
    """
    if member_id != user["id"] and not ({"view_all_members", "credit_committee_approval"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    try:
        loans = db.get_member_loans(member_id)
        return {"status": "success", "data": loans}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/loans/pending-review")
def get_loans_for_review(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Retrieves loans pending review for the logged-in officer's stage:
    - President / Super Admin sees all stages with override capability.
    - Credit Committee sees Stage 1 (0% -> 33%).
    - Financial Secretary sees Stage 2 (33% -> 66%).
    - Treasurer sees Stage 3 (66% -> 100% and Disbursement).
    """
    is_pres = ("PRESIDENT" in user.get("roles", []) or "SUPER_ADMIN" in user.get("roles", []) or user.get("primary_role") == "PRESIDENT")
    primary_role = user.get("primary_role", "MEMBER")
    
    loan_perms = {"credit_committee_approval", "financial_sec_loan_approval", "treasurer_loan_disbursement", "presidential_loan_override", "executive_oversight"}
    if not (loan_perms.intersection(user.get("permissions", [])) or user.get("is_executive")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to review loan applications.")

    try:
        loans = db.get_loans_for_review(
            officer_role=primary_role,
            officer_id=user["id"],
            is_president=is_pres
        )
        return {"status": "success", "data": loans, "officer_role": primary_role, "is_president": is_pres}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/loans/{loan_id}/review")
def review_loan_application(
    loan_id: int,
    payload: ReviewLoanRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Performs sequential loan review or presidential override.
    - If President approves: immediately sets 100% DISBURSED.
    - If Treasurer approves at Stage 3: sets 100% DISBURSED and generates repayment schedule.
    - If Declined: logs mandatory decline reason so borrower can appeal.
    """
    roles = user.get("roles", [])
    officer_role = user.get("primary_role") or ("PRESIDENT" if "PRESIDENT" in roles else ("SUPER_ADMIN" if "SUPER_ADMIN" in roles else "CREDIT_COMMITTEE"))

    try:
        res = db.review_loan_application(
            loan_id=loan_id,
            officer_id=user["id"],
            officer_role=officer_role,
            action=payload.action,
            comments=payload.comments,
            is_president_override=bool(payload.is_president_override)
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/loans/{loan_id}/foreclosure-offset")
def execute_loan_foreclosure_offset(
    loan_id: int,
    payload: ForeclosureOffsetPayload,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Statutory 90-Day Loan Default Foreclosure Offset:
    Authorized by Financial Secretary and President.
    Offsets severely defaulted loan balances against borrower savings and/or guarantor collateral savings.
    """
    if not ({"manage_loans", "approve_loans_executive"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive foreclosure clearance required.")
    try:
        res = db.execute_loan_foreclosure_offset(
            loan_id=loan_id,
            officer_id=user["id"],
            offset_borrower_amount=payload.offset_borrower_amount,
            offset_guarantor_amount=payload.offset_guarantor_amount,
            officer_notes=payload.officer_notes or ""
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/notifications")
def get_system_notifications(user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves active system notifications for the authenticated user or executive desk."""
    is_admin = bool(user.get("is_executive") or user.get("is_admin_only"))
    return db.get_notifications(user["id"], is_admin=is_admin)

@app.post("/api/notifications/{notification_id}/read")
def mark_system_notification_read(notification_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    """Marks a notification as read."""
    return {"success": db.mark_notification_as_read(notification_id, user["id"])}

@app.get("/api/members/{member_id}/login-prompts")
def get_member_login_prompts(member_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves active modal alerts/prompts for member."""
    return db.get_login_prompts_for_user(member_id, user.get("member_code", ""), user.get("roles", []))

@app.post("/api/members/{member_id}/loans/{loan_id}/appeal")
def submit_loan_appeal(
    member_id: int,
    loan_id: int,
    payload: SubmitLoanAppealRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Allows a cooperator to contest a declined loan by providing detailed explanation
    and uploading supporting documentation (PDF, image, doc).
    """
    if member_id != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only appeal your own loan applications.")
    try:
        res = db.submit_loan_appeal(
            loan_id=loan_id,
            member_id=member_id,
            appeal_comments=payload.appeal_comments,
            attached_document_path=payload.attached_document_path,
            document_name=payload.document_name,
            document_mime_type=payload.document_mime_type
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/loan-appeals")
def get_loan_appeals(
    loan_id: Optional[int] = None,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Inspects pending or resolved loan appeals."""
    if not ({"credit_committee_approval", "executive_oversight"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required.")
    try:
        appeals = db.get_loan_appeals(loan_id=loan_id)
        return {"status": "success", "data": appeals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/loan-appeals/{appeal_id}/resolve")
def resolve_loan_appeal(
    appeal_id: int,
    payload: ResolveLoanAppealRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Resolves a contested loan application:
    - REINSTATE: Re-enters loan into pipeline.
    - UPHOLD: Sustains decline.
    """
    if not ({"credit_committee_approval", "executive_oversight"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required.")
    try:
        res = db.resolve_loan_appeal(
            appeal_id=appeal_id,
            officer_id=user["id"],
            officer_role=user.get("primary_role", "EXECUTIVE"),
            action=payload.action,
            review_response=payload.review_response
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- E. POLARIS BANK MANUAL PAYMENT LOGGING & EXECUTIVE REMITTANCE DESK ---
@app.post("/api/members/{member_id}/manual-payments")
def log_manual_bank_payment(
    member_id: int,
    payload: ManualBankPaymentRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Allows a member to log a direct Polaris Bank transfer with uploaded proof of payment."""
    if member_id != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only log payments for your own account.")
    try:
        res = db.log_manual_bank_payment(
            member_id=member_id,
            amount=payload.amount,
            payment_date=payload.payment_date,
            payment_reference=payload.payment_reference,
            narration=payload.narration,
            receipt_file_path=payload.receipt_file_path,
            receipt_mime_type=payload.receipt_mime_type
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/manual-payments/pending")
def get_pending_manual_payments(user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieves Polaris Bank remittances pending reconciliation by Treasury."""
    if not ({"verify_contributions", "manage_inward_remittances", "authorize_disbursements"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Treasury clearance required.")
    try:
        payments = db.get_pending_manual_payments()
        return {"status": "success", "data": payments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/manual-payments/{payment_id}/verify")
def verify_manual_bank_payment(
    payment_id: int,
    payload: VerifyManualPaymentRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Verifies a Polaris Bank remittance and credits member ledgers via payment advice waterfall.
    Accessible to Financial Secretary, Treasurer, and President.
    """
    if not ({"verify_contributions", "manage_inward_remittances"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Treasury verification privilege required.")
    try:
        res = db.verify_manual_bank_payment(
            payment_id=payment_id,
            officer_id=user["id"],
            officer_role=user.get("primary_role", "TREASURY_OFFICER"),
            distribution_override=payload.distribution_override,
            verification_notes=payload.verification_notes
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/manual-payments/{payment_id}/reject")
def reject_manual_bank_payment(
    payment_id: int,
    payload: RejectManualPaymentRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Rejects an unverified or fraudulent manual bank payment."""
    if not ({"verify_contributions", "manage_inward_remittances"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Treasury verification privilege required.")
    try:
        res = db.reject_manual_bank_payment(
            payment_id=payment_id,
            officer_id=user["id"],
            officer_role=user.get("primary_role", "TREASURY_OFFICER"),
            rejection_reason=payload.rejection_reason
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/manual-payments/direct-credit")
def record_direct_member_credit(
    payload: DirectMemberCreditRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Direct executive credit desk for Financial Secretary, Treasurer, and President.
    Allows direct crediting of member savings, shares, or loan repayments with mandatory audit narration.
    """
    if not ({"verify_contributions", "manage_inward_remittances", "authorize_disbursements"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Treasury executive privileges required.")
    try:
        res = db.record_direct_member_credit(
            member_id=payload.member_id,
            officer_id=user["id"],
            officer_role=user.get("primary_role", "EXECUTIVE_OFFICER"),
            amount=payload.amount,
            credit_category=payload.credit_category,
            narration=payload.narration
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- F. PAYMENT ADVICE REVISION ---
@app.post("/api/admin/payment-advices/{advice_id}/modify")
def modify_payment_advice(
    advice_id: int,
    payload: ModifyAdviceRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Modifies monthly payment advice line items:
    - Scope: THIS_MONTH_ONLY or PERMANENT_COMMITMENT
    - Mandatory statutory justification recorded in immutable audit log.
    Accessible to Financial Secretary, Treasurer, and President.
    """
    if not ({"modify_payment_advice", "manage_finances"}.intersection(user.get("permissions", [])) or user.get("is_executive")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Advice modification privilege required.")
    try:
        modified_items = payload.dict(exclude={"scope", "statutory_justification"}, exclude_unset=True)
        res = db.modify_payment_advice(
            advice_id=advice_id,
            officer_id=user["id"],
            officer_role=user.get("primary_role", "FINANCIAL_SECRETARY"),
            scope=payload.scope,
            modified_items=modified_items,
            statutory_justification=payload.statutory_justification
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- G. TAMPER-EVIDENT FORENSIC AUDIT TRAIL ---
@app.get("/api/admin/audit-logs")
def get_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    actor_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Forensic inspection of immutable audit trail with deep before/after diffs.
    Strictly restricted to President, Super Admin, and Internal Auditor.
    """
    is_authorized = (
        "system_audit" in user.get("permissions", []) or
        "SUPER_ADMIN" in user.get("roles", []) or
        "PRESIDENT" in user.get("roles", []) or
        "INTERNAL_AUDITOR" in user.get("roles", []) or
        user.get("primary_role") in ("PRESIDENT", "SUPER_ADMIN", "INTERNAL_AUDITOR")
    )
    if not is_authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access strictly restricted to President, Super Admin, and Internal Auditor.")

    try:
        logs = db.get_audit_logs(
            limit=limit,
            offset=offset,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            date_from=date_from,
            date_to=date_to
        )
        return {"status": "success", "data": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/audit-logs/export")
def export_audit_logs_csv(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Exports forensic audit trail as CSV for legal compliance and external statutory audit."""
    is_authorized = (
        "system_audit" in user.get("permissions", []) or
        "SUPER_ADMIN" in user.get("roles", []) or
        "PRESIDENT" in user.get("roles", []) or
        "INTERNAL_AUDITOR" in user.get("roles", []) or
        user.get("primary_role") in ("PRESIDENT", "SUPER_ADMIN", "INTERNAL_AUDITOR")
    )
    if not is_authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    try:
        logs_data = db.get_audit_logs(limit=2000, offset=0, date_from=date_from, date_to=date_to)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Timestamp", "Actor ID", "Actor Name", "Actor Role", "Action", "Resource Type", "Resource ID", "IP Address", "Summary"])
        for row in logs_data["logs"]:
            writer.writerow([
                row["id"], row["created_at"], row.get("user_id", ""),
                row["actor_name"], row["actor_role"], row["action"],
                row["resource_type"], row.get("resource_id", ""),
                row.get("ip_address", ""), row.get("summary", "")
            ])

        csv_content = output.getvalue()
        filename = f"WMC_Forensic_Audit_Trail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# 16. GUARANTOR DIGITAL CONSENT WORKFLOW (MODULE 3 & 6)
# -----------------------------------------------------------------------------
@app.get("/api/members/{member_id}/guarantor-requests")
def get_member_guarantor_requests(
    member_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves all incoming and historical peer loan guarantee requests for a cooperator."""
    if member_id != user["id"] and not (user.get("is_executive") or "credit_committee_approval" in user.get("permissions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    try:
        requests_list = db.get_member_guarantor_requests(member_id)
        return {"status": "success", "data": requests_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/members/{member_id}/guarantor-requests/{request_id}/respond")
def respond_to_guarantor_request(
    member_id: int,
    request_id: int,
    payload: GuarantorConsentDecisionRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Executes in-portal digital signature consent:
    - ACCEPT: Validates available unencumbered savings, places administrative collateral lien,
      and if all peer guarantors have signed, advances loan to Stage 1 Credit Committee.
    - DECLINE: Marks guarantee declined and notifies loan applicant.
    """
    if member_id != user["id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the designated guarantor may sign this consent.")
    try:
        result = db.respond_to_guarantor_request(
            guarantor_member_id=member_id,
            guarantor_request_id=request_id,
            decision=payload.decision,
            comments=payload.comments
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------------------------------------------------------
# 17. COOPERATOR EXIT, WITHDRAWAL & SETTLEMENT DESK (ARTICLES 9 & 11)
# -----------------------------------------------------------------------------
@app.post("/api/members/{member_id}/exit-request")
def submit_member_exit_request(
    member_id: int,
    payload: MemberExitRequestPayload,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Lodges a statutory cooperator membership withdrawal or deceased estate settlement:
    - Calculates real-time financial obligations and liquidation refund breakdown.
    - Enforces statutory notice period: 60 days for voluntary withdrawal, 0 days for death/estate.
    - Calculates net refund = (Savings + Target Savings + Shares + Bereavement Grant) - (Loans + Fines + Exit Fee).
    - Status set to PENDING_CLEARANCE for General Secretary & President dual sign-off.
    """
    if member_id != user["id"] and not (user.get("is_executive") or "manage_members" in user.get("permissions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    try:
        result = db.submit_member_exit_request(
            member_id=member_id,
            exit_type=payload.exit_type,
            reason=payload.reason,
            supporting_doc_url=payload.supporting_doc_url,
            nok_claimant=payload.nok_claimant
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/members/{member_id}/exit-request")
def get_member_exit_record(
    member_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves current or historical exit/settlement records for a member."""
    if member_id != user["id"] and not (user.get("is_executive") or "manage_members" in user.get("permissions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT * FROM member_exits
                WHERE member_id = %s
                ORDER BY id DESC LIMIT 1;
            """, (member_id,))
            exit_rec = cursor.fetchone()
            if not exit_rec:
                return {"status": "none", "data": None}
            for col in ["total_savings_at_exit", "total_target_savings_at_exit", "total_shares_at_exit",
                        "outstanding_loans_at_exit", "outstanding_fines_at_exit", "exit_processing_fee",
                        "bereavement_welfare_grant", "net_refund_amount"]:
                if col in exit_rec:
                    exit_rec[col] = float(exit_rec[col])
            for dt_col in ["notice_date", "statutory_notice_expiry_date", "created_at", "updated_at", "refund_disbursed_at"]:
                if exit_rec.get(dt_col):
                    exit_rec[dt_col] = str(exit_rec[dt_col])
            return {"status": "success", "data": exit_rec}
        finally:
            cursor.close()
            conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/exits/pending")
def get_pending_exits(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """PRESIDENT & GENERAL_SECRETARY: Lists all pending exit/withdrawal files awaiting review."""
    is_authorized = (
        "manage_members" in user.get("permissions", []) or
        "PRESIDENT" in user.get("roles", []) or
        "GENERAL_SECRETARY" in user.get("roles", []) or
        "SUPER_ADMIN" in user.get("roles", []) or
        user.get("is_executive")
    )
    if not is_authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required to review exit settlements.")
    try:
        exits = db.get_pending_exits_for_review()
        return {"status": "success", "data": exits}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/exits/{exit_id}/approve")
def approve_exit_settlement(
    exit_id: int,
    payload: ApproveExitSettlementPayload,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    GENERAL_SECRETARY & PRESIDENT sign-off: Finalizes cooperator exit, settles accounts,
    disburses net liquidation refund, and transitions member status to EXITED (or DECEASED).
    """
    is_authorized = (
        "manage_members" in user.get("permissions", []) or
        "PRESIDENT" in user.get("roles", []) or
        "GENERAL_SECRETARY" in user.get("roles", []) or
        "SUPER_ADMIN" in user.get("roles", []) or
        user.get("is_executive")
    )
    if not is_authorized:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required to finalize exit settlements.")
    try:
        role = user.get("primary_role") or ("PRESIDENT" if "PRESIDENT" in user.get("roles", []) else "GENERAL_SECRETARY")
        result = db.approve_member_exit_settlement(
            exit_id=exit_id,
            officer_id=user["id"],
            officer_role=role,
            refund_payment_ref=payload.refund_payment_ref
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MODULE 4: ACCOUNTING & FINANCIAL CONTROL ENDPOINTS
# =============================================================================

@app.get("/api/accounting/chart-of-accounts")
def get_chart_of_accounts(
    account_type: Optional[str] = Query(None, description="ASSET, LIABILITY, EQUITY, INCOME, or EXPENSE"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves standard Chart of Accounts with live posted debit/credit/net balances."""
    if not (user.get("is_executive") or "manage_accounting" in user.get("permissions", []) or "view_financial_statements" in user.get("permissions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required to view general ledger accounts.")
    try:
        return {"status": "success", "data": db.get_chart_of_accounts(account_type=account_type)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accounting/trial-balance")
def get_trial_balance(
    as_of_date: Optional[str] = Query(None, description="Cut-off date (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Generates standard Trial Balance verifying double-entry Debits == Credits."""
    if not (user.get("is_executive") or "manage_accounting" in user.get("permissions", []) or "view_financial_statements" in user.get("permissions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required to view trial balance.")
    try:
        return {"status": "success", "data": db.get_trial_balance(as_of_date=as_of_date)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accounting/income-expenditure")
def get_income_expenditure_statement(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Generates Statement of Comprehensive Income (Operational Surplus and 50% statutory reserve)."""
    if not (user.get("is_executive") or "manage_accounting" in user.get("permissions", []) or "view_financial_statements" in user.get("permissions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required to view income statements.")
    try:
        return {"status": "success", "data": db.get_income_and_expenditure(date_from=date_from, date_to=date_to)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accounting/balance-sheet")
def get_balance_sheet(
    as_of_date: Optional[str] = Query(None, description="As of date (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Generates Statement of Financial Position (Balance Sheet: Assets == Liabilities + Equity)."""
    if not (user.get("is_executive") or "manage_accounting" in user.get("permissions", []) or "view_financial_statements" in user.get("permissions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required to view balance sheet.")
    try:
        return {"status": "success", "data": db.get_balance_sheet(as_of_date=as_of_date)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accounting/cash-flow")
def get_cash_flow_statement(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Generates Cash Flow Statement (Operating, Investing, Financing activities)."""
    if not (user.get("is_executive") or "manage_accounting" in user.get("permissions", []) or "view_financial_statements" in user.get("permissions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required to view cash flows.")
    try:
        return {"status": "success", "data": db.get_cash_flow_statement(date_from=date_from, date_to=date_to)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accounting/journal-entries")
def get_journal_entries(
    status_filter: Optional[str] = Query(None, alias="status", description="DRAFT, POSTED, or REJECTED"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Lists General Ledger journal entries with full line items."""
    if not (user.get("is_executive") or "manage_accounting" in user.get("permissions", []) or "view_financial_statements" in user.get("permissions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required to view journal entries.")
    try:
        return {"status": "success", "data": db.get_journal_entries(status=status_filter, limit=limit, offset=offset)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accounting/journal-entries")
def create_manual_journal_entry(
    payload: SubmitJournalEntryPayload,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Maker step: Drafts a balanced manual journal entry awaiting Checker approval."""
    if not (user.get("is_executive") or "post_manual_journal" in user.get("permissions", []) or "manage_accounting" in user.get("permissions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission required to draft manual journal entries.")
    try:
        res = db.submit_manual_journal_entry(
            entry_date=payload.entry_date,
            narration=payload.narration,
            lines=[l.dict() for l in payload.lines],
            created_by=user["id"],
            supporting_doc_url=payload.supporting_doc_url
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accounting/journal-entries/{entry_id}/approve")
def approve_manual_journal_entry(
    entry_id: int,
    payload: ApproveJournalEntryPayload,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Checker step: President / Auditor reviews and posts (or rejects) draft manual journal."""
    can_approve = (
        "approve_manual_journal" in user.get("permissions", []) or
        "PRESIDENT" in user.get("roles", []) or
        "SUPER_ADMIN" in user.get("roles", [])
    )
    if not can_approve:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Checker clearance (President / Auditor / Super Admin) required to review journals.")
    try:
        role = user.get("primary_role") or ("PRESIDENT" if "PRESIDENT" in user.get("roles", []) else "AUDITOR")
        res = db.approve_manual_journal_entry(
            entry_id=entry_id,
            officer_id=user["id"],
            officer_role=role,
            action=payload.action,
            rejection_reason=payload.rejection_reason
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accounting/sync-transactions")
def sync_transactions_to_general_ledger(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Reconciles and syncs historical transactions into double-entry General Ledger."""
    if not (user.get("is_executive") or "SUPER_ADMIN" in user.get("roles", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required for GL reconciliation.")
    try:
        return db.sync_transactions_to_general_ledger()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MODULE 5: DIVIDEND & ANNUAL SURPLUS DISTRIBUTION ENDPOINTS
# =============================================================================

@app.post("/api/dividends/simulate")
def simulate_dividend_distribution(
    payload: SimulateDividendPayload,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Executes dynamic annual dividend distribution simulation with custom weighting and qualification rules."""
    if not (user.get("is_executive") or "simulate_dividends" in user.get("permissions", []) or "manage_accounting" in user.get("permissions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required to simulate dividends.")
    try:
        sim = db.simulate_dividend_distribution(
            period_name=payload.period_name,
            financial_year_start=payload.financial_year_start,
            financial_year_end=payload.financial_year_end,
            net_surplus=payload.net_surplus,
            statutory_reserve_pct=payload.statutory_reserve_pct,
            weight_share_pct=payload.weight_share_pct,
            weight_savings_pct=payload.weight_savings_pct,
            weight_patronage_pct=payload.weight_patronage_pct,
            min_shares=payload.min_shares,
            min_months=payload.min_months,
            disqualify_arrears=payload.disqualify_arrears,
            simulated_by=user["id"]
        )
        return {"status": "success", "data": sim}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dividends/save-simulation")
def save_dividend_simulation(
    payload: SaveDividendPayload,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Persists a simulated dividend run as a period in AUDIT_REVIEW status."""
    if not (user.get("is_executive") or "simulate_dividends" in user.get("permissions", []) or "manage_accounting" in user.get("permissions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required to save dividend period.")
    try:
        return db.save_dividend_period(payload.simulation_data, officer_id=user["id"])
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dividends/periods")
def get_dividend_periods(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Lists all dividend distribution periods."""
    if not (user.get("is_executive") or "view_financial_statements" in user.get("permissions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required to view dividend periods.")
    try:
        return {"status": "success", "data": db.get_dividend_periods()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dividends/periods/{period_id}")
def get_dividend_period_details(
    period_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves full member-level allocation audit table for a dividend distribution period."""
    if not (user.get("is_executive") or "view_financial_statements" in user.get("permissions", [])):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Executive clearance required to view dividend details.")
    try:
        return {"status": "success", "data": db.get_dividend_period_details(period_id=period_id)}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dividends/periods/{period_id}/approve")
def approve_and_post_dividend(
    period_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Presidential sign-off: Disburses dividends, credits member savings, and posts double-entry GL."""
    can_approve = (
        "approve_dividends" in user.get("permissions", []) or
        "PRESIDENT" in user.get("roles", []) or
        "SUPER_ADMIN" in user.get("roles", [])
    )
    if not can_approve:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Presidential sign-off clearance required to post dividend distribution.")
    try:
        role = user.get("primary_role") or ("PRESIDENT" if "PRESIDENT" in user.get("roles", []) else "SUPER_ADMIN")
        return db.approve_and_post_dividend(period_id=period_id, officer_id=user["id"], officer_role=role)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/members/{member_id}/dividend-preference")
def get_member_dividend_preference(
    member_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves member's surplus distribution payout choice (SAVINGS_CREDIT vs BANK_TRANSFER)."""
    if member_id != user["id"] and not user.get("is_executive"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    try:
        conn = db.get_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute("SELECT id, member_code, dividend_payout_preference, bank_name, bank_account_number, bank_account_name FROM members WHERE id = %s;", (member_id,))
            m = cur.fetchone()
            if not m:
                raise HTTPException(status_code=404, detail="Member not found.")
            return {"status": "success", "data": m}
        finally:
            cur.close()
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/members/{member_id}/dividend-preference")
def update_member_dividend_preference(
    member_id: int,
    payload: UpdateDividendPreferencePayload,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Allows member to set their dividend payout choice."""
    if member_id != user["id"] and not user.get("is_executive"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    try:
        return db.update_member_dividend_payout_preference(member_id=member_id, payout_preference=payload.payout_preference)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/members/{member_id}/dividend-history")
def get_member_dividend_history(
    member_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Returns member's dividend distribution history."""
    if member_id != user["id"] and not user.get("is_executive"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    try:
        return {"status": "success", "data": db.get_member_dividend_history(member_id=member_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


app.mount("/uploads", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "uploads")), name="uploads")
app.mount("/", StaticFiles(directory=os.path.dirname(__file__), html=True), name="web")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("wbmf_api:app", host="127.0.0.1", port=8088, reload=True)
