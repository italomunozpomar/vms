@echo off
REM ============================================================================
REM VMS - Sistema de Monitoreo de Video
REM Script de Desarrollo con Herramientas de Debug
REM ============================================================================

title VMS Development Mode
color 0E

echo.
echo ========================================
echo  VMS - MODO DESARROLLO
echo  Herramientas de Debug v1.0
echo ========================================
echo.

REM Activar entorno virtual
if exist venv (
    call venv\Scripts\activate.bat
    echo [DEV] Entorno virtual activado
) else (
    echo [ERROR] Entorno virtual no encontrado. Ejecuta install.bat primero
    pause
    exit /b 1
)

:menu
echo.
echo ========================================
echo  OPCIONES DE DESARROLLO
echo ========================================
echo  1. Ejecutar VMS (modo normal)
echo  2. Ejecutar VMS (modo debug)
echo  3. Diagnostico del sistema
echo  4. Verificar dependencias
echo  5. Limpiar cache de Python
echo  6. Formatear codigo (autopep8)
echo  7. Analizar codigo (flake8)
echo  8. Generar documentacion
echo  9. Salir
echo ========================================
set /p choice="Selecciona una opcion (1-9): "

if "%choice%"=="1" goto run_normal
if "%choice%"=="2" goto run_debug
if "%choice%"=="3" goto diagnostics
if "%choice%"=="4" goto check_deps
if "%choice%"=="5" goto clean_cache
if "%choice%"=="6" goto format_code
if "%choice%"=="7" goto analyze_code
if "%choice%"=="8" goto generate_docs
if "%choice%"=="9" goto exit
goto menu

:run_normal
echo [RUN] Ejecutando VMS (modo normal)...
python main.py
goto menu

:run_debug
echo [DEBUG] Ejecutando VMS (modo debug)...
python -u main.py
goto menu

:diagnostics
echo [DIAG] Ejecutando diagnostico del sistema...
python diagnostico_sistema.py
pause
goto menu

:check_deps
echo [CHECK] Verificando dependencias...
pip check
pip list
pause
goto menu

:clean_cache
echo [CLEAN] Limpiando cache de Python...
python -c "import shutil, os; [shutil.rmtree(root) for root, dirs, files in os.walk('.') for d in dirs if d == '__pycache__']"
echo Cache limpiado
pause
goto menu

:format_code
echo [FORMAT] Formateando codigo con autopep8...
autopep8 --in-place --recursive --aggressive --aggressive .
echo Codigo formateado
pause
goto menu

:analyze_code
echo [ANALYZE] Analizando codigo con flake8...
flake8 . --max-line-length=120 --extend-ignore=E501,W503
pause
goto menu

:generate_docs
echo [DOCS] Generando documentacion...
echo TODO: Implementar generacion de documentacion
pause
goto menu

:exit
echo [EXIT] Saliendo del modo desarrollo...
exit /b 0
