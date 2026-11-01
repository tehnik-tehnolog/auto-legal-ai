@echo off
:: ==============================================================================
:: Запуск коллекторов RAG на Windows 10 (локальный ПК / PyCharm)
:: Использование:
::   run_collectors.bat cars     (сбор машин raskatof.ru)
::   run_collectors.bat news     (сбор автоновостей)
::   run_collectors.bat vsrf     (сбор практики ВС РФ)
::   run_collectors.bat laws     (сбор ГК/НК РФ)
::   run_collectors.bat all      (запуск всех коллекторов)
::   run_collectors.bat status   (проверка состояния базы)
:: ==============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

:: Проверяем наличие виртуального окружения PyCharm/venv
if exist "venv\Scripts\python.exe" (
    set "PY_CMD=venv\Scripts\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
) else (
    set "PY_CMD=python"
)

echo [RAG Collector] Используется Python: !PY_CMD!

if "%1"=="" (
    !PY_CMD! rag_collectors\runner.py --status
) else if "%1"=="status" (
    !PY_CMD! rag_collectors\runner.py --status
) else (
    !PY_CMD! rag_collectors\runner.py --collector %1
)

endlocal
