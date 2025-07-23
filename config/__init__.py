"""
Configuración principal del VMS
Proporciona acceso unificado a toda la configuración del sistema
"""

# Importar configuración legacy (para compatibilidad)
from .config_manager import config_manager

# Importar configuración profesional (si está disponible)
try:
    from .settings import *
    PROFESSIONAL_CONFIG_AVAILABLE = True
except ImportError:
    PROFESSIONAL_CONFIG_AVAILABLE = False

# Exportar para uso global
__all__ = ['config_manager', 'PROFESSIONAL_CONFIG_AVAILABLE']

# Verificar disponibilidad de módulos profesionales
if PROFESSIONAL_CONFIG_AVAILABLE:
    try:
        from ..core.logger import get_logger
        logger = get_logger("VMS.Config")
        logger.info("✅ Configuración profesional cargada")
    except ImportError:
        import logging
        logger = logging.getLogger("VMS.Config")
        logger.info("⚠️ Logger básico en uso")
else:
    import logging
    logger = logging.getLogger("VMS.Config")
    logger.warning("⚠️ Usando configuración legacy")
