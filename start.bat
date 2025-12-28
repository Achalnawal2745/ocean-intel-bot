@echo off
echo ========================================
echo ARGO Ocean Intelligence System
echo ========================================
echo.
echo Starting backend server...
start "Backend" cmd /k "python -m uvicorn backend16:app --reload"
timeout /t 3 /nobreak > nul
echo.
echo Starting frontend...
start "Frontend" cmd /k "streamlit run app.py"
echo.
echo ========================================
echo System started!
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:8501
echo ========================================
