@echo off
if not exist venv (
    echo Creando entorno virtual...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Instalando dependencias...
    pip install --upgrade pip
    pip install -r requirements.txt
) else (
    echo Activando entorno virtual...
    call venv\Scripts\activate.bat
)
echo Ejecutando VMS...
python main.py
pause
