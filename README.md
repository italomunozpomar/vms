# VMS - Video Management System

![VMS Logo](https://img.shields.io/badge/VMS-Video_Management_System-blue?style=for-the-badge)
![Version](https://img.shields.io/badge/version-1.2.0-green?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-orange?style=flat-square)

## 📋 Descripción

Sistema profesional de gestión de video con inteligencia artificial integrada, diseñado para monitoreo de seguridad en tiempo real con múltiples cámaras IP.

## ✨ Características Principales

### 🎥 **Gestión de Video**
- ✅ **Multi-cámara**: Soporte para 4+ cámaras IP simultáneas
- ✅ **Calidad adaptativa**: Automático switch entre alta/baja resolución
- ✅ **Grabación inteligente**: Solo graba cuando es necesario
- ✅ **Reproducción avanzada**: Sistema de playback con controles profesionales

### 🤖 **Inteligencia Artificial**
- ✅ **Detección de personas**: YOLO v8 optimizado
- ✅ **Detección de rostros**: OpenCV DNN + face_recognition
- ✅ **Detección de poses**: MediaPipe para gestos específicos
- ✅ **Eventos de seguridad**: Motion, line crossing, intrusion

### 🔧 **Sistema de Control**
- ✅ **Modo Merodeo**: Control granular de vigilancia por cámara
- ✅ **Multi-GPU**: Distribución automática de carga
- ✅ **Interfaz moderna**: UI responsiva con tema oscuro
- ✅ **Base de datos**: SQLite integrada para eventos

### 🚀 **Rendimiento**
- ✅ **Optimización GPU**: Soporte CUDA para máximo rendimiento
- ✅ **Threading avanzado**: Procesamiento paralelo eficiente
- ✅ **Memoria inteligente**: Gestión automática de recursos
- ✅ **Escalabilidad**: Arquitectura modular expandible

## 🛠️ Instalación

### Requisitos del Sistema
- Windows 10/11 (64-bit)
- Python 3.10+
- NVIDIA GPU (recomendado)
- 8GB RAM mínimo
- 50GB espacio libre

### Instalación Rápida
```bash
# Clonar repositorio
git clone https://github.com/italomunozpomar/vms.git
cd vms

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar VMS
python main.py
```

### Instalación con GPU (Recomendado)
```bash
# Instalar PyTorch con CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Verificar instalación GPU
python -c "import torch; print(f'CUDA disponible: {torch.cuda.is_available()}')"
```

## 📖 Uso

### Inicio Rápido
1. **Ejecutar VMS**: `python main.py`
2. **Seleccionar cámaras**: Click en las cámaras para seleccionar
3. **Activar Merodeo**: Botón para vigilancia activa
4. **Configurar analíticas**: Personas, rostros, gestos según necesidad

### Modos de Operación

#### 🔍 **Modo Solo Visualización**
- Merodeo: `OFF`
- Uso: Monitoreo visual básico
- Rendimiento: Máximo (mínimo procesamiento)

#### 🛡️ **Modo Vigilancia Completa**
- Merodeo: `ON`
- Uso: Detección completa de eventos
- Incluye: Motion, line crossing, intrusion

#### 🤖 **Modo Analíticas Avanzadas**
- Personas: Detección YOLO
- Rostros: Reconocimiento facial
- Gestos: Detección de poses específicas

## 🏗️ Arquitectura

```
VMS/
├── 📁 config/          # Configuración del sistema
│   ├── settings.py     # Configuración centralizada
│   ├── config_manager.py  # Gestor de estado
│   └── database_manager.py  # Base de datos
├── 📁 core/            # Núcleo del sistema
│   ├── camera_thread.py    # Gestión de cámaras
│   ├── yolo_model.py      # Detección de personas
│   ├── deteccion_rostro.py # Detección facial
│   ├── manos_arriba.py    # Detección de gestos
│   ├── hikvision_events.py # Eventos de cámaras
│   ├── gpu_manager.py     # Gestión GPU
│   └── logger.py          # Sistema de logging
├── 📁 ui/              # Interfaz de usuario
│   ├── window_grid.py     # Ventana principal
│   ├── playback_panel.py  # Panel reproducción
│   └── opengl_video_widget.py # Renderizado video
└── 📁 models/          # Modelos de IA
```

## ⚙️ Configuración

### Cámaras IP
Editar `config/settings.py`:
```python
CAMERA_CONFIG = {
    "ip_address": "192.168.67.63",
    "username": "admin", 
    "password": "tu_password",
    "channels": {
        "high_res": ['101', '501', '601', '901'],
        "low_res": ['102', '502', '602', '902'],
    }
}
```

### Rutas de Salida
```python
OUTPUT_DIR = Path("D:/output")  # Cambiar según necesidad
```

### Rendimiento GPU
```python
PERFORMANCE = {
    "gpu_memory_fraction": 0.8,
    "yolo_frame_skip": 3,
    "max_fps": 30,
}
```

## 📊 Monitoreo

### Logs del Sistema
- **Ubicación**: `logs/vms_YYYYMMDD.log`
- **Rotación**: Automática (10MB por archivo)
- **Retención**: 5 archivos de respaldo

### Base de Datos
- **Tipo**: SQLite
- **Ubicación**: `config/vms_events.db`
- **Contenido**: Eventos, grabaciones, metadatos

### Archivos de Salida
```
D:/output/
├── recordings/     # Grabaciones normales
├── events/         # Grabaciones de eventos  
├── snapshots/      # Capturas de pantalla
└── analytics/      # Resultados de IA
```

## 🐛 Resolución de Problemas

### Error: CUDA no disponible
```bash
# Verificar instalación NVIDIA
nvidia-smi

# Reinstalar PyTorch con CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Warning: Triton no disponible (Windows)
Agregar al inicio de `main.py`:
```python
import torch._dynamo
torch._dynamo.config.suppress_errors = True
```

### Cameras no conectan
1. Verificar IP y credenciales en `config/settings.py`
2. Probar conexión: `ping 192.168.67.63`
3. Verificar puertos RTSP (554)

## 🤝 Contribuir

1. Fork del proyecto
2. Crear branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m 'Agregar nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Pull Request

## 📝 Changelog

### v1.2.0 (Actual)
- ✅ Sistema de Merodeo implementado
- ✅ Control granular por cámara
- ✅ Optimización de rendimiento
- ✅ Logging profesional

### v1.1.0
- ✅ Multi-GPU support
- ✅ OpenGL rendering
- ✅ Database integration

### v1.0.0
- ✅ Versión inicial
- ✅ Detección básica
- ✅ Interfaz PyQt5

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 👨‍💻 Autor

**Italo Muñoz Pomar**
- GitHub: [@italomunozpomar](https://github.com/italomunozpomar)
- Email: italo.munoz@ejemplo.com

## 🙏 Agradecimientos

- YOLO team por el modelo de detección
- OpenCV community
- PyQt development team
- MediaPipe team

---

⭐ **¡Si te gusta este proyecto, dale una estrella!** ⭐
