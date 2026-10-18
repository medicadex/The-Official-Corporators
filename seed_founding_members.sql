-- =====================================================================
-- WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
-- SEED DATA: FOUNDING MEMBERS & INAUGURAL GOVERNANCE COHORT
-- Reference: TOC-MINUTES-04 / Inaugural Meeting (26th September 2026)
-- Official Contact: wealthbridge.coopsociety@gmail.com
-- =====================================================================

USE `wbmf`;

-- ---------------------------------------------------------------------
-- 1. SEED 8 FOUNDING MEMBERS
-- ---------------------------------------------------------------------
INSERT INTO `members` (
    `id`, `member_code`, `first_name`, `last_name`, `other_names`, 
    `email`, `password_hash`, `phone`, `gender`, `residential_address`, 
    `identification_type`, `identification_number`, 
    `employment_status`, `contribution_tier`, `status`, `admission_date`
) VALUES
(1, 'WMC-2026-001', 'Qazeem', 'Adebowale', NULL, 
 'qazeem.adebowale@wealthbridge.ng', 'a65d26d84db6cbe41121d58cf5f5cbb819c9e54d89e248b64b1509176bf7d848', '08020000001', 'MALE', 
 '13, Agbaje Iloro Street, Odogunyan, Ikorodu, Lagos State', 
 'NIN', 'NIN-WMC-FOUNDER-001', 'PROFESSIONAL', 'STANDARD', 'ACTIVE', '2026-09-26'),

(2, 'WMC-2026-002', 'Olaleke', 'Olaoye', 'Ebenezer', 
 'olaleke.olaoye@wealthbridge.ng', 'a65d26d84db6cbe41121d58cf5f5cbb819c9e54d89e248b64b1509176bf7d848', '07066482098', 'MALE', 
 'Ikorodu, Lagos State, Nigeria', 
 'NIN', 'NIN-WMC-FOUNDER-002', 'SALARY_EARNER', 'STANDARD', 'ACTIVE', '2026-09-26'),

(3, 'WMC-2026-003', 'Sulaimon', 'Olajide', 'Akinola', 
 'sulaimon.olajide@wealthbridge.ng', 'a65d26d84db6cbe41121d58cf5f5cbb819c9e54d89e248b64b1509176bf7d848', '08039273458', 'MALE', 
 'Lagos State, Nigeria', 
 'NIN', 'NIN-WMC-FOUNDER-003', 'PROFESSIONAL', 'STANDARD', 'ACTIVE', '2026-09-26'),

(4, 'WMC-2026-004', 'Rukayat', 'Yahaya', 'Temitope', 
 'rukayat.yahaya@wealthbridge.ng', 'a65d26d84db6cbe41121d58cf5f5cbb819c9e54d89e248b64b1509176bf7d848', '08168540916', 'FEMALE', 
 'Lagos State, Nigeria', 
 'NIN', 'NIN-WMC-FOUNDER-004', 'SALARY_EARNER', 'STANDARD', 'ACTIVE', '2026-09-26'),

(5, 'WMC-2026-005', 'Evelyn', 'Omokosi', NULL, 
 'evelyn.omokosi@wealthbridge.ng', 'a65d26d84db6cbe41121d58cf5f5cbb819c9e54d89e248b64b1509176bf7d848', '08032342401', 'FEMALE', 
 'Lagos State, Nigeria', 
 'NIN', 'NIN-WMC-FOUNDER-005', 'PROFESSIONAL', 'STANDARD', 'ACTIVE', '2026-09-26'),

(6, 'WMC-2026-006', 'Yusuf', 'Adebowale', 'Adekoya', 
 'yusuf.adebowale@wealthbridge.ng', 'a65d26d84db6cbe41121d58cf5f5cbb819c9e54d89e248b64b1509176bf7d848', '08130201653', 'MALE', 
 'Lagos State, Nigeria', 
 'NIN', 'NIN-WMC-FOUNDER-006', 'PROFESSIONAL', 'STANDARD', 'ACTIVE', '2026-09-26'),

(7, 'WMC-2026-007', 'Hammed', 'Badmus', 'Oriyomi', 
 'hammed.badmus@wealthbridge.ng', 'a65d26d84db6cbe41121d58cf5f5cbb819c9e54d89e248b64b1509176bf7d848', '07080034088', 'MALE', 
 'Lagos State, Nigeria', 
 'NIN', 'NIN-WMC-FOUNDER-007', 'PROFESSIONAL', 'STANDARD', 'ACTIVE', '2026-09-26'),

(8, 'WMC-2026-008', 'Azeezat', 'Adebowale', 'Rukayat', 
 'azeezat.adebowale@wealthbridge.ng', 'a65d26d84db6cbe41121d58cf5f5cbb819c9e54d89e248b64b1509176bf7d848', '09133448925', 'FEMALE', 
 'Lagos State, Nigeria', 
 'NIN', 'NIN-WMC-FOUNDER-008', 'SALARY_EARNER', 'STANDARD', 'ACTIVE', '2026-09-26')
ON DUPLICATE KEY UPDATE 
    `member_code` = VALUES(`member_code`),
    `first_name` = VALUES(`first_name`),
    `last_name` = VALUES(`last_name`),
    `password_hash` = VALUES(`password_hash`),
    `status` = VALUES(`status`);

-- ---------------------------------------------------------------------
-- 2. INITIALIZE TRIPARTITE LEDGERS FOR FOUNDING MEMBERS
-- ---------------------------------------------------------------------
-- 2a. Share Capital Ledger (Mandatory 5 share units = N5,000 paid-up equity)
INSERT INTO `share_accounts` (`member_id`, `units_held`, `paid_up_amount`, `is_minimum_met`, `benefits_qualified`)
VALUES
(1, 5, 5000.00, TRUE, TRUE),
(2, 5, 5000.00, TRUE, TRUE),
(3, 5, 5000.00, TRUE, TRUE),
(4, 5, 5000.00, TRUE, TRUE),
(5, 5, 5000.00, TRUE, TRUE),
(6, 5, 5000.00, TRUE, TRUE),
(7, 5, 5000.00, TRUE, TRUE),
(8, 5, 5000.00, TRUE, TRUE)
ON DUPLICATE KEY UPDATE 
    `units_held` = VALUES(`units_held`),
    `paid_up_amount` = VALUES(`paid_up_amount`),
    `is_minimum_met` = VALUES(`is_minimum_met`),
    `benefits_qualified` = VALUES(`benefits_qualified`);

-- 2b. Regular Savings Ledger
INSERT INTO `savings_accounts` (`member_id`, `total_balance`, `encumbered_balance`)
VALUES
(1, 0.00, 0.00),
(2, 0.00, 0.00),
(3, 0.00, 0.00),
(4, 0.00, 0.00),
(5, 0.00, 0.00),
(6, 0.00, 0.00),
(7, 0.00, 0.00),
(8, 0.00, 0.00)
ON DUPLICATE KEY UPDATE 
    `total_balance` = VALUES(`total_balance`),
    `encumbered_balance` = VALUES(`encumbered_balance`);

-- 2c. Member Welfare Fund Ledger
INSERT INTO `welfare_accounts` (`member_id`, `cumulative_contributions`, `consecutive_months_active`, `last_contribution_date`)
VALUES
(1, 0.00, 1, '2026-09-26'),
(2, 0.00, 1, '2026-09-26'),
(3, 0.00, 1, '2026-09-26'),
(4, 0.00, 1, '2026-09-26'),
(5, 0.00, 1, '2026-09-26'),
(6, 0.00, 1, '2026-09-26'),
(7, 0.00, 1, '2026-09-26'),
(8, 0.00, 1, '2026-09-26')
ON DUPLICATE KEY UPDATE 
    `consecutive_months_active` = VALUES(`consecutive_months_active`);

-- ---------------------------------------------------------------------
-- 3. APPOINT INTERIM EXECUTIVE OFFICERS (Article 15 & Minutes)
-- ---------------------------------------------------------------------
INSERT INTO `officers` (`member_id`, `portfolio`, `appointment_date`, `is_active`)
VALUES
(1, 'PRESIDENT', '2026-09-26', TRUE),
(2, 'GENERAL_SECRETARY', '2026-09-26', TRUE),
(3, 'LEGAL_COMPLIANCE_LEAD', '2026-09-26', TRUE),
(4, 'FINANCIAL_SECRETARY', '2026-09-26', TRUE),
(5, 'TREASURER', '2026-09-26', TRUE),
(6, 'TECHNOLOGY_SYSTEMS_LEAD', '2026-09-26', TRUE)
ON DUPLICATE KEY UPDATE 
    `portfolio` = VALUES(`portfolio`),
    `is_active` = VALUES(`is_active`);

-- ---------------------------------------------------------------------
-- 4. LOG INAUGURAL GENERAL MEETING & RECORD ATTENDANCE
-- ---------------------------------------------------------------------
INSERT INTO `general_meetings` (
    `id`, `meeting_type`, `meeting_title`, `meeting_date`, `minute_reference_doc`
) VALUES (
    1, 
    'SPECIAL_GENERAL_MEETING', 
    'Inaugural Founding Meeting of Wealthbridge / The Official Corporators', 
    '2026-09-26', 
    'TOC-MINUTES-04'
)
ON DUPLICATE KEY UPDATE 
    `meeting_title` = VALUES(`meeting_title`);

INSERT INTO `meeting_attendance` (`meeting_id`, `member_id`, `attendance_status`, `arrival_time`)
VALUES
(1, 1, 'PRESENT', '12:30:00'),
(1, 2, 'PRESENT', '12:30:00'),
(1, 3, 'PRESENT', '12:30:00'),
(1, 4, 'PRESENT', '12:30:00'),
(1, 5, 'PRESENT', '12:30:00'),
(1, 6, 'PRESENT', '12:30:00'),
(1, 7, 'PRESENT', '12:30:00'),
(1, 8, 'PRESENT', '12:30:00')
ON DUPLICATE KEY UPDATE 
    `attendance_status` = VALUES(`attendance_status`);
