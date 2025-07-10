"""
Configuración Multi-GPU para VMS
Gestiona la distribución de tareas entre múltiples GPUs
"""

import torch
import os
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class GPUManager:
    """Administrador de GPUs para distribución de tareas"""
    
    def __init__(self):
        self.available_gpus = []
        self.task_assignments = {}
        self.gpu_memory_info = {}
        self.initialize_gpus()
        
    def initialize_gpus(self):
        """Inicializa y configura todas las GPUs disponibles"""
        if not torch.cuda.is_available():
            logger.warning("CUDA no está disponible. Usando CPU.")
            return
            
        gpu_count = torch.cuda.device_count()
        logger.info(f"GPUs detectadas: {gpu_count}")
        
        for i in range(gpu_count):
            gpu_props = torch.cuda.get_device_properties(i)
            memory_gb = gpu_props.total_memory / (1024**3)
            
            self.available_gpus.append(i)
            self.gpu_memory_info[i] = {
                'name': gpu_props.name,
                'memory_gb': memory_gb,
                'memory_free_gb': memory_gb,  # Inicialmente toda la memoria está libre
                'compute_capability': f"{gpu_props.major}.{gpu_props.minor}",
                'multiprocessor_count': getattr(gpu_props, 'multiprocessor_count', 0)
            }
            
            logger.info(f"GPU {i}: {gpu_props.name} - {memory_gb:.1f}GB - SM_{gpu_props.major}.{gpu_props.minor}")
            
        # Configurar distribución automática de tareas
        self.configure_task_distribution()
        
    def configure_task_distribution(self):
        """Configura la distribución automática de tareas entre GPUs"""
        if len(self.available_gpus) == 0:
            logger.warning("No hay GPUs disponibles")
            return
            
        elif len(self.available_gpus) == 1:
            # Una sola GPU: todas las tareas en GPU 0
            gpu_id = self.available_gpus[0]
            self.task_assignments = {
                'yolo_detection': gpu_id,
                'face_detection': gpu_id,
                'pose_detection': gpu_id,
                'rendering': gpu_id,
                'video_encoding': gpu_id
            }
            logger.info("Configuración una GPU: todas las tareas en GPU 0")
            
        else:
            # Múltiples GPUs: distribución optimizada
            # GPU 0: Tareas principales (YOLO + Visualización)
            # GPU 1+: Tareas secundarias (Rostros, Poses, etc.)
            
            gpu_primary = self.available_gpus[0]
            gpu_secondary = self.available_gpus[1] if len(self.available_gpus) > 1 else gpu_primary
            
            self.task_assignments = {
                'yolo_detection': gpu_primary,     # GPU 0: YOLO (más pesado)
                'rendering': gpu_primary,          # GPU 0: Renderizado
                'face_detection': gpu_secondary,   # GPU 1: Rostros
                'pose_detection': gpu_secondary,   # GPU 1: Poses/Manos arriba
                'video_encoding': gpu_secondary    # GPU 1: Codificación de video
            }
            
            logger.info(f"Configuración multi-GPU:")
            logger.info(f"  GPU {gpu_primary}: YOLO + Renderizado")
            logger.info(f"  GPU {gpu_secondary}: Rostros + Poses + Video")
            
    def get_device_for_task(self, task_name: str) -> torch.device:
        """Obtiene el dispositivo PyTorch para una tarea específica"""
        if task_name not in self.task_assignments:
            logger.warning(f"Tarea '{task_name}' no asignada. Usando GPU 0 por defecto.")
            return torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
            
        gpu_id = self.task_assignments[task_name]
        return torch.device(f'cuda:{gpu_id}' if torch.cuda.is_available() else 'cpu')
        
    def get_gpu_id_for_task(self, task_name: str) -> int:
        """Obtiene el ID de GPU para una tarea específica"""
        if task_name not in self.task_assignments:
            return 0
        return self.task_assignments[task_name]
        
    def set_gpu_for_opencv(self, task_name: str):
        """Configura OpenCV para usar una GPU específica"""
        gpu_id = self.get_gpu_id_for_task(task_name)
        if torch.cuda.is_available():
            # Configurar OpenCV para usar la GPU específica
            os.environ['CUDA_VISIBLE_DEVICES'] = str(gpu_id)
            
    def get_memory_info(self) -> Dict:
        """Obtiene información de memoria de todas las GPUs"""
        if not torch.cuda.is_available():
            return {}
            
        memory_info = {}
        for gpu_id in self.available_gpus:
            torch.cuda.set_device(gpu_id)
            memory_info[gpu_id] = {
                'allocated_gb': torch.cuda.memory_allocated(gpu_id) / (1024**3),
                'cached_gb': torch.cuda.memory_reserved(gpu_id) / (1024**3),
                'free_gb': (torch.cuda.get_device_properties(gpu_id).total_memory - 
                           torch.cuda.memory_reserved(gpu_id)) / (1024**3)
            }
        return memory_info
        
    def optimize_gpu_settings(self, gpu_id: int):
        """Optimiza configuraciones para una GPU específica"""
        if not torch.cuda.is_available():
            return
            
        torch.cuda.set_device(gpu_id)
        
        # Configuraciones de optimización
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
        
        # Configurar streams CUDA para procesamiento paralelo
        torch.cuda.empty_cache()
        
        logger.info(f"GPU {gpu_id} optimizada para rendimiento")
        
    def print_status(self):
        """Imprime el estado actual de las GPUs"""
        if not torch.cuda.is_available():
            logger.info("Estado GPU: CUDA no disponible")
            return
            
        logger.info("=== Estado GPU Manager ===")
        logger.info(f"GPUs disponibles: {len(self.available_gpus)}")
        
        for task, gpu_id in self.task_assignments.items():
            logger.info(f"  {task}: GPU {gpu_id}")
            
        memory_info = self.get_memory_info()
        for gpu_id, info in memory_info.items():
            logger.info(f"GPU {gpu_id} - Memoria: {info['allocated_gb']:.1f}GB usado, "
                       f"{info['free_gb']:.1f}GB libre")

# Instancia global del administrador de GPUs
gpu_manager = GPUManager()

# Funciones de conveniencia
def get_yolo_device():
    """Obtiene el dispositivo para YOLO"""
    return gpu_manager.get_device_for_task('yolo_detection')

def get_face_device():
    """Obtiene el dispositivo para detección de rostros"""
    return gpu_manager.get_device_for_task('face_detection')

def get_pose_device():
    """Obtiene el dispositivo para detección de poses"""
    return gpu_manager.get_device_for_task('pose_detection')

def get_rendering_device():
    """Obtiene el dispositivo para renderizado"""
    return gpu_manager.get_device_for_task('rendering')

def setup_opencv_gpu(task_name: str):
    """Configura OpenCV para usar la GPU asignada a una tarea"""
    gpu_manager.set_gpu_for_opencv(task_name)

def print_gpu_status():
    """Imprime el estado de todas las GPUs"""
    gpu_manager.print_status()
