@echo off
:: ==============================================================================
:: Запуск веб-части Streamlit на Windows 10
:: ==============================================================================
cd /d "%~dp0"

if exist "venv\Scripts\streamlit.exe" (
    venv\Scripts\streamlit.exe run streamlit_app.py
) else if exist ".venv\Scripts\streamlit.exe" (
    .venv\Scripts\streamlit.exe run streamlit_app.py
) else (
    streamlit run streamlit_app.py
)
pause
