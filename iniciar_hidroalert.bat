@echo off
rem ============================================================
rem  HidroAlert - Centro de Mando 3D (API + interfaz web)
rem  Doble clic para iniciar. La interfaz se abre sola en el navegador:
rem  http://localhost:8000/mando3d
rem ============================================================
title HidroAlert - API (puerto 8000)
cd /d "%~dp0.."

echo.
echo  🌊 HidroAlert - iniciando API y Centro de Mando 3D...
echo  La interfaz se abrira en http://localhost:8000/mando3d
echo  (cierre esta ventana para detener el sistema)
echo.

start "" /min cmd /c "timeout /t 4 /nobreak >nul & start http://localhost:8000/mando3d"

"%~dp0.venv\Scripts\python.exe" -m uvicorn hidroalert.api.main:app --host 127.0.0.1 --port 8000
pause
