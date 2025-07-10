#!/usr/bin/env python3
"""
Configuración final del sistema VMS
Asegura que todas las configuraciones estén optimizadas para producción
"""

import os
import sys
import logging
import json
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_production_config():
    """Crea configuración optimizada para producción"""
    logger.info("Creando configuración de producción...")
    
    config = {
        "system": {
            "name": "VMS - Sistema de Monitoreo de Video",
            "version": "1.0.0",
            "environment": "production",
            "optimization_level": "high"
        },
        "gpu": {
            "cuda_enabled": True,
            "multi_gpu_enabled": True,
            "memory_optimization": True,
            "task_distribution": {
                "yolo_detection": 0,
                "face_detection": 1,
                "pose_detection": 1,
                "rendering": 0,
                "video_encoding": 1
            }
        },
        "performance": {
            "max_threads": 4,
            "buffer_size": 30,
            "frame_skip": 1,
            "detection_interval": 1,
            "save_detections": True,
            "realtime_processing": True
        },
        "storage": {
            "base_path": "output",
            "auto_cleanup": True,
            "max_storage_days": 30,
            "compression_enabled": True
        },
        "cameras": {
            "channels": [101, 501, 601, 901],
            "resolution": "1920x1080",
            "fps": 25,
            "codec": "h264"
        },
        "detection": {
            "yolo_confidence": 0.5,
            "face_confidence": 0.7,
            "pose_confidence": 0.6,
            "min_detection_size": 50,
            "max_detections_per_frame": 10
        },
        "ui": {
            "theme": "dark",
            "grid_layout": "2x2",
            "fps_display": True,
            "stats_display": True,
            "fullscreen_mode": True
        }
    }
    
    # Guardar configuración
    config_path = Path("config/production_config.json")
    config_path.parent.mkdir(exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Configuración guardada en: {config_path}")
    return config_path

def optimize_environment_variables():
    """Optimiza variables de entorno para rendimiento"""
    logger.info("Optimizando variables de entorno...")
    
    env_vars = {
        # PyTorch optimizations
        'TORCH_CUDA_ARCH_LIST': '6.0;6.1;7.0;7.5;8.0;8.6',
        'CUDA_LAUNCH_BLOCKING': '0',
        'TORCH_USE_CUDA_DSA': '1',
        
        # OpenCV optimizations
        'OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS': '0',
        'OPENCV_VIDEOIO_PRIORITY_MSMF': '0',
        
        # PyQt optimizations
        'QT_AUTO_SCREEN_SCALE_FACTOR': '1',
        'QT_ENABLE_HIGHDPI_SCALING': '1',
        
        # Memory optimizations
        'PYTHONMALLOC': 'malloc',
        'MALLOC_TRIM_THRESHOLD_': '100000',
        
        # CUDA optimizations
        'CUDA_CACHE_MAXSIZE': '268435456',  # 256MB
        'CUDA_CACHE_DISABLE': '0'
    }
    
    for var, value in env_vars.items():
        os.environ[var] = value
        logger.info(f"  {var}={value}")
    
    # Crear archivo de variables de entorno
    env_file = Path("config/environment.bat")
    env_file.parent.mkdir(exist_ok=True)
    
    with open(env_file, 'w') as f:
        f.write("@echo off\n")
        f.write("REM Variables de entorno optimizadas para VMS\n\n")
        
        for var, value in env_vars.items():
            f.write(f"set {var}={value}\n")
    
    logger.info(f"Variables de entorno guardadas en: {env_file}")

def create_startup_script():
    """Crea script de inicio optimizado"""
    logger.info("Creando script de inicio...")
    
    script_content = """@echo off
title VMS - Sistema de Monitoreo de Video
color 0A

echo ====================================
echo VMS - Sistema de Monitoreo de Video
echo Version 1.0.0 - Produccion
echo ====================================
echo.

REM Configurar variables de entorno
if exist config\\environment.bat (
    echo Cargando configuracion optimizada...
    call config\\environment.bat
) else (
    echo Configuracion no encontrada, usando valores por defecto
)

REM Verificar entorno virtual
if not exist venv (
    echo Creando entorno virtual...
    python -m venv venv
    if errorlevel 1 (
        echo Error: No se pudo crear el entorno virtual
        pause
        exit /b 1
    )
)

REM Activar entorno virtual
echo Activando entorno virtual...
call venv\\Scripts\\activate.bat
if errorlevel 1 (
    echo Error: No se pudo activar el entorno virtual
    pause
    exit /b 1
)

REM Verificar e instalar dependencias
echo Verificando dependencias...
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo Error: No se pudieron instalar las dependencias
    pause
    exit /b 1
)

REM Ejecutar verificacion del sistema
echo Ejecutando verificacion del sistema...
python check_system.py
if errorlevel 1 (
    echo.
    echo Advertencia: Algunas verificaciones fallaron
    echo El sistema puede funcionar con rendimiento reducido
    echo.
    choice /C YN /M "¿Desea continuar de todos modos"
    if errorlevel 2 exit /b 1
)

echo.
echo Iniciando VMS...
echo Presione Ctrl+C para detener
echo.

REM Ejecutar aplicacion principal
python main.py

echo.
echo VMS finalizado
pause
"""
    
    script_path = Path("start_vms_production.bat")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    logger.info(f"Script de inicio creado: {script_path}")
    return script_path

def create_monitoring_script():
    """Crea script de monitoreo de sistema"""
    logger.info("Creando script de monitoreo...")
    
    script_content = """#!/usr/bin/env python3
\"\"\"
Monitor del sistema VMS
Monitorea el rendimiento y estado del sistema en tiempo real
\"\"\"

import psutil
import time
import os
import logging
from pathlib import Path

def monitor_system():
    \"\"\"Monitorea recursos del sistema\"\"\"
    while True:
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memoria
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_gb = memory.used / (1024**3)
            
            # GPU (si está disponible)
            gpu_info = "N/A"
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_memory = torch.cuda.memory_allocated() / (1024**3)
                    gpu_info = f"{gpu_memory:.1f}GB"
            except ImportError:
                pass
            
            # Disco
            disk = psutil.disk_usage('.')
            disk_percent = disk.percent
            
            # Mostrar información
            os.system('cls' if os.name == 'nt' else 'clear')
            print("="*50)
            print("VMS - MONITOR DEL SISTEMA")
            print("="*50)
            print(f"CPU: {cpu_percent:5.1f}%")
            print(f"RAM: {memory_percent:5.1f}% ({memory_gb:.1f}GB)")
            print(f"GPU: {gpu_info}")
            print(f"Disco: {disk_percent:5.1f}%")
            print("="*50)
            print("Presione Ctrl+C para salir")
            
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\\nMonitor detenido")
            break
        except Exception as e:
            print(f"Error en monitor: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_system()
"""
    
    script_path = Path("monitor_system.py")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    logger.info(f"Script de monitoreo creado: {script_path}")
    return script_path

def create_readme():
    """Crea README con instrucciones de uso"""
    logger.info("Creando README...")
    
    readme_content = """# VMS - Sistema de Monitoreo de Video

## Versión 1.0.0 - Producción

### Descripción
Sistema avanzado de monitoreo de video con detección de personas, rostros y poses usando múltiples GPUs para máximo rendimiento.

### Características
- ✅ Detección de personas con YOLO v8
- ✅ Detección de rostros con OpenCV DNN
- ✅ Detección de poses/manos arriba con MediaPipe
- ✅ Soporte multi-GPU para distribución de carga
- ✅ Interfaz gráfica optimizada con PyQt5
- ✅ Grabación automática de eventos
- ✅ Capturas automáticas de detecciones

### Requisitos del Sistema
- Windows 10/11
- Python 3.8+
- CUDA 11.x o superior
- GPUs NVIDIA con al menos 4GB VRAM
- 16GB RAM recomendado

### Instalación y Uso

#### Opción 1: Inicio Rápido
```batch
# Ejecutar el script de inicio automático
start_vms_production.bat
```

#### Opción 2: Manual
```batch
# Crear entorno virtual
python -m venv venv
venv\\Scripts\\activate.bat

# Instalar dependencias
pip install -r requirements.txt

# Verificar sistema
python check_system.py

# Ejecutar VMS
python main.py
```

### Distribución de Tareas GPU
- **GPU 0**: Detección YOLO + Renderizado UI
- **GPU 1**: Detección rostros + Poses + Codificación video

### Estructura de Archivos
```
vms/
├── main.py                    # Aplicación principal
├── check_system.py            # Verificación del sistema
├── monitor_system.py          # Monitor de recursos
├── start_vms_production.bat   # Script de inicio
├── requirements.txt           # Dependencias
├── config/                    # Configuraciones
├── core/                      # Módulos principales
├── ui/                        # Interfaz de usuario
└── output/                    # Salidas del sistema
    ├── captures/              # Capturas de detecciones
    ├── eventos/               # Videos de eventos
    ├── rostros/               # Detecciones de rostros
    └── videos/                # Videos procesados
```

### Configuración
Las configuraciones se encuentran en `config/production_config.json` y pueden ajustarse según las necesidades específicas.

### Monitoreo
Ejecute `python monitor_system.py` para monitorear el rendimiento del sistema en tiempo real.

### Solución de Problemas
1. **Error CUDA**: Verificar drivers NVIDIA y versión CUDA
2. **Memoria insuficiente**: Reducir resolución o número de cámaras
3. **Rendimiento lento**: Verificar asignación de GPUs

### Soporte
Para soporte técnico, revisar los logs en `vms.log` y ejecutar `python check_system.py` para diagnóstico.

---
© 2025 VMS System - Optimizado para producción
"""
    
    readme_path = Path("README.md")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    logger.info(f"README creado: {readme_path}")
    return readme_path

def main():
    """Función principal de configuración"""
    logger.info("🔧 Iniciando configuración final del sistema VMS")
    
    tasks = [
        ("Configuración de producción", create_production_config),
        ("Variables de entorno", optimize_environment_variables),
        ("Script de inicio", create_startup_script),
        ("Script de monitoreo", create_monitoring_script),
        ("README", create_readme)
    ]
    
    results = []
    for task_name, task_func in tasks:
        logger.info(f"Ejecutando: {task_name}")
        try:
            result = task_func()
            results.append((task_name, True, result))
            logger.info(f"✅ {task_name} completado")
        except Exception as e:
            results.append((task_name, False, str(e)))
            logger.error(f"❌ {task_name} falló: {e}")
    
    # Resumen
    print("\n" + "="*60)
    print("RESUMEN DE CONFIGURACIÓN")
    print("="*60)
    
    for task_name, success, result in results:
        status = "✅ COMPLETADO" if success else "❌ FALLÓ"
        print(f"{task_name:<30}: {status}")
        if success and hasattr(result, 'name'):
            print(f"  → {result}")
    
    successful = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"\nResultado: {successful}/{total} configuraciones completadas")
    
    if successful == total:
        print("\n🎉 ¡Sistema VMS completamente configurado para producción!")
        print("\nPara iniciar el sistema, ejecute:")
        print("  start_vms_production.bat")
        print("\nPara monitorear el sistema:")
        print("  python monitor_system.py")
    else:
        print("\n⚠️ Algunas configuraciones fallaron. Revisar logs.")
    
    return 0 if successful == total else 1

if __name__ == "__main__":
    sys.exit(main())
