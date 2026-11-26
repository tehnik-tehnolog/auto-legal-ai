@echo off
:: ==============================================================================
:: Run RAG data collectors locally (Windows/Linux CLI helper)
:: Usage:
::   run_collectors.bat cars     (collect vehicle catalog from raskatof.ru)
::   run_collectors.bat news     (collect automotive news)
::   run_collectors.bat vsrf     (collect Supreme Court case law)
::   run_collectors.bat laws     (collect Civil/Tax/Admin Codes & transport laws)
::   run_collectors.bat all      (run all collectors)
::   run_collectors.bat status   (inspect current KB stats)
:: ==============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

:: Detect local virtual environment (venv / .venv)
if exist "venv\Scripts\python.exe" (
    set "PY_CMD=venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
) else (
    set "PY_CMD=python"
)

echo [RAG Collector] Using Python: !PY_CMD!

if "%1"=="" (
    !PY_CMD! rag_collectors\runner.py --status
) else if "%1"=="status" (
    !PY_CMD! rag_collectors\runner.py --status
) else (
    !PY_CMD! rag_collectors\runner.py --collector %1
)

endlocal
