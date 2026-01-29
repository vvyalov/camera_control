# camera_control/monitors/__init__.py
"""
Мониторы для отображения данных камеры
"""

from .unified_monitor import DebugMonitor
from .main_monitor import CameraMonitor

__all__ = ['DebugMonitor', 'CameraMonitor']