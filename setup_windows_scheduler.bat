@echo off
:: ==============================================================================
:: Configure OS Task Scheduler for periodic RAG data collection:
::   1. raskatof.ru vehicle catalog (weekly, Mon 04:00)
::   2. automotive news (weekly, Mon 05:00)
::   3. Supreme Court case law (monthly, 1st at 03:00)
::   4. statutory legal codes (quarterly, 1st of Jan/Apr/Jul/Oct at 02:00)
:: ==============================================================================

chcp 65001 >nul
cd /d "%~dp0"
echo ==============================================================================
echo [RAG COLLECTORS TASK SCHEDULER SETUP]
echo ==============================================================================

set "BAT_PATH=%~dp0run_collectors.bat"

echo 1. Creating task: RAG_Collector_Cars (weekly, Mon 04:00)...
schtasks /create /tn "RAG_Collector_Cars" /tr "\"%BAT_PATH%\" cars" /sc weekly /d MON /st 04:00 /f

echo 2. Creating task: RAG_Collector_News (weekly, Mon 05:00)...
schtasks /create /tn "RAG_Collector_News" /tr "\"%BAT_PATH%\" news" /sc weekly /d MON /st 05:00 /f

echo 3. Creating task: RAG_Collector_VSRF (monthly, 1st at 03:00)...
schtasks /create /tn "RAG_Collector_VSRF" /tr "\"%BAT_PATH%\" vsrf" /sc monthly /d 1 /st 03:00 /f

echo 4. Creating task: RAG_Collector_Laws (quarterly, 1st at 02:00)...
schtasks /create /tn "RAG_Collector_Laws" /tr "\"%BAT_PATH%\" laws" /sc monthly /m JAN,APR,JUL,OCT /d 1 /st 02:00 /f

echo ==============================================================================
echo [OK] All 4 scheduled tasks registered. Review them via taskschd.msc
echo ==============================================================================
pause
