@echo off
title Wealthbridge Cooperative - Wipe Test Data
echo =========================================================================
echo WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
echo DATABASE TEST DATA PURGE UTILITY
echo Official Contact: wealthbridge.coopsociety@gmail.com
echo =========================================================================
echo.
echo WARNING: This will delete all registered test members and transactions
echo while keeping system configuration, bye-law rules, and loan products intact.
echo.
pause
echo.
python "%~dp0wipe_test_data.py"
echo.
pause
