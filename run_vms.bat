@echo off
REM ============================================================================
REM VMS - Sistema de Monitoreo de Video
REM Script de Ejecución Rápida
REM ============================================================================

title VMS - Sistema de Monitoreo de Video
color 0A

echo.
echo ========================================
echo  VMS - Sistema de Monitoreo de Video
echo  Iniciador Rapido v1.0
echo ========================================
echo.

REM Verificar si existe el entorno virtual
if not exist venv (
    echo [SETUP] Entorno virtual no encontrado
    echo [SETUP] Ejecutando instalacion automatica...
    call install.bat
    if %errorlevel% neq 0 (
        echo ERROR: Fallo en la instalacion
        pause
        exit /b 1
    )
) else (
    echo [INFO] Activando entorno virtual...
    call venv\Scripts\activate.bat
)

REM Verificar dependencias críticas
echo [VERIF] Verificando dependencias criticas...
python -c "import PyQt5, cv2, torch, ultralytics" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Dependencias faltantes. Reinstalando...
    pip install -r requirements.txt
)

REM Ejecutar VMS
echo [START] Iniciando VMS...
echo.
python main.py

echo.
echo [INFO] VMS finalizado
pause
