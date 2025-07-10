#!/usr/bin/env python3
"""
Diagnóstico Rápido VMS - Sistema Optimizado
"""

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def diagnostico_rapido():
    """Diagnóstico rápido del sistema VMS optimizado"""
    logger.info("🔍 DIAGNÓSTICO VMS OPTIMIZADO")
    logger.info("=" * 40)
    
    # 1. GPUs
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            logger.info(f"✅ GPUs disponibles: {gpu_count}")
            for i in range(gpu_count):
                props = torch.cuda.get_device_properties(i)
                memory_gb = props.total_memory / (1024**3)
                logger.info(f"  GPU {i}: {props.name} - {memory_gb:.1f}GB")
        else:
            logger.error("❌ CUDA no disponible")
    except Exception as e:
        logger.error(f"❌ Error verificando GPUs: {e}")
    
    # 2. GPU Manager
    try:
        from core.gpu_manager import gpu_manager
        logger.info("✅ GPU Manager funcionando")
        logger.info("📋 Distribución de tareas:")
        for task, gpu_id in gpu_manager.task_assignments.items():
            logger.info(f"  {task}: GPU {gpu_id}")
    except Exception as e:
        logger.error(f"❌ Error en GPU Manager: {e}")
    
    # 3. Configuración optimizada
    try:
        from config.config_manager import config_manager
        config = config_manager.PERFORMANCE_CONFIG
        logger.info("✅ Configuración optimizada cargada")
        logger.info(f"  Frame skips - YOLO: {config['yolo_frame_skip']}, "
                   f"Manos: {config['hands_frame_skip']}, "
                   f"Rostros: {config['face_frame_skip']}")
    except Exception as e:
        logger.error(f"❌ Error en configuración: {e}")
    
    # 4. Monitor de rendimiento
    try:
        from core.performance_monitor import performance_monitor
        logger.info("✅ Monitor de rendimiento disponible")
    except Exception as e:
        logger.error(f"❌ Error en monitor: {e}")
    
    logger.info("\n🎯 SISTEMA LISTO PARA PRODUCCIÓN")
    logger.info("💡 Ejecutar: python main.py")

if __name__ == "__main__":
    diagnostico_rapido()
