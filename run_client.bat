@echo off
REM Script para iniciar el CLIENTE VMS (GUI)

REM Activar entorno virtual si existe
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python main_tcp_client.py

REM Esperar para no cerrar la ventana principal
pause
