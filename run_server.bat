@echo off
REM Script para iniciar todos los servicios del SERVIDOR VMS (video + comandos)

REM Activar entorno virtual si existe
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

start "VMS Video Server" cmd /k "python tcp_vms_server.py"
start "VMS Command Server" cmd /k "python tcp_vms_command_server.py"

REM Puedes agregar aquí otros servicios necesarios

REM Esperar para no cerrar la ventana principal
pause
