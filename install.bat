@echo off
REM ============================================================================
REM VMS - Sistema de Monitoreo de Video
REM Script de Instalación Automática para Windows
REM ============================================================================

echo.
echo ========================================
echo  VMS - Sistema de Monitoreo de Video
echo  Instalador Automatico v1.0
echo ========================================
echo.

REM Verificar Python
echo [1/6] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no encontrado. Instala Python 3.8+ desde https://python.org
    pause
    exit /b 1
)
echo ✓ Python encontrado

REM Verificar pip
echo [2/6] Verificando pip...
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: pip no encontrado. Instala pip o reinstala Python
    pause
    exit /b 1
)
echo ✓ pip encontrado

REM Crear entorno virtual (opcional)
echo [3/6] Creando entorno virtual...
if not exist "venv" (
    python -m venv venv
    echo ✓ Entorno virtual creado
) else (
    echo ✓ Entorno virtual ya existe
)

REM Activar entorno virtual
echo [4/6] Activando entorno virtual...
call venv\Scripts\activate.bat

REM Actualizar pip
echo [5/6] Actualizando pip...
python -m pip install --upgrade pip

REM Instalar dependencias
echo [6/6] Instalando dependencias...
pip install -r requirements.txt

echo.
echo ========================================
echo  INSTALACION COMPLETADA
echo ========================================
echo.
echo Para ejecutar el VMS:
echo   1. Activar entorno: venv\Scripts\activate.bat
echo   2. Ejecutar: python main.py
echo.
echo O usar el acceso directo: run_vms.bat
echo.
pause
