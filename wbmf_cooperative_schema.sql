-- =====================================================================
-- WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
-- DATABASE SCHEMA: wbmf
-- Reference: SOP-WMC-2026-V1 & WMC-BYELAWS-REV-2026-V1
-- Official Email: wealthbridge.coopsociety@gmail.com
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `wbmf`
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE `wbmf`;

-- ---------------------------------------------------------------------
-- 1. SYSTEM CONFIGURATION & REGULATORY INVARIANTS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `system_config` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `config_key` VARCHAR(64) NOT NULL UNIQUE,
    `config_value` VARCHAR(255) NOT NULL,
    `description` VARCHAR(255) NULL,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `system_config` (`config_key`, `config_value`, `description`) VALUES
('SOCIETY_NAME', 'Wealthbridge Multipurpose Cooperative Society Limited', 'Official legal name'),
('OFFICIAL_EMAIL', 'wealthbridge.coopsociety@gmail.com', 'Official Secretariat Email invariant'),
('OFFICIAL_PHONE', '+234 800 000 0000', 'Secretariat Helpdesk Contact'),
('REGISTERED_ADDRESS', '13, Agbaje Iloro Street, Odogunyan, Ikorodu, Lagos State, Nigeria', 'Statutory physical secretariat'),
('BANK_NAME', 'Polaris Bank Limited', 'Corporate operational banking partner'),
('SHARE_UNIT_PRICE', '1000', 'Nominal price per ordinary share unit in NGN'),
('MIN_SHARE_UNITS', '5', 'Mandatory minimum share units (NGN 5,000) for benefit qualification'),
('MAX_SHARE_UNITS', '200', 'Statutory 20% anti-monopoly ceiling (NGN 200,000) for Year 1'),
('TARGET_SHARE_CAPITAL', '1000000', 'First-year target share capital in NGN'),
('MONTHLY_DUE_DAY', '28', 'Monthly contribution deadline day of each month'),
('WELFARE_MONTHLY_LEVY', '1000', 'Fixed monthly welfare levy per member in NGN'),
('REGISTRATION_FEE', '5000', 'One-time onboarding registration fee in NGN'),
('PASSBOOK_FEE', '2000', 'Passbook and digital ID issuance fee in NGN')
ON DUPLICATE KEY UPDATE `config_value` = VALUES(`config_value`);

-- ---------------------------------------------------------------------
-- 2. MEMBERSHIP REGISTRY (Core CRM & KYC)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `members` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `member_code` VARCHAR(20) NOT NULL UNIQUE COMMENT 'e.g. WMC-2026-001',
    `first_name` VARCHAR(50) NOT NULL,
    `last_name` VARCHAR(50) NOT NULL,
    `other_names` VARCHAR(50) NULL,
    `email` VARCHAR(100) NOT NULL UNIQUE,
    `password_hash` VARCHAR(255) NULL COMMENT 'Bcrypt or salted SHA256 hashed password',
    `phone` VARCHAR(20) NOT NULL UNIQUE,
    `gender` ENUM('MALE', 'FEMALE') NOT NULL,
    `marital_status` ENUM('SINGLE', 'MARRIED', 'DIVORCED', 'WIDOWED') DEFAULT 'SINGLE',
    `date_of_birth` DATE NULL,
    `residential_address` TEXT NOT NULL,
    `identification_type` ENUM('NIN', 'PASSPORT', 'VOTERS_CARD', 'DRIVERS_LICENSE') NOT NULL,
    `identification_number` VARCHAR(50) NOT NULL,
    `passport_photo` LONGTEXT NULL COMMENT 'Base64 encoded photograph data',
    `employment_status` ENUM('SALARY_EARNER', 'BUSINESS_OWNER', 'PROFESSIONAL', 'OTHER') NOT NULL,
    `employer_or_business_name` VARCHAR(150) NULL,
    `bank_name` VARCHAR(100) NULL,
    `bank_account_number` VARCHAR(20) NULL,
    `bank_account_name` VARCHAR(150) NULL,
    `bvn` VARCHAR(20) NULL,
    `monthly_income_verified` DECIMAL(15, 2) DEFAULT 0.00,
    `contribution_tier` ENUM('STANDARD', 'PLUS', 'PREMIUM') DEFAULT 'STANDARD' COMMENT 'Standard: 10k, Plus: 25k, Premium: 50k+',
    `kyc_completion_percent` INT DEFAULT 20 COMMENT 'Calculated profile completion score (0-100%)',
    `pending_email` VARCHAR(100) NULL COMMENT 'Awaiting President & General Secretary sign-off',
    `pending_phone` VARCHAR(20) NULL COMMENT 'Awaiting President & General Secretary sign-off',
    `pending_address` TEXT NULL COMMENT 'Awaiting President & General Secretary sign-off',
    `contact_change_status` ENUM('NONE', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED') DEFAULT 'NONE',
    `contact_change_requested_at` DATETIME NULL,
    `contact_change_reviewed_by` INT NULL,
    `contact_change_reviewed_at` DATETIME NULL,
    `status` ENUM('PENDING_KYC', 'ACTIVE', 'SUSPENDED', 'EXITED') DEFAULT 'PENDING_KYC',
    `admission_date` DATE NULL,
    `exit_date` DATE NULL,
    `last_login` DATETIME NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX `idx_member_status` (`status`),
    INDEX `idx_member_email` (`email`),
    INDEX `idx_member_phone` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 3. BENEFICIARY & NEXT OF KIN (Article 11)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `next_of_kin` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `member_id` INT NOT NULL,
    `full_name` VARCHAR(100) NOT NULL,
    `relationship` VARCHAR(50) NOT NULL,
    `phone` VARCHAR(20) NOT NULL,
    `email` VARCHAR(100) NULL,
    `residential_address` TEXT NOT NULL,
    `allocation_percentage` DECIMAL(5, 2) DEFAULT 100.00,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`member_id`) REFERENCES `members`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Dual-control approvals for changes to a member's contact details.
CREATE TABLE IF NOT EXISTS `contact_change_approvals` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `member_id` INT NOT NULL,
    `officer_id` INT NOT NULL,
    `officer_portfolio` ENUM('PRESIDENT', 'GENERAL_SECRETARY') NOT NULL,
    `approved_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_contact_change_approver` (`member_id`, `officer_id`),
    FOREIGN KEY (`member_id`) REFERENCES `members`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`officer_id`) REFERENCES `members`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 4. GOVERNANCE & EXECUTIVE BOARD (Article 15)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `officers` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `member_id` INT NOT NULL,
    `portfolio` ENUM(
        'PRESIDENT',
        'VICE_PRESIDENT',
        'GENERAL_SECRETARY',
        'TREASURER',
        'FINANCIAL_SECRETARY',
        'LEGAL_COMPLIANCE_LEAD',
        'TECHNOLOGY_SYSTEMS_LEAD',
        'WELFARE_SECRETARY',
        'PUBLIC_RELATIONS_OFFICER'
    ) NOT NULL,
    `appointment_date` DATE NOT NULL,
    `tenure_end_date` DATE NULL,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`member_id`) REFERENCES `members`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 5. TRIPARTITE ACCOUNT LEDGERS (Article 12 & 13)
-- ---------------------------------------------------------------------
-- 5a. Share Capital Ledger (Permanent Equity)
CREATE TABLE IF NOT EXISTS `share_accounts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `member_id` INT NOT NULL UNIQUE,
    `units_held` INT DEFAULT 0 COMMENT '1 unit = N1,000',
    `paid_up_amount` DECIMAL(15, 2) DEFAULT 0.00,
    `is_minimum_met` BOOLEAN DEFAULT FALSE COMMENT 'True if units_held >= 5 (N5,000)',
    `benefits_qualified` BOOLEAN DEFAULT FALSE COMMENT 'Mandatory requirement for loans, voting & welfare',
    `last_updated` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`member_id`) REFERENCES `members`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5b. Regular Savings Ledger (Primary Cash Collateral)
CREATE TABLE IF NOT EXISTS `savings_accounts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `member_id` INT NOT NULL UNIQUE,
    `total_balance` DECIMAL(15, 2) DEFAULT 0.00,
    `encumbered_balance` DECIMAL(15, 2) DEFAULT 0.00 COMMENT 'Held as collateral for personal loans or guarantees',
    `available_balance` DECIMAL(15, 2) GENERATED ALWAYS AS (`total_balance` - `encumbered_balance`) STORED,
    `last_updated` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`member_id`) REFERENCES `members`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5c. Member Welfare Fund Ledger (Mutual Solidarity Pool)
CREATE TABLE IF NOT EXISTS `welfare_accounts` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `member_id` INT NOT NULL UNIQUE,
    `cumulative_contributions` DECIMAL(15, 2) DEFAULT 0.00 COMMENT 'Non-refundable solidarity pool',
    `consecutive_months_active` INT DEFAULT 0 COMMENT 'Minimum 6 months for standard grants',
    `last_contribution_date` DATE NULL,
    `last_updated` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`member_id`) REFERENCES `members`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 6. UNIFIED TRANSACTIONS LEDGER (Double-Entry Audit Trail)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `transactions` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `transaction_ref` VARCHAR(64) NOT NULL UNIQUE,
    `member_id` INT NOT NULL,
    `transaction_type` ENUM('CREDIT', 'DEBIT') NOT NULL,
    `ledger_category` ENUM(
        'SAVINGS',
        'SHARE_CAPITAL',
        'WELFARE_FUND',
        'REGISTRATION_FEE',
        'PASSBOOK_FEE',
        'LOAN_DISBURSEMENT',
        'LOAN_REPAYMENT',
        'WELFARE_GRANT',
        'DISCIPLINARY_FINE',
        'MARKETPLACE_SETTLEMENT'
    ) NOT NULL,
    `amount` DECIMAL(15, 2) NOT NULL,
    `payment_method` ENUM('POLARIS_BANK_TRANSFER', 'DIRECT_DEBIT', 'ONLINE_GATEWAY', 'INTERNAL_SET_OFF') NOT NULL,
    `channel_reference` VARCHAR(100) NULL COMMENT 'Bank deposit slip ref / gateway ID',
    `narration` VARCHAR(255) NOT NULL,
    `status` ENUM('PENDING', 'VERIFIED', 'REJECTED') DEFAULT 'PENDING',
    `verified_by_officer_id` INT NULL,
    `transaction_date` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`member_id`) REFERENCES `members`(`id`),
    INDEX `idx_txn_member` (`member_id`),
    INDEX `idx_txn_type_cat` (`transaction_type`, `ledger_category`),
    INDEX `idx_txn_date` (`transaction_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 7. NON-INTEREST FINANCING & CREDIT FACILITIES (Article 14 & SOP)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `loan_products` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `product_name` VARCHAR(100) NOT NULL,
    `product_code` VARCHAR(30) NOT NULL UNIQUE,
    `description` TEXT NULL,
    `min_membership_months` INT DEFAULT 6,
    `max_multiplier_of_savings` DECIMAL(3, 1) DEFAULT 2.0 COMMENT 'Standard 2x rule',
    `max_principal_ceiling` DECIMAL(15, 2) NOT NULL,
    `admin_cost_fee_percent` DECIMAL(5, 2) NOT NULL COMMENT '0% compounding interest; flat admin cost recovery',
    `min_tenure_months` INT DEFAULT 1,
    `max_tenure_months` INT DEFAULT 12,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `loan_products` (`product_name`, `product_code`, `description`, `min_membership_months`, `max_multiplier_of_savings`, `max_principal_ceiling`, `admin_cost_fee_percent`, `min_tenure_months`, `max_tenure_months`) VALUES
('Standard Personal Financing', 'STD_FINANCE_2X', 'Ordinary facility up to 2x savings collateral', 6, 2.0, 500000.00, 2.50, 3, 12),
('Salary Advance Product', 'SALARY_ADVANCE_30D', 'Fast-track facility capped at 50% salary up to N150,000 (30 days)', 6, 1.0, 150000.00, 1.50, 1, 1),
('CO-CARE Asset & Equipment Finance', 'COCARE_ASSET_Y1', 'Goods/Equipment purchase via CO-CARE Marketplace (Year 1 cap)', 6, 2.0, 250000.00, 2.00, 3, 6)
ON DUPLICATE KEY UPDATE `product_name` = VALUES(`product_name`);

CREATE TABLE IF NOT EXISTS `loans` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `loan_reference` VARCHAR(50) NOT NULL UNIQUE,
    `member_id` INT NOT NULL,
    `product_id` INT NOT NULL,
    `principal_amount` DECIMAL(15, 2) NOT NULL,
    `admin_cost_fee` DECIMAL(15, 2) NOT NULL,
    `total_amount_payable` DECIMAL(15, 2) NOT NULL,
    `tenure_months` INT NOT NULL,
    `monthly_installment` DECIMAL(15, 2) NOT NULL,
    `total_paid` DECIMAL(15, 2) DEFAULT 0.00,
    `outstanding_balance` DECIMAL(15, 2) NOT NULL,
    `status` ENUM(
        'APPLICATION_SUBMITTED',
        'CREDIT_VETTED',
        'APPROVED',
        'REJECTED',
        'DISBURSED',
        'ACTIVE',
        'COMPLETED',
        'DEFAULTED'
    ) DEFAULT 'APPLICATION_SUBMITTED',
    `application_date` DATE NOT NULL,
    `approval_date` DATE NULL,
    `disbursement_date` DATE NULL,
    `next_due_date` DATE NULL,
    `maturity_date` DATE NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (`member_id`) REFERENCES `members`(`id`),
    FOREIGN KEY (`product_id`) REFERENCES `loan_products`(`id`),
    INDEX `idx_loan_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7b. Loan Guarantors (Exposure & Lien Management)
CREATE TABLE IF NOT EXISTS `loan_guarantors` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `loan_id` INT NOT NULL,
    `guarantor_member_id` INT NOT NULL,
    `guaranteed_amount` DECIMAL(15, 2) NOT NULL,
    `lien_encumbered_amount` DECIMAL(15, 2) NOT NULL,
    `status` ENUM('PENDING_CONSENT', 'ACCEPTED', 'RELEASED', 'INVOKED') DEFAULT 'PENDING_CONSENT',
    `accepted_at` DATETIME NULL,
    `released_at` DATETIME NULL,
    FOREIGN KEY (`loan_id`) REFERENCES `loans`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`guarantor_member_id`) REFERENCES `members`(`id`),
    INDEX `idx_guarantor_status` (`guarantor_member_id`, `status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7c. Loan Repayment Schedule & Records
CREATE TABLE IF NOT EXISTS `loan_repayments` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `loan_id` INT NOT NULL,
    `installment_number` INT NOT NULL,
    `due_date` DATE NOT NULL,
    `amount_due` DECIMAL(15, 2) NOT NULL,
    `amount_paid` DECIMAL(15, 2) DEFAULT 0.00,
    `paid_date` DATETIME NULL,
    `transaction_ref` VARCHAR(64) NULL,
    `status` ENUM('PENDING', 'PARTIAL', 'PAID', 'OVERDUE') DEFAULT 'PENDING',
    FOREIGN KEY (`loan_id`) REFERENCES `loans`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 8. WELFARE CLAIMS & MUTUAL SOLIDARITY GRANTS (SOP Section 3)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `welfare_claims` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `claim_code` VARCHAR(50) NOT NULL UNIQUE,
    `member_id` INT NOT NULL,
    `benefit_category` ENUM(
        'MEMBER_BEREAVEMENT',
        'SPOUSE_BEREAVEMENT',
        'CHILD_BEREAVEMENT',
        'PARENT_BEREAVEMENT',
        'EMERGENCY_MEDICAL_GRANT',
        'MEMBER_WEDDING',
        'CHILDBIRTH_NAMING',
        'RETIREMENT_LANDMARK'
    ) NOT NULL,
    `tariff_amount` DECIMAL(15, 2) NOT NULL,
    `amount_disbursed` DECIMAL(15, 2) DEFAULT 0.00,
    `evidence_doc_reference` VARCHAR(255) NULL COMMENT 'Medical certificate, death certificate, wedding invitation, etc.',
    `status` ENUM('SUBMITTED', 'VETTED', 'EXECUTIVE_APPROVED', 'REJECTED', 'DISBURSED') DEFAULT 'SUBMITTED',
    `submission_date` DATE NOT NULL,
    `disbursed_date` DATE NULL,
    `welfare_secretary_notes` TEXT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`member_id`) REFERENCES `members`(`id`),
    INDEX `idx_welfare_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 9. CO-CARE MARKETPLACE (Article 4 & 14)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `marketplace_merchants` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `member_id` INT NOT NULL UNIQUE,
    `business_trading_name` VARCHAR(150) NOT NULL,
    `category` VARCHAR(100) NOT NULL,
    `status` ENUM('PENDING_APPROVAL', 'APPROVED', 'SUSPENDED') DEFAULT 'PENDING_APPROVAL',
    `registered_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`member_id`) REFERENCES `members`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `marketplace_products` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `merchant_id` INT NOT NULL,
    `product_title` VARCHAR(150) NOT NULL,
    `description` TEXT NULL,
    `price` DECIMAL(15, 2) NOT NULL,
    `is_financing_eligible` BOOLEAN DEFAULT TRUE COMMENT 'Eligible for cooperative asset credit',
    `stock_quantity` INT DEFAULT 0,
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`merchant_id`) REFERENCES `marketplace_merchants`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 10. DISCIPLINE, FINES & GENERAL MEETINGS (Article 10 & SOP)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `disciplinary_fines` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `member_id` INT NOT NULL,
    `infraction_type` ENUM(
        'LATE_MONTHLY_REMITTANCE',
        'MEETING_ABSENTEEISM',
        'MEETING_LATENESS',
        'UNAUTHORIZED_REPRESENTATION',
        'CODE_OF_CONDUCT_BREACH'
    ) NOT NULL,
    `fine_amount` DECIMAL(15, 2) NOT NULL,
    `reason` TEXT NOT NULL,
    `status` ENUM('UNPAID', 'SETTLED', 'WAIVED') DEFAULT 'UNPAID',
    `issued_date` DATE NOT NULL,
    `settled_date` DATE NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`member_id`) REFERENCES `members`(`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `general_meetings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `meeting_type` ENUM('ANNUAL_GENERAL_MEETING', 'SPECIAL_GENERAL_MEETING', 'MONTHLY_EXECUTIVE') NOT NULL,
    `meeting_title` VARCHAR(150) NOT NULL,
    `meeting_date` DATE NOT NULL,
    `minute_reference_doc` VARCHAR(255) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `meeting_attendance` (
    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
    `meeting_id` INT NOT NULL,
    `member_id` INT NOT NULL,
    `attendance_status` ENUM('PRESENT', 'ABSENT_WITH_APOLOGY', 'ABSENT_WITHOUT_APOLOGY') NOT NULL,
    `arrival_time` TIME NULL,
    FOREIGN KEY (`meeting_id`) REFERENCES `general_meetings`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`member_id`) REFERENCES `members`(`id`),
    UNIQUE KEY `uk_meeting_member` (`meeting_id`, `member_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
