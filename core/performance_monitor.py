#!/usr/bin/env python3
"""
Monitor de Rendimiento VMS
Controla la carga del sistema y ajusta automáticamente los parámetros
"""

import psutil
import time
import threading
import logging
from datetime import datetime, timedelta
from config.config_manager import config_manager

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitor de rendimiento del sistema"""
    
    def __init__(self):
        self.running = False
        self.monitor_thread = None
        self.last_check = datetime.now()
        self.performance_history = []
        self.overload_detected = False
        
        # Umbrales de rendimiento
        self.CPU_THRESHOLD = 85  # %
        self.MEMORY_THRESHOLD = 80  # %
        self.GPU_MEMORY_THRESHOLD = 90  # %
        
    def start_monitoring(self):
        """Inicia el monitoreo de rendimiento"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("🔍 Monitor de rendimiento iniciado")
            
    def stop_monitoring(self):
        """Detiene el monitoreo"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logger.info("🔍 Monitor de rendimiento detenido")
        
    def _monitor_loop(self):
        """Loop principal de monitoreo"""
        while self.running:
            try:
                self._check_system_performance()
                time.sleep(5)  # Verificar cada 5 segundos
            except Exception as e:
                logger.error(f"Error en monitor de rendimiento: {e}")
                
    def _check_system_performance(self):
        """Verifica el rendimiento del sistema"""
        try:
            # CPU y Memoria
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # GPU (si está disponible)
            gpu_memory_percent = self._get_gpu_memory_usage()
            
            # Registrar métricas
            metrics = {
                'timestamp': datetime.now(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'gpu_memory_percent': gpu_memory_percent
            }
            
            self.performance_history.append(metrics)
            
            # Mantener solo las últimas 60 mediciones (5 minutos)
            if len(self.performance_history) > 60:
                self.performance_history.pop(0)
                
            # Detectar sobrecarga
            overload = (
                cpu_percent > self.CPU_THRESHOLD or 
                memory_percent > self.MEMORY_THRESHOLD or
                gpu_memory_percent > self.GPU_MEMORY_THRESHOLD
            )
            
            if overload and not self.overload_detected:
                self.overload_detected = True
                self._handle_overload(metrics)
            elif not overload and self.overload_detected:
                self.overload_detected = False
                self._handle_recovery(metrics)
                
        except Exception as e:
            logger.error(f"Error verificando rendimiento: {e}")
            
    def _get_gpu_memory_usage(self):
        """Obtiene el uso de memoria GPU"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_memory_used = 0
                gpu_memory_total = 0
                
                for i in range(torch.cuda.device_count()):
                    mem_used = torch.cuda.memory_allocated(i)
                    mem_total = torch.cuda.get_device_properties(i).total_memory
                    gpu_memory_used += mem_used
                    gpu_memory_total += mem_total
                    
                if gpu_memory_total > 0:
                    return (gpu_memory_used / gpu_memory_total) * 100
                    
        except Exception:
            pass
            
        return 0
        
    def _handle_overload(self, metrics):
        """Maneja la sobrecarga del sistema"""
        logger.warning(f"🚨 SOBRECARGA DETECTADA - CPU: {metrics['cpu_percent']:.1f}% | "
                      f"RAM: {metrics['memory_percent']:.1f}% | "
                      f"GPU: {metrics['gpu_memory_percent']:.1f}%")
        
        # Aquí podrías implementar medidas automáticas:
        # - Aumentar frame skips temporalmente
        # - Reducir resolución de procesamiento
        # - Pausar analíticas menos críticas
        
        self._suggest_optimizations(metrics)
        
    def _handle_recovery(self, metrics):
        """Maneja la recuperación del sistema"""
        logger.info(f"✅ Sistema recuperado - CPU: {metrics['cpu_percent']:.1f}% | "
                   f"RAM: {metrics['memory_percent']:.1f}% | "
                   f"GPU: {metrics['gpu_memory_percent']:.1f}%")
                   
    def _suggest_optimizations(self, metrics):
        """Sugiere optimizaciones basadas en las métricas"""
        suggestions = []
        
        if metrics['cpu_percent'] > self.CPU_THRESHOLD:
            suggestions.append("- Reducir analíticas activas o aumentar frame skips")
            suggestions.append("- Verificar procesos en segundo plano")
            
        if metrics['memory_percent'] > self.MEMORY_THRESHOLD:
            suggestions.append("- Reducir buffer sizes")
            suggestions.append("- Cerrar aplicaciones innecesarias")
            
        if metrics['gpu_memory_percent'] > self.GPU_MEMORY_THRESHOLD:
            suggestions.append("- Reducir batch sizes en modelos")
            suggestions.append("- Limpiar cache GPU")
            
        if suggestions:
            logger.warning("💡 Sugerencias de optimización:")
            for suggestion in suggestions:
                logger.warning(suggestion)
                
    def get_current_metrics(self):
        """Obtiene las métricas actuales"""
        if self.performance_history:
            return self.performance_history[-1]
        return None
        
    def is_system_overloaded(self):
        """Verifica si el sistema está sobrecargado"""
        return self.overload_detected
        
    def get_performance_summary(self):
        """Obtiene un resumen del rendimiento"""
        if not self.performance_history:
            return None
            
        recent_metrics = self.performance_history[-10:]  # Últimos 10 mediciones
        
        avg_cpu = sum(m['cpu_percent'] for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m['memory_percent'] for m in recent_metrics) / len(recent_metrics)
        avg_gpu = sum(m['gpu_memory_percent'] for m in recent_metrics) / len(recent_metrics)
        
        return {
            'avg_cpu_percent': avg_cpu,
            'avg_memory_percent': avg_memory,
            'avg_gpu_memory_percent': avg_gpu,
            'is_overloaded': self.overload_detected,
            'sample_count': len(recent_metrics)
        }

# Instancia global del monitor
performance_monitor = PerformanceMonitor()

def start_performance_monitoring():
    """Inicia el monitoreo de rendimiento"""
    performance_monitor.start_monitoring()
    
def stop_performance_monitoring():
    """Detiene el monitoreo de rendimiento"""
    performance_monitor.stop_monitoring()
    
def get_performance_metrics():
    """Obtiene métricas actuales de rendimiento"""
    return performance_monitor.get_current_metrics()
    
def is_system_overloaded():
    """Verifica si el sistema está sobrecargado"""
    return performance_monitor.is_system_overloaded()
