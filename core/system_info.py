# core/system_info.py
"""
Información del sistema y diagnósticos
Proporciona información detallada sobre el estado del VMS
"""
import platform
import psutil
import torch
import cv2
import sys
from pathlib import Path
from datetime import datetime
import subprocess

from config.settings import APP_NAME, APP_VERSION, APP_AUTHOR
from core.constants import VERSION, BUILD_DATE, BUILD_NUMBER

class SystemInfo:
    """Recopila información del sistema para diagnósticos"""
    
    def __init__(self):
        self.info = self._gather_system_info()
    
    def _gather_system_info(self) -> dict:
        """Recopila toda la información del sistema"""
        return {
            "app": self._get_app_info(),
            "system": self._get_system_info(),
            "hardware": self._get_hardware_info(),
            "gpu": self._get_gpu_info(),
            "software": self._get_software_info(),
            "network": self._get_network_info(),
            "storage": self._get_storage_info(),
        }
    
    def _get_app_info(self) -> dict:
        """Información de la aplicación"""
        return {
            "name": APP_NAME,
            "version": APP_VERSION,
            "author": APP_AUTHOR,
            "build_version": VERSION,
            "build_date": BUILD_DATE,
            "build_number": BUILD_NUMBER,
            "start_time": datetime.now().isoformat(),
        }
    
    def _get_system_info(self) -> dict:
        """Información del sistema operativo"""
        return {
            "platform": platform.platform(),
            "system": platform.system(),
            "version": platform.version(),
            "release": platform.release(),
            "architecture": platform.architecture()[0],
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "python_executable": sys.executable,
        }
    
    def _get_hardware_info(self) -> dict:
        """Información del hardware"""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "cpu_cores_physical": psutil.cpu_count(logical=False),
            "cpu_cores_logical": psutil.cpu_count(logical=True),
            "cpu_freq_max": psutil.cpu_freq().max if psutil.cpu_freq() else "N/A",
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "memory_percent": memory.percent,
            "swap_total_gb": round(swap.total / (1024**3), 2),
            "swap_used_gb": round(swap.used / (1024**3), 2),
        }
    
    def _get_gpu_info(self) -> dict:
        """Información de las GPUs"""
        gpu_info = {
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda if torch.cuda.is_available() else "N/A",
            "cudnn_version": torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else "N/A",
            "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "gpus": []
        }
        
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                gpu_info["gpus"].append({
                    "id": i,
                    "name": props.name,
                    "memory_total_gb": round(props.total_memory / (1024**3), 2),
                    "memory_free_gb": round(torch.cuda.mem_get_info(i)[0] / (1024**3), 2),
                    "compute_capability": f"{props.major}.{props.minor}",
                    "multiprocessor_count": props.multi_processor_count,
                })
        
        return gpu_info
    
    def _get_software_info(self) -> dict:
        """Información del software instalado"""
        return {
            "opencv_version": cv2.__version__,
            "torch_version": torch.__version__,
            "python_packages": self._get_installed_packages(),
        }
    
    def _get_installed_packages(self) -> dict:
        """Lista de paquetes Python instalados (principales)"""
        try:
            import pkg_resources
            packages = {}
            key_packages = [
                'torch', 'torchvision', 'opencv-python', 'PyQt5', 
                'mediapipe', 'ultralytics', 'numpy', 'psutil'
            ]
            
            for package in key_packages:
                try:
                    version = pkg_resources.get_distribution(package).version
                    packages[package] = version
                except pkg_resources.DistributionNotFound:
                    packages[package] = "Not installed"
            
            return packages
        except Exception as e:
            return {"error": str(e)}
    
    def _get_network_info(self) -> dict:
        """Información de red"""
        interfaces = []
        
        for interface, addrs in psutil.net_if_addrs().items():
            interface_info = {"name": interface, "addresses": []}
            
            for addr in addrs:
                if addr.family == 2:  # IPv4
                    interface_info["addresses"].append({
                        "type": "IPv4",
                        "address": addr.address,
                        "netmask": addr.netmask,
                    })
                elif addr.family == 23:  # IPv6
                    interface_info["addresses"].append({
                        "type": "IPv6", 
                        "address": addr.address,
                    })
            
            if interface_info["addresses"]:
                interfaces.append(interface_info)
        
        return {
            "interfaces": interfaces,
            "connections": len(psutil.net_connections()),
        }
    
    def _get_storage_info(self) -> dict:
        """Información de almacenamiento"""
        drives = []
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                drives.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": round((usage.used / usage.total) * 100, 1),
                })
            except PermissionError:
                continue
        
        return {"drives": drives}
    
    def print_summary(self):
        """Imprime un resumen del sistema"""
        print("=" * 60)
        print(f"🚀 {self.info['app']['name']} v{self.info['app']['version']}")
        print(f"📅 Build: {self.info['app']['build_date']} ({self.info['app']['build_number']})")
        print("=" * 60)
        
        # Sistema
        sys_info = self.info['system']
        print(f"💻 Sistema: {sys_info['system']} {sys_info['release']}")
        print(f"🏗️ Arquitectura: {sys_info['architecture']}")
        print(f"🐍 Python: {sys_info['python_version'].split()[0]}")
        
        # Hardware
        hw_info = self.info['hardware']
        print(f"⚡ CPU: {hw_info['cpu_cores_physical']}C/{hw_info['cpu_cores_logical']}T")
        print(f"🧠 RAM: {hw_info['memory_total_gb']}GB ({hw_info['memory_percent']}% usado)")
        
        # GPU
        gpu_info = self.info['gpu']
        if gpu_info['cuda_available']:
            print(f"🎮 CUDA: Disponible (v{gpu_info['cuda_version']})")
            for gpu in gpu_info['gpus']:
                print(f"   - GPU {gpu['id']}: {gpu['name']} ({gpu['memory_total_gb']}GB)")
        else:
            print("🎮 CUDA: No disponible")
        
        # Software clave
        sw_info = self.info['software']
        print(f"📦 OpenCV: {sw_info['opencv_version']}")
        print(f"🔥 PyTorch: {sw_info['torch_version']}")
        
        print("=" * 60)
    
    def export_to_file(self, filename: str = None):
        """Exporta la información a un archivo"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"system_info_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"VMS System Information Report\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")
            
            for category, data in self.info.items():
                f.write(f"{category.upper()}\n")
                f.write("-" * 40 + "\n")
                self._write_dict_to_file(f, data, indent=0)
                f.write("\n")
        
        print(f"✅ Información del sistema exportada a: {filename}")
        return filename
    
    def _write_dict_to_file(self, file, data, indent=0):
        """Escribe un diccionario al archivo con formato"""
        spaces = "  " * indent
        
        for key, value in data.items():
            if isinstance(value, dict):
                file.write(f"{spaces}{key}:\n")
                self._write_dict_to_file(file, value, indent + 1)
            elif isinstance(value, list):
                file.write(f"{spaces}{key}:\n")
                for item in value:
                    if isinstance(item, dict):
                        self._write_dict_to_file(file, item, indent + 1)
                        file.write("\n")
                    else:
                        file.write(f"{spaces}  - {item}\n")
            else:
                file.write(f"{spaces}{key}: {value}\n")

def get_system_info() -> SystemInfo:
    """Función conveniente para obtener información del sistema"""
    return SystemInfo()

if __name__ == "__main__":
    # Demo de uso
    system = get_system_info()
    system.print_summary()
    system.export_to_file()
