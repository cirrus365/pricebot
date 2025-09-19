"""
System resource monitoring for Chatbot
"""
import psutil
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SystemMonitor:
    """Handles system resource monitoring"""
    
    @classmethod
    def get_cpu_info(cls) -> Dict:
        """Get CPU usage information"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            return {
                'percent': cpu_percent,
                'cores': cpu_count,
                'frequency': cpu_freq.current if cpu_freq else None,
                'frequency_max': cpu_freq.max if cpu_freq else None
            }
        except Exception as e:
            logger.error(f"Error getting CPU info: {e}")
            return {}
    
    @classmethod
    def get_memory_info(cls) -> Dict:
        """Get memory usage information"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                'total': memory.total,
                'used': memory.used,
                'available': memory.available,
                'percent': memory.percent,
                'swap_total': swap.total,
                'swap_used': swap.used,
                'swap_percent': swap.percent
            }
        except Exception as e:
            logger.error(f"Error getting memory info: {e}")
            return {}
    
    @classmethod
    def get_disk_info(cls) -> Dict:
        """Get disk usage information"""
        try:
            disk = psutil.disk_usage('/')
            
            return {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent
            }
        except Exception as e:
            logger.error(f"Error getting disk info: {e}")
            return {}
    
    @classmethod
    def format_bytes(cls, bytes_value: int) -> str:
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    
    @classmethod
    def get_system_info(cls) -> str:
        """Get formatted system resource information"""
        try:
            # Get all system info
            cpu_info = cls.get_cpu_info()
            memory_info = cls.get_memory_info()
            disk_info = cls.get_disk_info()
            
            # Format the response
            response = "🖥️ **System Resource Monitor**\n\n"
            
            # CPU Information
            if cpu_info:
                response += "**📊 CPU Usage:**\n"
                response += f"• Usage: {cpu_info.get('percent', 'N/A')}%\n"
                response += f"• Cores: {cpu_info.get('cores', 'N/A')}\n"
                if cpu_info.get('frequency'):
                    response += f"• Frequency: {cpu_info['frequency']:.2f} MHz"
                    if cpu_info.get('frequency_max'):
                        response += f" (Max: {cpu_info['frequency_max']:.2f} MHz)"
                    response += "\n"
            
            # Memory Information
            if memory_info:
                response += "\n**💾 Memory (RAM):**\n"
                total = memory_info.get('total', 0)
                used = memory_info.get('used', 0)
                available = memory_info.get('available', 0)
                percent = memory_info.get('percent', 0)
                
                response += f"• Total: {cls.format_bytes(total)}\n"
                response += f"• Used: {cls.format_bytes(used)} ({percent:.1f}%)\n"
                response += f"• Available: {cls.format_bytes(available)}\n"
                
                # Swap information
                swap_total = memory_info.get('swap_total', 0)
                if swap_total > 0:
                    swap_used = memory_info.get('swap_used', 0)
                    swap_percent = memory_info.get('swap_percent', 0)
                    response += f"\n**💱 Swap:**\n"
                    response += f"• Total: {cls.format_bytes(swap_total)}\n"
                    response += f"• Used: {cls.format_bytes(swap_used)} ({swap_percent:.1f}%)\n"
            
            # Disk Information
            if disk_info:
                response += "\n**💿 Disk Space:**\n"
                total = disk_info.get('total', 0)
                used = disk_info.get('used', 0)
                free = disk_info.get('free', 0)
                percent = disk_info.get('percent', 0)
                
                response += f"• Total: {cls.format_bytes(total)}\n"
                response += f"• Used: {cls.format_bytes(used)} ({percent:.1f}%)\n"
                response += f"• Free: {cls.format_bytes(free)}\n"
            
            # Add status indicators
            response += "\n**📈 Status:**\n"
            
            # CPU status
            cpu_percent = cpu_info.get('percent', 0)
            if cpu_percent < 50:
                response += "• CPU: ✅ Normal\n"
            elif cpu_percent < 80:
                response += "• CPU: ⚠️ Moderate load\n"
            else:
                response += "• CPU: 🔴 High load\n"
            
            # Memory status
            mem_percent = memory_info.get('percent', 0)
            if mem_percent < 60:
                response += "• Memory: ✅ Normal\n"
            elif mem_percent < 85:
                response += "• Memory: ⚠️ Moderate usage\n"
            else:
                response += "• Memory: 🔴 High usage\n"
            
            # Disk status
            disk_percent = disk_info.get('percent', 0)
            if disk_percent < 70:
                response += "• Disk: ✅ Normal\n"
            elif disk_percent < 90:
                response += "• Disk: ⚠️ Getting full\n"
            else:
                response += "• Disk: 🔴 Critical - Low space\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return "❌ Error: Unable to retrieve system information. Please ensure psutil is installed and the bot has necessary permissions."

system_monitor = SystemMonitor()
