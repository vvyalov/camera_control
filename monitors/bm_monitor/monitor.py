"""
Blackmagic Camera Monitoring - Главный класс
Объединяет парсер, декодер и состояние
"""

import asyncio
from typing import Optional, Dict, Any, Callable
from .parser import BlackmagicParser
from .tables import CameraState


class BlackmagicMonitor:
    """
    Мониторинг Blackmagic камеры через BLE
    Агностик к BLE библиотеке - получает сырые данные и парсит
    """
    
    def __init__(self):
        self.parser = BlackmagicParser()
        self.state = CameraState()
        self.connected = False
        self.camera_model = ""
        self.camera_name = ""
        
        # Подключаем состояние к парсеру
        self.parser.register_callback('camera_status', self._on_camera_status)
        self.parser.register_callback('timecode', self._on_timecode)
        self.parser.register_callback('camera_control', self._on_camera_control)
    
    def _on_camera_status(self, data: Dict):
        """Обработчик статуса"""
        self.state.update_from_parser(data)
    
    def _on_timecode(self, data: Dict):
        """Обработчик таймкода"""
        self.state.update_from_parser(data)
    
    def _on_camera_control(self, data: Dict):
        """Обработчик настроек"""
        self.state.update_from_parser(data)
    
    def process_notification(self, char_uuid: str, data: bytes) -> Dict:
        """
        Основной вход для BLE нотификаций
        Вызывается из BLE-клиента
        """
        parsed = self.parser.parse_notification(char_uuid, data)
        self.state.update_from_parser(parsed)
        return parsed
    
    def process_device_info(self, manufacturer: str, model: str, version: str = ""):
        """Информация об устройстве"""
        self.state.device_info = {
            'manufacturer': manufacturer,
            'model': model,
            'protocol_version': version
        }
        self.camera_model = model
        self.connected = True
    
    def register_state_callback(self, callback: Callable):
        """Подписка на изменения состояния"""
        self.state.register_callback(callback)
    
    # ========== HELPER GETTERS ==========
    
    @property
    def is_recording(self) -> bool:
        return self.state.media.transport_mode == 2
    
    @property
    def is_preview(self) -> bool:
        return self.state.media.transport_mode == 0
    
    @property
    def current_timecode(self) -> str:
        return self.state.timecode.timecode
    
    @property
    def battery_level(self) -> Optional[int]:
        """TODO: Добавить мониторинг батареи если есть"""
        return None
    
    def get_all_params(self) -> Dict:
        """Все текущие параметры"""
        return {
            'status': self.state.status,
            'timecode': self.state.timecode,
            'lens': self.state.lens,
            'video': self.state.video,
            'audio': self.state.audio,
            'display': self.state.display,
            'media': self.state.media,
            'metadata': self.state.metadata
        }