-- =====================================================================
-- WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
-- COMPLETE SUPABASE POSTGRESQL SCHEMA (39 TABLES)
-- Statutory Jurisdiction: Lagos State Cooperative Societies Law (Cap C15)
-- Official Secretariat Email: wealthbridge.coopsociety@gmail.com
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ---------------------------------------------------------------------
-- Table: system_config
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(64) NOT NULL UNIQUE,
    config_value VARCHAR(255) NOT NULL,
    description VARCHAR(255),
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: roles
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.roles (
    id SERIAL PRIMARY KEY,
    role_code VARCHAR(50) NOT NULL UNIQUE,
    role_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: permissions
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.permissions (
    id SERIAL PRIMARY KEY,
    perm_key VARCHAR(60) NOT NULL UNIQUE,
    perm_name VARCHAR(120) NOT NULL,
    module VARCHAR(50) NOT NULL,
    description TEXT
);

-- ---------------------------------------------------------------------
-- Table: role_permissions
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.role_permissions (
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    PRIMARY KEY (role_id, permission_id)
);

-- ---------------------------------------------------------------------
-- Table: admin_users
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.admin_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'SUPER_ADMIN',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMPTZ
);

-- ---------------------------------------------------------------------
-- Table: members
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.members (
    id SERIAL PRIMARY KEY,
    member_code VARCHAR(20) NOT NULL UNIQUE,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    other_names VARCHAR(50),
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255),
    phone VARCHAR(20) NOT NULL UNIQUE,
    gender TEXT CHECK (gender IN ('MALE','FEMALE')) NOT NULL,
    marital_status TEXT CHECK (marital_status IN ('SINGLE','MARRIED','DIVORCED','WIDOWED')) DEFAULT 'SINGLE',
    date_of_birth DATE,
    residential_address TEXT NOT NULL,
    identification_type TEXT CHECK (identification_type IN ('NIN','PASSPORT','VOTERS_CARD','DRIVERS_LICENSE')) NOT NULL,
    identification_number VARCHAR(50) NOT NULL,
    passport_photo TEXT,
    employment_status TEXT CHECK (employment_status IN ('SALARY_EARNER','BUSINESS_OWNER','PROFESSIONAL','OTHER')) NOT NULL,
    employer_or_business_name VARCHAR(150),
    bank_name VARCHAR(100),
    bank_account_number VARCHAR(20),
    bank_account_name VARCHAR(150),
    bvn VARCHAR(20),
    monthly_income_verified NUMERIC(15,2) DEFAULT 0.00,
    contribution_tier TEXT CHECK (contribution_tier IN ('STANDARD','PLUS','PREMIUM')) DEFAULT 'STANDARD',
    dividend_payout_preference TEXT CHECK (dividend_payout_preference IN ('SAVINGS_CREDIT','BANK_TRANSFER')) DEFAULT 'SAVINGS_CREDIT',
    kyc_completion_percent INTEGER DEFAULT 20,
    pending_email VARCHAR(100),
    pending_phone VARCHAR(20),
    pending_address TEXT,
    contact_change_status TEXT CHECK (contact_change_status IN ('NONE','PENDING_APPROVAL','APPROVED','REJECTED')) DEFAULT 'NONE',
    contact_change_requested_at TIMESTAMPTZ,
    contact_change_reviewed_by INTEGER,
    contact_change_reviewed_at TIMESTAMPTZ,
    status TEXT CHECK (status IN ('PENDING_KYC','ACTIVE','SUSPENDED','EXITED','DECEASED')) NOT NULL DEFAULT 'PENDING_KYC',
    admission_date DATE,
    exit_date DATE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    paystack_customer_code VARCHAR(100),
    paystack_dva_account_number VARCHAR(20),
    paystack_dva_bank_name VARCHAR(100),
    paystack_dva_account_name VARCHAR(150),
    paystack_auth_code VARCHAR(100)
);

-- ---------------------------------------------------------------------
-- Table: next_of_kin
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.next_of_kin (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    relationship VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    residential_address TEXT NOT NULL,
    allocation_percentage NUMERIC(5,2) DEFAULT 100.00,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: member_roles
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.member_roles (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    assigned_by_user_id INTEGER,
    assigned_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: officers
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.officers (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL,
    portfolio TEXT CHECK (portfolio IN ('PRESIDENT','VICE_PRESIDENT','GENERAL_SECRETARY','TREASURER','FINANCIAL_SECRETARY','LEGAL_COMPLIANCE_LEAD','TECHNOLOGY_SYSTEMS_LEAD','WELFARE_SECRETARY','PUBLIC_RELATIONS_OFFICER')) NOT NULL,
    appointment_date DATE NOT NULL,
    tenure_end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: chart_of_accounts
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.chart_of_accounts (
    id SERIAL PRIMARY KEY,
    account_code VARCHAR(16) NOT NULL UNIQUE,
    account_name VARCHAR(128) NOT NULL,
    account_type TEXT CHECK (account_type IN ('ASSET','LIABILITY','EQUITY','INCOME','EXPENSE')) NOT NULL,
    description VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_system_controlled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: journal_entries
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.journal_entries (
    id SERIAL PRIMARY KEY,
    entry_number VARCHAR(64) NOT NULL UNIQUE,
    entry_date DATE NOT NULL,
    source_module TEXT CHECK (source_module IN ('REMITTANCE_WATERFALL','LOAN_DISBURSEMENT','LOAN_REPAYMENT','EXIT_SETTLEMENT','WELFARE_PAYOUT','DIVIDEND_DISTRIBUTION','MANUAL_JOURNAL','LOAN_FORECLOSURE')) NOT NULL,
    source_reference VARCHAR(128),
    narration TEXT NOT NULL,
    total_debit NUMERIC(15,2) NOT NULL,
    total_credit NUMERIC(15,2) NOT NULL,
    is_balanced BOOLEAN DEFAULT TRUE,
    status TEXT CHECK (status IN ('DRAFT','POSTED','REJECTED')) DEFAULT 'POSTED',
    created_by INTEGER,
    approved_by INTEGER,
    approved_at TIMESTAMPTZ,
    supporting_doc_url VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: journal_entry_lines
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.journal_entry_lines (
    id SERIAL PRIMARY KEY,
    journal_entry_id INTEGER NOT NULL,
    account_id INTEGER NOT NULL,
    line_type TEXT CHECK (line_type IN ('DEBIT','CREDIT')) NOT NULL,
    amount NUMERIC(15,2) NOT NULL,
    memo VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: savings_accounts
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.savings_accounts (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL UNIQUE,
    total_balance NUMERIC(15,2) DEFAULT 0.00,
    encumbered_balance NUMERIC(15,2) DEFAULT 0.00,
    available_balance NUMERIC(15,2) GENERATED ALWAYS AS (total_balance - encumbered_balance) STORED,
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: share_accounts
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.share_accounts (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL UNIQUE,
    units_held INTEGER DEFAULT 0,
    paid_up_amount NUMERIC(15,2) DEFAULT 0.00,
    is_minimum_met BOOLEAN DEFAULT FALSE,
    benefits_qualified BOOLEAN DEFAULT FALSE,
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: welfare_accounts
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.welfare_accounts (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL UNIQUE,
    cumulative_contributions NUMERIC(15,2) DEFAULT 0.00,
    consecutive_months_active INTEGER DEFAULT 0,
    last_contribution_date DATE,
    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: target_savings_accounts
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.target_savings_accounts (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL,
    target_type TEXT CHECK (target_type IN ('BIRTHDAY','CHRISTMAS','ILEYA','BUILDING','PILGRIMAGE','EDUCATION','OTHERS')) NOT NULL,
    title VARCHAR(150) NOT NULL,
    target_amount NUMERIC(15,2) NOT NULL,
    current_balance NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    start_date DATE NOT NULL,
    maturity_date DATE NOT NULL,
    auto_save_amount NUMERIC(15,2) DEFAULT 0.00,
    status TEXT CHECK (status IN ('ACTIVE','MATURED','WITHDRAWN','CANCELLED')) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: target_savings_transactions
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.target_savings_transactions (
    id SERIAL PRIMARY KEY,
    target_account_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    transaction_type TEXT CHECK (transaction_type IN ('DEPOSIT','WITHDRAWAL','INTEREST_DIVIDEND')) NOT NULL,
    amount NUMERIC(15,2) NOT NULL,
    balance_after NUMERIC(15,2) NOT NULL,
    payment_method VARCHAR(50) DEFAULT 'POLARIS_BANK_TRANSFER',
    channel_reference VARCHAR(100) NOT NULL,
    narration TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: transactions
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.transactions (
    id SERIAL PRIMARY KEY,
    transaction_ref VARCHAR(64) NOT NULL UNIQUE,
    member_id INTEGER NOT NULL,
    transaction_type TEXT CHECK (transaction_type IN ('CREDIT','DEBIT')) NOT NULL,
    ledger_category TEXT CHECK (ledger_category IN ('SAVINGS','SHARE_CAPITAL','WELFARE_FUND','REGISTRATION_FEE','PASSBOOK_FEE','LOAN_DISBURSEMENT','LOAN_REPAYMENT','WELFARE_GRANT','DISCIPLINARY_FINE','MARKETPLACE_SETTLEMENT')) NOT NULL,
    amount NUMERIC(15,2) NOT NULL,
    payment_method TEXT CHECK (payment_method IN ('POLARIS_BANK_TRANSFER','DIRECT_DEBIT','ONLINE_GATEWAY','INTERNAL_SET_OFF')) NOT NULL,
    channel_reference VARCHAR(100),
    narration VARCHAR(255) NOT NULL,
    status TEXT CHECK (status IN ('PENDING','VERIFIED','REJECTED')) DEFAULT 'PENDING',
    verified_by_officer_id INTEGER,
    transaction_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: payment_advices
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.payment_advices (
    id SERIAL PRIMARY KEY,
    advice_reference VARCHAR(64) NOT NULL UNIQUE,
    member_id INTEGER NOT NULL,
    billing_period VARCHAR(7) NOT NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    tier_at_issuance TEXT CHECK (tier_at_issuance IN ('STANDARD','PLUS','PREMIUM')) NOT NULL DEFAULT 'STANDARD',
    amount_fines NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    amount_registration_fee NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    amount_loan_repayment NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    amount_welfare NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    amount_share_capital NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    amount_regular_savings NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    amount_target_savings NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    amount_arrears NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    total_expected_amount NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    paid_fines NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    paid_registration NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    paid_loan NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    paid_welfare NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    paid_shares NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    paid_savings NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    paid_targets NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    total_amount_paid NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    outstanding_balance NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    status TEXT CHECK (status IN ('DUE','PARTIALLY_PAID','FULLY_SETTLED','OVERDUE')) NOT NULL DEFAULT 'DUE',
    admin_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: payment_advice_distributions
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.payment_advice_distributions (
    id SERIAL PRIMARY KEY,
    advice_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    payment_reference VARCHAR(128) NOT NULL,
    payment_method VARCHAR(64) NOT NULL DEFAULT 'PAYSTACK_DVA',
    total_payment_received NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    allocated_fines NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    allocated_registration NUMERIC(15,2) DEFAULT 0.00,
    allocated_loan NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    allocated_welfare NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    allocated_shares NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    allocated_savings NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    allocated_targets NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    allocated_surplus_savings NUMERIC(12,2) NOT NULL DEFAULT 0.00,
    narration VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: disciplinary_fines
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.disciplinary_fines (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL,
    infraction_type TEXT CHECK (infraction_type IN ('LATE_MONTHLY_REMITTANCE','MEETING_ABSENTEEISM','MEETING_LATENESS','UNAUTHORIZED_REPRESENTATION','CODE_OF_CONDUCT_BREACH')) NOT NULL,
    fine_amount NUMERIC(15,2) NOT NULL,
    reason TEXT NOT NULL,
    status TEXT CHECK (status IN ('UNPAID','SETTLED','WAIVED')) DEFAULT 'UNPAID',
    issued_date DATE NOT NULL,
    settled_date DATE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: loan_products
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.loan_products (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    product_code VARCHAR(30) NOT NULL UNIQUE,
    description TEXT,
    min_membership_months INTEGER DEFAULT 6,
    max_multiplier_of_savings NUMERIC(3,1) DEFAULT 2.0,
    max_principal_ceiling NUMERIC(15,2) NOT NULL,
    admin_cost_fee_percent NUMERIC(5,2) NOT NULL,
    min_tenure_months INTEGER DEFAULT 1,
    max_tenure_months INTEGER DEFAULT 12,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: loans
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.loans (
    id SERIAL PRIMARY KEY,
    loan_reference VARCHAR(50) NOT NULL UNIQUE,
    member_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    principal_amount NUMERIC(15,2) NOT NULL,
    admin_cost_fee NUMERIC(15,2) NOT NULL,
    total_amount_payable NUMERIC(15,2) NOT NULL,
    tenure_months INTEGER NOT NULL,
    monthly_installment NUMERIC(15,2) NOT NULL,
    total_paid NUMERIC(15,2) DEFAULT 0.00,
    outstanding_balance NUMERIC(15,2) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    application_date DATE NOT NULL,
    approval_date DATE,
    disbursement_date DATE,
    next_due_date DATE,
    maturity_date DATE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    approval_level_percent INTEGER DEFAULT 0,
    current_approval_stage VARCHAR(40) DEFAULT 'CREDIT_COMMITTEE',
    presidential_override BOOLEAN DEFAULT FALSE,
    decline_reason TEXT,
    declined_by_officer_id INTEGER,
    declined_by_role VARCHAR(50),
    purpose_narration TEXT
);

-- ---------------------------------------------------------------------
-- Table: loan_approval_steps
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.loan_approval_steps (
    id SERIAL PRIMARY KEY,
    loan_id INTEGER NOT NULL,
    step_name VARCHAR(50) NOT NULL,
    officer_id INTEGER NOT NULL,
    officer_role VARCHAR(80) NOT NULL,
    action TEXT CHECK (action IN ('APPROVED','DECLINED','OVERRIDDEN')) NOT NULL,
    comments TEXT,
    percentage_granted INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: loan_guarantors
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.loan_guarantors (
    id SERIAL PRIMARY KEY,
    loan_id INTEGER NOT NULL,
    guarantor_member_id INTEGER NOT NULL,
    guaranteed_amount NUMERIC(15,2) NOT NULL,
    lien_encumbered_amount NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    status TEXT CHECK (status IN ('PENDING_CONSENT','ACCEPTED','DECLINED','RELEASED','INVOKED')) NOT NULL DEFAULT 'PENDING_CONSENT',
    accepted_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ
);

-- ---------------------------------------------------------------------
-- Table: loan_repayments
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.loan_repayments (
    id SERIAL PRIMARY KEY,
    loan_id INTEGER NOT NULL,
    installment_number INTEGER NOT NULL,
    due_date DATE NOT NULL,
    amount_due NUMERIC(15,2) NOT NULL,
    amount_paid NUMERIC(15,2) DEFAULT 0.00,
    paid_date TIMESTAMPTZ,
    transaction_ref VARCHAR(64),
    status TEXT CHECK (status IN ('PENDING','PARTIAL','PAID','OVERDUE')) DEFAULT 'PENDING'
);

-- ---------------------------------------------------------------------
-- Table: loan_appeals
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.loan_appeals (
    id SERIAL PRIMARY KEY,
    loan_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    appeal_comments TEXT NOT NULL,
    attached_document_path VARCHAR(255),
    document_name VARCHAR(150),
    document_mime_type VARCHAR(80),
    target_officer_id INTEGER,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING_REVIEW',
    review_response TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ
);

-- ---------------------------------------------------------------------
-- Table: welfare_claims
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.welfare_claims (
    id SERIAL PRIMARY KEY,
    claim_code VARCHAR(50) NOT NULL UNIQUE,
    member_id INTEGER NOT NULL,
    benefit_category TEXT CHECK (benefit_category IN ('MEMBER_BEREAVEMENT','SPOUSE_BEREAVEMENT','CHILD_BEREAVEMENT','PARENT_BEREAVEMENT','EMERGENCY_MEDICAL_GRANT','MEMBER_WEDDING','CHILDBIRTH_NAMING','RETIREMENT_LANDMARK')) NOT NULL,
    tariff_amount NUMERIC(15,2) NOT NULL,
    amount_disbursed NUMERIC(15,2) DEFAULT 0.00,
    evidence_doc_reference VARCHAR(255),
    status TEXT CHECK (status IN ('SUBMITTED','VETTED','EXECUTIVE_APPROVED','REJECTED','DISBURSED')) DEFAULT 'SUBMITTED',
    submission_date DATE NOT NULL,
    disbursed_date DATE,
    welfare_secretary_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: marketplace_merchants
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.marketplace_merchants (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL UNIQUE,
    business_trading_name VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    status TEXT CHECK (status IN ('PENDING_APPROVAL','APPROVED','SUSPENDED')) DEFAULT 'PENDING_APPROVAL',
    registered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: marketplace_products
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.marketplace_products (
    id SERIAL PRIMARY KEY,
    merchant_id INTEGER NOT NULL,
    product_title VARCHAR(150) NOT NULL,
    description TEXT,
    price NUMERIC(15,2) NOT NULL,
    is_financing_eligible BOOLEAN DEFAULT TRUE,
    stock_quantity INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: general_meetings
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.general_meetings (
    id SERIAL PRIMARY KEY,
    meeting_type TEXT CHECK (meeting_type IN ('ANNUAL_GENERAL_MEETING','SPECIAL_GENERAL_MEETING','MONTHLY_EXECUTIVE')) NOT NULL,
    meeting_title VARCHAR(150) NOT NULL,
    meeting_date DATE NOT NULL,
    minute_reference_doc VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: meeting_attendance
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.meeting_attendance (
    id SERIAL PRIMARY KEY,
    meeting_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    attendance_status TEXT CHECK (attendance_status IN ('PRESENT','ABSENT_WITH_APOLOGY','ABSENT_WITHOUT_APOLOGY')) NOT NULL,
    arrival_time TIME
);

-- ---------------------------------------------------------------------
-- Table: member_exits
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.member_exits (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL,
    exit_type TEXT CHECK (exit_type IN ('VOLUNTARY_WITHDRAWAL','DEATH_ESTATE_SETTLEMENT','EXPULSION')) NOT NULL DEFAULT 'VOLUNTARY_WITHDRAWAL',
    notice_date DATE NOT NULL,
    statutory_notice_expiry_date DATE NOT NULL,
    reason TEXT,
    supporting_doc_url VARCHAR(500),
    nok_claimant_name VARCHAR(150),
    nok_claimant_phone VARCHAR(30),
    nok_relationship VARCHAR(50),
    status TEXT CHECK (status IN ('PENDING_CLEARANCE','FINANCIALLY_CLEARED','SETTLED_REFUNDED','REJECTED')) NOT NULL DEFAULT 'PENDING_CLEARANCE',
    total_savings_at_exit NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    total_target_savings_at_exit NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    total_shares_at_exit NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    outstanding_loans_at_exit NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    outstanding_fines_at_exit NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    active_guarantor_commitments_count INTEGER NOT NULL DEFAULT 0,
    exit_processing_fee NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    bereavement_welfare_grant NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    net_refund_amount NUMERIC(15,2) NOT NULL DEFAULT 0.00,
    cleared_by_officer_id INTEGER,
    approved_by_president_id INTEGER,
    rejection_reason TEXT,
    refund_payment_ref VARCHAR(100),
    refund_disbursed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: dividend_periods
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.dividend_periods (
    id SERIAL PRIMARY KEY,
    period_name VARCHAR(64) NOT NULL,
    financial_year_start DATE NOT NULL,
    financial_year_end DATE NOT NULL,
    net_surplus_amount NUMERIC(15,2) NOT NULL,
    statutory_reserve_percent NUMERIC(5,2) DEFAULT 50.00,
    statutory_reserve_amount NUMERIC(15,2) NOT NULL,
    distributable_pool_amount NUMERIC(15,2) NOT NULL,
    weight_share_capital_percent NUMERIC(5,2) DEFAULT 60.00,
    weight_savings_volume_percent NUMERIC(5,2) DEFAULT 40.00,
    weight_patronage_percent NUMERIC(5,2) DEFAULT 0.00,
    min_share_units_required INTEGER DEFAULT 5,
    min_active_months_required INTEGER DEFAULT 6,
    disqualify_active_arrears BOOLEAN DEFAULT TRUE,
    total_qualified_members INTEGER DEFAULT 0,
    total_disqualified_members INTEGER DEFAULT 0,
    status TEXT CHECK (status IN ('DRAFT_SIMULATION','AUDIT_REVIEW','APPROVED_POSTED','CANCELLED')) DEFAULT 'DRAFT_SIMULATION',
    simulated_by_user_id INTEGER,
    approved_by_president_id INTEGER,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: dividend_allocations
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.dividend_allocations (
    id SERIAL PRIMARY KEY,
    dividend_period_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    shares_held INTEGER NOT NULL,
    share_equity_amount NUMERIC(15,2) NOT NULL,
    savings_balance NUMERIC(15,2) NOT NULL,
    loan_patronage_volume NUMERIC(15,2) DEFAULT 0.00,
    is_qualified BOOLEAN NOT NULL,
    disqualification_reason VARCHAR(255),
    dividend_from_shares NUMERIC(15,2) DEFAULT 0.00,
    dividend_from_savings NUMERIC(15,2) DEFAULT 0.00,
    dividend_from_patronage NUMERIC(15,2) DEFAULT 0.00,
    total_dividend_payable NUMERIC(15,2) NOT NULL,
    payout_preference TEXT CHECK (payout_preference IN ('SAVINGS_CREDIT','BANK_TRANSFER')) DEFAULT 'SAVINGS_CREDIT',
    payout_status TEXT CHECK (payout_status IN ('PENDING','CREDITED_TO_SAVINGS','DISBURSED_TO_BANK')) DEFAULT 'PENDING',
    payout_reference VARCHAR(128),
    settled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: system_notifications
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.system_notifications (
    id SERIAL PRIMARY KEY,
    recipient_type TEXT CHECK (recipient_type IN ('MEMBER','OFFICER','ALL_ADMIN')) NOT NULL,
    recipient_id INTEGER,
    category VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    severity TEXT CHECK (severity IN ('INFO','WARNING','CRITICAL','DANGER')) DEFAULT 'INFO',
    reference_type VARCHAR(50),
    reference_id VARCHAR(100),
    milestone_tier INTEGER DEFAULT 0,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: audit_logs
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    actor_name VARCHAR(150) NOT NULL,
    actor_role VARCHAR(80) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    details_before JSONB,
    details_after JSONB,
    summary VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: manual_bank_payments
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.manual_bank_payments (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL,
    amount NUMERIC(15,2) NOT NULL,
    payment_date DATE NOT NULL,
    bank_name VARCHAR(100) DEFAULT 'Polaris Bank Limited',
    payment_reference VARCHAR(100) NOT NULL,
    narration VARCHAR(255),
    receipt_file_path VARCHAR(255),
    receipt_mime_type VARCHAR(80),
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING_RECONCILIATION',
    verified_by_officer_id INTEGER,
    verified_at TIMESTAMPTZ,
    rejection_reason VARCHAR(255),
    distribution_json JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Table: paystack_webhook_logs
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.paystack_webhook_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    reference VARCHAR(100) NOT NULL UNIQUE,
    member_id INTEGER,
    amount NUMERIC(15,2) NOT NULL,
    channel VARCHAR(50) DEFAULT 'dedicated_nuban',
    payload JSONB NOT NULL,
    status TEXT CHECK (status IN ('PROCESSED','IGNORED','FAILED')) DEFAULT 'PROCESSED',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE public.system_config ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for system_config" ON public.system_config;
CREATE POLICY "Permissive full access for system_config" ON public.system_config FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for roles" ON public.roles;
CREATE POLICY "Permissive full access for roles" ON public.roles FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.permissions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for permissions" ON public.permissions;
CREATE POLICY "Permissive full access for permissions" ON public.permissions FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.role_permissions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for role_permissions" ON public.role_permissions;
CREATE POLICY "Permissive full access for role_permissions" ON public.role_permissions FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.admin_users ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for admin_users" ON public.admin_users;
CREATE POLICY "Permissive full access for admin_users" ON public.admin_users FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.members ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for members" ON public.members;
CREATE POLICY "Permissive full access for members" ON public.members FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.next_of_kin ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for next_of_kin" ON public.next_of_kin;
CREATE POLICY "Permissive full access for next_of_kin" ON public.next_of_kin FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.member_roles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for member_roles" ON public.member_roles;
CREATE POLICY "Permissive full access for member_roles" ON public.member_roles FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.officers ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for officers" ON public.officers;
CREATE POLICY "Permissive full access for officers" ON public.officers FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.chart_of_accounts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for chart_of_accounts" ON public.chart_of_accounts;
CREATE POLICY "Permissive full access for chart_of_accounts" ON public.chart_of_accounts FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.journal_entries ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for journal_entries" ON public.journal_entries;
CREATE POLICY "Permissive full access for journal_entries" ON public.journal_entries FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.journal_entry_lines ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for journal_entry_lines" ON public.journal_entry_lines;
CREATE POLICY "Permissive full access for journal_entry_lines" ON public.journal_entry_lines FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.savings_accounts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for savings_accounts" ON public.savings_accounts;
CREATE POLICY "Permissive full access for savings_accounts" ON public.savings_accounts FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.share_accounts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for share_accounts" ON public.share_accounts;
CREATE POLICY "Permissive full access for share_accounts" ON public.share_accounts FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.welfare_accounts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for welfare_accounts" ON public.welfare_accounts;
CREATE POLICY "Permissive full access for welfare_accounts" ON public.welfare_accounts FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.target_savings_accounts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for target_savings_accounts" ON public.target_savings_accounts;
CREATE POLICY "Permissive full access for target_savings_accounts" ON public.target_savings_accounts FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.target_savings_transactions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for target_savings_transactions" ON public.target_savings_transactions;
CREATE POLICY "Permissive full access for target_savings_transactions" ON public.target_savings_transactions FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for transactions" ON public.transactions;
CREATE POLICY "Permissive full access for transactions" ON public.transactions FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.payment_advices ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for payment_advices" ON public.payment_advices;
CREATE POLICY "Permissive full access for payment_advices" ON public.payment_advices FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.payment_advice_distributions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for payment_advice_distributions" ON public.payment_advice_distributions;
CREATE POLICY "Permissive full access for payment_advice_distributions" ON public.payment_advice_distributions FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.disciplinary_fines ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for disciplinary_fines" ON public.disciplinary_fines;
CREATE POLICY "Permissive full access for disciplinary_fines" ON public.disciplinary_fines FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.loan_products ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for loan_products" ON public.loan_products;
CREATE POLICY "Permissive full access for loan_products" ON public.loan_products FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.loans ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for loans" ON public.loans;
CREATE POLICY "Permissive full access for loans" ON public.loans FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.loan_approval_steps ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for loan_approval_steps" ON public.loan_approval_steps;
CREATE POLICY "Permissive full access for loan_approval_steps" ON public.loan_approval_steps FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.loan_guarantors ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for loan_guarantors" ON public.loan_guarantors;
CREATE POLICY "Permissive full access for loan_guarantors" ON public.loan_guarantors FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.loan_repayments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for loan_repayments" ON public.loan_repayments;
CREATE POLICY "Permissive full access for loan_repayments" ON public.loan_repayments FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.loan_appeals ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for loan_appeals" ON public.loan_appeals;
CREATE POLICY "Permissive full access for loan_appeals" ON public.loan_appeals FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.welfare_claims ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for welfare_claims" ON public.welfare_claims;
CREATE POLICY "Permissive full access for welfare_claims" ON public.welfare_claims FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.marketplace_merchants ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for marketplace_merchants" ON public.marketplace_merchants;
CREATE POLICY "Permissive full access for marketplace_merchants" ON public.marketplace_merchants FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.marketplace_products ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for marketplace_products" ON public.marketplace_products;
CREATE POLICY "Permissive full access for marketplace_products" ON public.marketplace_products FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.general_meetings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for general_meetings" ON public.general_meetings;
CREATE POLICY "Permissive full access for general_meetings" ON public.general_meetings FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.meeting_attendance ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for meeting_attendance" ON public.meeting_attendance;
CREATE POLICY "Permissive full access for meeting_attendance" ON public.meeting_attendance FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.member_exits ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for member_exits" ON public.member_exits;
CREATE POLICY "Permissive full access for member_exits" ON public.member_exits FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.dividend_periods ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for dividend_periods" ON public.dividend_periods;
CREATE POLICY "Permissive full access for dividend_periods" ON public.dividend_periods FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.dividend_allocations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for dividend_allocations" ON public.dividend_allocations;
CREATE POLICY "Permissive full access for dividend_allocations" ON public.dividend_allocations FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.system_notifications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for system_notifications" ON public.system_notifications;
CREATE POLICY "Permissive full access for system_notifications" ON public.system_notifications FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for audit_logs" ON public.audit_logs;
CREATE POLICY "Permissive full access for audit_logs" ON public.audit_logs FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.manual_bank_payments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for manual_bank_payments" ON public.manual_bank_payments;
CREATE POLICY "Permissive full access for manual_bank_payments" ON public.manual_bank_payments FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.paystack_webhook_logs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Permissive full access for paystack_webhook_logs" ON public.paystack_webhook_logs;
CREATE POLICY "Permissive full access for paystack_webhook_logs" ON public.paystack_webhook_logs FOR ALL USING (true) WITH CHECK (true);
