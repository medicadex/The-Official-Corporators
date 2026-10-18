-- =====================================================================
-- WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
-- STORED PROCEDURES: AUTOMATED TRIPARTITE REMITTANCE & LEDGER ENGINE
-- Reference: SOP-WMC-2026-V1 (Section 1.3 Tripartite Ledger Allocation)
-- Official Secretariat Contact: wealthbridge.coopsociety@gmail.com
-- =====================================================================

USE `wbmf`;

DELIMITER $$

-- ---------------------------------------------------------------------
-- 1. PROCEDURE: process_monthly_contribution
-- Splits incoming remittances into Savings, Share Capital, and Welfare
-- and records immutable transaction audit receipts.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `process_monthly_contribution`$$

CREATE PROCEDURE `process_monthly_contribution`(
    IN p_member_id INT,
    IN p_total_amount DECIMAL(15, 2),
    IN p_payment_method ENUM('POLARIS_BANK_TRANSFER', 'DIRECT_DEBIT', 'ONLINE_GATEWAY', 'INTERNAL_SET_OFF'),
    IN p_channel_ref VARCHAR(100),
    IN p_verified_by_officer_id INT,
    OUT p_status VARCHAR(20),
    OUT p_message VARCHAR(255)
)
proc_block: BEGIN
    DECLARE v_member_status VARCHAR(20);
    DECLARE v_tier VARCHAR(20);
    DECLARE v_current_shares INT DEFAULT 0;
    DECLARE v_max_shares INT DEFAULT 200;
    
    DECLARE v_welfare_amount DECIMAL(15, 2) DEFAULT 1000.00;
    DECLARE v_raw_shares DECIMAL(15, 2) DEFAULT 0.00;
    DECLARE v_share_amount DECIMAL(15, 2) DEFAULT 0.00;
    DECLARE v_savings_amount DECIMAL(15, 2) DEFAULT 0.00;
    DECLARE v_new_share_units INT DEFAULT 0;
    
    DECLARE v_batch_ts VARCHAR(30);
    DECLARE v_txn_ref_sav VARCHAR(64);
    DECLARE v_txn_ref_shr VARCHAR(64);
    DECLARE v_txn_ref_wlf VARCHAR(64);

    -- Error handler for transactions
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_status = 'ERROR';
        SET p_message = 'An unexpected database error occurred during contribution allocation.';
    END;

    -- 1. Validate Member
    SELECT `status`, `contribution_tier` 
    INTO v_member_status, v_tier 
    FROM `members` 
    WHERE `id` = p_member_id;

    IF v_member_status IS NULL THEN
        SET p_status = 'NOT_FOUND';
        SET p_message = CONCAT('Member ID ', p_member_id, ' does not exist in registry.');
        LEAVE proc_block;
    END IF;

    IF v_member_status != 'ACTIVE' THEN
        SET p_status = 'INACTIVE_MEMBER';
        SET p_message = CONCAT('Cannot process contribution: Member status is ', v_member_status);
        LEAVE proc_block;
    END IF;

    -- 2. Validate Minimum Amount (Standard Tier baseline = N10,000)
    IF p_total_amount < 10000.00 THEN
        SET p_status = 'INVALID_AMOUNT';
        SET p_message = 'Contribution remittance cannot be less than Standard Tier baseline (NGN 10,000).';
        LEAVE proc_block;
    END IF;

    -- 3. Get Current Share Capital Status
    SELECT `units_held` INTO v_current_shares 
    FROM `share_accounts` 
    WHERE `member_id` = p_member_id;

    IF v_current_shares IS NULL THEN
        SET v_current_shares = 0;
    END IF;

    -- 4. Calculate Statutory Tripartite Ledger Split (SOP 1.3)
    -- Share formula: 10% of total payment, rounded to nearest N1,000
    SET v_raw_shares = ROUND(p_total_amount * 0.10, -3);

    -- Anti-monopoly check: Cap at 200 units (NGN 200,000)
    IF (v_current_shares * 1000 + v_raw_shares) > (v_max_shares * 1000) THEN
        SET v_share_amount = (v_max_shares * 1000) - (v_current_shares * 1000);
        IF v_share_amount < 0.00 THEN
            SET v_share_amount = 0.00;
        END IF;
    ELSE
        SET v_share_amount = v_raw_shares;
    END IF;

    SET v_new_share_units = FLOOR(v_share_amount / 1000);
    
    -- Fixed Welfare Levy = N1,000
    SET v_welfare_amount = 1000.00;

    -- Liquid Savings = Total Remittance - Welfare - Shares
    SET v_savings_amount = p_total_amount - v_welfare_amount - v_share_amount;

    -- 5. Prepare Unique Transaction References
    SET v_batch_ts = UNIX_TIMESTAMP();
    SET v_txn_ref_sav = CONCAT('TXN-WMC-SAV-', p_member_id, '-', v_batch_ts);
    SET v_txn_ref_shr = CONCAT('TXN-WMC-SHR-', p_member_id, '-', v_batch_ts);
    SET v_txn_ref_wlf = CONCAT('TXN-WMC-WLF-', p_member_id, '-', v_batch_ts);

    -- 6. Execute Atomic Ledger Posting
    START TRANSACTION;

        -- A. Post Regular Savings
        IF v_savings_amount > 0 THEN
            INSERT INTO `transactions` (
                `transaction_ref`, `member_id`, `transaction_type`, `ledger_category`, 
                `amount`, `payment_method`, `channel_reference`, `narration`, 
                `status`, `verified_by_officer_id`, `transaction_date`
            ) VALUES (
                v_txn_ref_sav, p_member_id, 'CREDIT', 'SAVINGS', 
                v_savings_amount, p_payment_method, p_channel_ref, 
                CONCAT('Monthly Regular Savings Remittance (', v_tier, ')'), 
                'VERIFIED', p_verified_by_officer_id, NOW()
            );

            INSERT INTO `savings_accounts` (`member_id`, `total_balance`, `encumbered_balance`)
            VALUES (p_member_id, v_savings_amount, 0.00)
            ON DUPLICATE KEY UPDATE 
                `total_balance` = `total_balance` + v_savings_amount;
        END IF;

        -- B. Post Share Capital (if quota remains)
        IF v_share_amount > 0 THEN
            INSERT INTO `transactions` (
                `transaction_ref`, `member_id`, `transaction_type`, `ledger_category`, 
                `amount`, `payment_method`, `channel_reference`, `narration`, 
                `status`, `verified_by_officer_id`, `transaction_date`
            ) VALUES (
                v_txn_ref_shr, p_member_id, 'CREDIT', 'SHARE_CAPITAL', 
                v_share_amount, p_payment_method, p_channel_ref, 
                CONCAT('Monthly Share Capital Equity Subscription (', v_new_share_units, ' units)'), 
                'VERIFIED', p_verified_by_officer_id, NOW()
            );

            INSERT INTO `share_accounts` (`member_id`, `units_held`, `paid_up_amount`, `is_minimum_met`, `benefits_qualified`)
            VALUES (p_member_id, v_new_share_units, v_share_amount, (v_new_share_units >= 5), (v_new_share_units >= 5))
            ON DUPLICATE KEY UPDATE 
                `units_held` = `units_held` + v_new_share_units,
                `paid_up_amount` = `paid_up_amount` + v_share_amount,
                `is_minimum_met` = (`units_held` >= 5),
                `benefits_qualified` = (`units_held` >= 5);
        END IF;

        -- C. Post Welfare Fund Levy
        IF v_welfare_amount > 0 THEN
            INSERT INTO `transactions` (
                `transaction_ref`, `member_id`, `transaction_type`, `ledger_category`, 
                `amount`, `payment_method`, `channel_reference`, `narration`, 
                `status`, `verified_by_officer_id`, `transaction_date`
            ) VALUES (
                v_txn_ref_wlf, p_member_id, 'CREDIT', 'WELFARE_FUND', 
                v_welfare_amount, p_payment_method, p_channel_ref, 
                'Mandatory Monthly Welfare Solidarity Fund Contribution', 
                'VERIFIED', p_verified_by_officer_id, NOW()
            );

            INSERT INTO `welfare_accounts` (`member_id`, `cumulative_contributions`, `consecutive_months_active`, `last_contribution_date`)
            VALUES (p_member_id, v_welfare_amount, 1, CURDATE())
            ON DUPLICATE KEY UPDATE 
                `cumulative_contributions` = `cumulative_contributions` + v_welfare_amount,
                `consecutive_months_active` = `consecutive_months_active` + 1,
                `last_contribution_date` = CURDATE();
        END IF;

    COMMIT;

    SET p_status = 'SUCCESS';
    SET p_message = CONCAT(
        'Successfully allocated NGN ', FORMAT(p_total_amount, 2), 
        ' (Savings: NGN ', FORMAT(v_savings_amount, 2), 
        ', Shares: NGN ', FORMAT(v_share_amount, 2), 
        ', Welfare: NGN ', FORMAT(v_welfare_amount, 2), ')'
    );

END proc_block$$

-- ---------------------------------------------------------------------
-- 2. PROCEDURE: get_member_consolidated_statement
-- Returns complete 360-degree financial standing of any member
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `get_member_consolidated_statement`$$

CREATE PROCEDURE `get_member_consolidated_statement`(
    IN p_member_id INT
)
BEGIN
    SELECT 
        m.id AS member_id,
        m.member_code,
        CONCAT(m.first_name, ' ', m.last_name) AS full_name,
        m.email,
        m.phone,
        m.contribution_tier,
        m.status AS membership_status,
        m.admission_date,
        -- Share Equity Standing
        COALESCE(sh.units_held, 0) AS share_units,
        COALESCE(sh.paid_up_amount, 0.00) AS total_share_equity_ngn,
        COALESCE(sh.benefits_qualified, FALSE) AS is_benefits_qualified,
        -- Savings & Collateral Standing
        COALESCE(sv.total_balance, 0.00) AS total_savings_balance_ngn,
        COALESCE(sv.encumbered_balance, 0.00) AS encumbered_collateral_ngn,
        COALESCE(sv.available_balance, 0.00) AS available_unencumbered_savings_ngn,
        -- Borrowing Capacity (2x Rule)
        (COALESCE(sv.available_balance, 0.00) * 2.0) AS max_ordinary_loan_capacity_ngn,
        -- Welfare Standing
        COALESCE(w.cumulative_contributions, 0.00) AS total_welfare_pool_contributed_ngn,
        COALESCE(w.consecutive_months_active, 0) AS welfare_active_months,
        COALESCE(w.last_contribution_date, 'None') AS last_contribution_date
    FROM members m
    LEFT JOIN share_accounts sh ON m.id = sh.member_id
    LEFT JOIN savings_accounts sv ON m.id = sv.member_id
    LEFT JOIN welfare_accounts w ON m.id = w.member_id
    WHERE m.id = p_member_id;
END$$

-- ---------------------------------------------------------------------
-- 3. PROCEDURE: process_new_member_onboarding
-- Enforces statutory onboarding tariffs (SOP Section 1.1 & 1.4):
-- 1. Registration Fee: N5,000 (Non-refundable administrative fee)
-- 2. Passbook & Digital ID: N2,000 (Passbook & digital identity)
-- 3. Minimum Share Capital: N5,000 (Optional upfront or installmental)
-- 4. Activates member status to ACTIVE upon verified receipt
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `process_new_member_onboarding`$$

CREATE PROCEDURE `process_new_member_onboarding`(
    IN p_member_id INT,
    IN p_payment_method ENUM('POLARIS_BANK_TRANSFER', 'DIRECT_DEBIT', 'ONLINE_GATEWAY', 'INTERNAL_SET_OFF'),
    IN p_channel_ref VARCHAR(100),
    IN p_pay_shares_upfront BOOLEAN,
    IN p_first_month_contribution DECIMAL(15, 2),
    IN p_verified_by_officer_id INT,
    OUT p_status VARCHAR(20),
    OUT p_message VARCHAR(255)
)
onboarding_block: BEGIN
    DECLARE v_member_status VARCHAR(20);
    DECLARE v_first_name VARCHAR(50);
    DECLARE v_last_name VARCHAR(50);
    DECLARE v_reg_fee DECIMAL(15, 2) DEFAULT 5000.00;
    DECLARE v_passbook_fee DECIMAL(15, 2) DEFAULT 2000.00;
    DECLARE v_shares_upfront DECIMAL(15, 2) DEFAULT 5000.00;
    DECLARE v_batch_ts VARCHAR(30);
    DECLARE v_contrib_status VARCHAR(20);
    DECLARE v_contrib_msg VARCHAR(255);

    -- Error Handler
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_status = 'ERROR';
        SET p_message = 'Failed to process onboarding payments due to database transaction error.';
    END;

    -- Validate member
    SELECT `status`, `first_name`, `last_name`
    INTO v_member_status, v_first_name, v_last_name
    FROM `members`
    WHERE `id` = p_member_id;

    IF v_member_status IS NULL THEN
        SET p_status = 'NOT_FOUND';
        SET p_message = CONCAT('Member ID ', p_member_id, ' not found.');
        LEAVE onboarding_block;
    END IF;

    IF v_member_status = 'ACTIVE' THEN
        SET p_status = 'ALREADY_ACTIVE';
        SET p_message = CONCAT('Member ', v_first_name, ' ', v_last_name, ' is already active.');
        LEAVE onboarding_block;
    END IF;

    SET v_batch_ts = UNIX_TIMESTAMP();

    START TRANSACTION;

        -- 1. Post Statutory Registration Fee (N5,000)
        INSERT INTO `transactions` (
            `transaction_ref`, `member_id`, `transaction_type`, `ledger_category`,
            `amount`, `payment_method`, `channel_reference`, `narration`,
            `status`, `verified_by_officer_id`, `transaction_date`
        ) VALUES (
            CONCAT('TXN-WMC-REG-', p_member_id, '-', v_batch_ts), p_member_id, 'CREDIT', 'REGISTRATION_FEE',
            v_reg_fee, p_payment_method, p_channel_ref,
            'One-time Non-refundable Statutory Entrance Registration Fee',
            'VERIFIED', p_verified_by_officer_id, NOW()
        );

        -- 2. Post Statutory Passbook & Digital ID Fee (N2,000)
        INSERT INTO `transactions` (
            `transaction_ref`, `member_id`, `transaction_type`, `ledger_category`,
            `amount`, `payment_method`, `channel_reference`, `narration`,
            `status`, `verified_by_officer_id`, `transaction_date`
        ) VALUES (
            CONCAT('TXN-WMC-PBK-', p_member_id, '-', v_batch_ts), p_member_id, 'CREDIT', 'PASSBOOK_FEE',
            v_passbook_fee, p_payment_method, p_channel_ref,
            'Statutory Cooperative Passbook and Digital ID Card Issuance Fee',
            'VERIFIED', p_verified_by_officer_id, NOW()
        );

        -- 3. Upfront Minimum Shareholding Payment (Optional upfront or installmental)
        IF p_pay_shares_upfront = TRUE THEN
            INSERT INTO `transactions` (
                `transaction_ref`, `member_id`, `transaction_type`, `ledger_category`,
                `amount`, `payment_method`, `channel_reference`, `narration`,
                `status`, `verified_by_officer_id`, `transaction_date`
            ) VALUES (
                CONCAT('TXN-WMC-SHR-UPFRONT-', p_member_id, '-', v_batch_ts), p_member_id, 'CREDIT', 'SHARE_CAPITAL',
                v_shares_upfront, p_payment_method, p_channel_ref,
                'Upfront Mandatory Minimum Share Capital Subscription (5 units @ N1,000)',
                'VERIFIED', p_verified_by_officer_id, NOW()
            );

            INSERT INTO `share_accounts` (`member_id`, `units_held`, `paid_up_amount`, `is_minimum_met`, `benefits_qualified`)
            VALUES (p_member_id, 5, v_shares_upfront, TRUE, TRUE)
            ON DUPLICATE KEY UPDATE
                `units_held` = `units_held` + 5,
                `paid_up_amount` = `paid_up_amount` + v_shares_upfront,
                `is_minimum_met` = TRUE,
                `benefits_qualified` = TRUE;
        ELSE
            -- Ensure initialized share account exists with 0 units
            INSERT INTO `share_accounts` (`member_id`, `units_held`, `paid_up_amount`, `is_minimum_met`, `benefits_qualified`)
            VALUES (p_member_id, 0, 0.00, FALSE, FALSE)
            ON DUPLICATE KEY UPDATE `member_id` = `member_id`;
        END IF;

        -- 4. Initialize Savings & Welfare Accounts
        INSERT INTO `savings_accounts` (`member_id`, `total_balance`, `encumbered_balance`)
        VALUES (p_member_id, 0.00, 0.00)
        ON DUPLICATE KEY UPDATE `member_id` = `member_id`;

        INSERT INTO `welfare_accounts` (`member_id`, `cumulative_contributions`, `consecutive_months_active`, `last_contribution_date`)
        VALUES (p_member_id, 0.00, 0, NULL)
        ON DUPLICATE KEY UPDATE `member_id` = `member_id`;

        -- 5. Activate Member Status
        UPDATE `members`
        SET `status` = 'ACTIVE', `admission_date` = CURDATE()
        WHERE `id` = p_member_id;

    COMMIT;

    -- 6. Process First Monthly Contribution if included
    IF p_first_month_contribution IS NOT NULL AND p_first_month_contribution >= 10000.00 THEN
        CALL process_monthly_contribution(
            p_member_id, 
            p_first_month_contribution, 
            p_payment_method, 
            CONCAT(p_channel_ref, '-MONTH1'), 
            p_verified_by_officer_id, 
            v_contrib_status, 
            v_contrib_msg
        );
    END IF;

    SET p_status = 'SUCCESS';
    SET p_message = CONCAT(
        'Member ', v_first_name, ' ', v_last_name, 
        ' successfully activated! Statutory onboarding fees (N7,000) verified and recorded.'
    );

END onboarding_block$$

DELIMITER ;

