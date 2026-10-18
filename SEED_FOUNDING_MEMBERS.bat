@echo off
title Wealthbridge Cooperative - Seed Founding Members
echo =========================================================================
echo WEALTHBRIDGE MULTIPURPOSE COOPERATIVE SOCIETY LIMITED (WMC)
echo SEED FOUNDING MEMBERS UTILITY
echo Official Contact: wealthbridge.coopsociety@gmail.com
echo =========================================================================
echo.
echo This script inserts the 8 Founding Members (WMC-2026-001 to WMC-2026-008),
echo tripartite share/savings/welfare accounts, executive appointments, and
echo inaugural meeting attendance records into MySQL database (wbmf).
echo.
pause
echo.
python "%~dp0seed_founding_members.py"
echo.
pause
