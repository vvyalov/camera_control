"""
Blackmagic Camera Monitoring - Парсер
Определяет тип пакета и вызывает соответствующий декодер
"""

from typing import Dict, Any, Callable, Optional
from monitors.bm_monitor.constants import (
    CHAR_CAMERA_STATUS_UUID, CHAR_TIMECODE_UUID, CHAR_INCOMING_CONTROL_UUID,
    CategoryId, CommandId
)
from .decoder import BlackmagicDecoder
from .utils import bcd_to_timecode, bcd_to_int


class BlackmagicParser:
    """
    Парсер BLE нотификаций от Blackmagic камеры
    Маршрутизирует пакеты по UUID характеристики
    """
    
    def __init__(self):
        self.decoder = BlackmagicDecoder()
        self.callbacks = {}
        
    def register_callback(self, name: str, callback: Callable):
        """Регистрация коллбека на событие"""
        self.callbacks[name] = callback
        
    def _trigger_callback(self, name: str, data: Any):
        """Вызов коллбека если зарегистрирован"""
        if name in self.callbacks:
            self.callbacks[name](data)
    
    def parse_notification(self, char_uuid: str, data: bytes) -> Dict[str, Any]:
        """
        Основной метод парсинга BLE нотификаций
        """
        result = {
            'characteristic': char_uuid,
            'timestamp': None,  # TODO: добавить time.time()
            'raw': data.hex(),
            'parsed': None,
            'type': 'unknown'
        }
        
        # 1. CAMERA STATUS
        if char_uuid.lower() == CHAR_CAMERA_STATUS_UUID.lower():
            return self._parse_camera_status(data)
            
        # 2. TIMECODE
        elif char_uuid.lower() == CHAR_TIMECODE_UUID.lower():
            return self._parse_timecode(data)
            
        # 3. INCOMING CAMERA CONTROL (ВСЕ НАСТРОЙКИ)
        elif char_uuid.lower() == CHAR_INCOMING_CONTROL_UUID.lower():
            return self._parse_incoming_control(data)
            
        else:
            result['error'] = f'Unknown characteristic: {char_uuid}'
            
        return result
    
    def _parse_camera_status(self, data: bytes) -> Dict[str, Any]:
        """Парсинг Camera Status (8-bit флаги)"""
        result = {
            'characteristic': CHAR_CAMERA_STATUS_UUID,
            'type': 'camera_status',
            'raw': data.hex()
        }
        
        if len(data) >= 1:
            status = data[0]
            from monitors.bm_monitor.constants import CameraStatus
            
            result['status_byte'] = status
            result['flags'] = {
                'power_on': bool(status & CameraStatus.POWER_ON),
                'connected': bool(status & CameraStatus.CONNECTED),
                'paired': bool(status & CameraStatus.PAIRED),
                'versions_verified': bool(status & CameraStatus.VERSIONS_VERIFIED),
                'initial_payload': bool(status & CameraStatus.INITIAL_PAYLOAD),
                'ready': bool(status & CameraStatus.READY)
            }
            
            # Строковое представление
            active_flags = []
            for flag, name in [
                (CameraStatus.POWER_ON, "POWER_ON"),
                (CameraStatus.CONNECTED, "CONNECTED"),
                (CameraStatus.PAIRED, "PAIRED"),
                (CameraStatus.VERSIONS_VERIFIED, "VERIFIED"),
                (CameraStatus.INITIAL_PAYLOAD, "INITIAL"),
                (CameraStatus.READY, "READY")
            ]:
                if status & flag:
                    active_flags.append(name)
                    
            result['display'] = ' | '.join(active_flags) if active_flags else 'NONE'
            
        self._trigger_callback('camera_status', result)
        return result
    
    def _parse_timecode(self, data: bytes) -> Dict[str, Any]:
        """Парсинг Timecode (32-bit BCD)"""
        result = {
            'characteristic': CHAR_TIMECODE_UUID,
            'type': 'timecode',
            'raw': data.hex()
        }
        
        if len(data) >= 4:
            # Первые 4 байта - BCD таймкод
            tc_bytes = data[:4]
            tc_int = bcd_to_int(tc_bytes)
            tc_str = bcd_to_timecode(tc_bytes)
            
            result['timecode_bcd'] = tc_int
            result['timecode'] = tc_str
            result['hours'] = int(tc_str[0:2])
            result['minutes'] = int(tc_str[3:5])
            result['seconds'] = int(tc_str[6:8])
            result['frames'] = int(tc_str[9:11])
            result['display'] = tc_str
            
        self._trigger_callback('timecode', result)
        return result
    
    def _parse_incoming_control(self, data: bytes) -> Dict[str, Any]:
        """Парсинг Incoming Camera Control (все настройки)"""
        result = {
            'characteristic': CHAR_INCOMING_CONTROL_UUID,
            'type': 'camera_control',
            'raw': data.hex(),
            'packets': []
        }
        
        offset = 0
        while offset < len(data):
            # Проверяем, достаточно ли данных для заголовка
            if offset + 8 > len(data):
                break
                
            header = self.decoder.decode_packet_header(data[offset:])
            if not header:
                offset += 4  # 32-bit alignment
                continue
                
            packet = {
                'header': header,
                'offset': offset
            }
            
            # Декодируем в зависимости от категории
            category = header['category']
            parameter = header['parameter']
            
            # Специальные случаи для сложных параметров
            if category == CategoryId.VIDEO and parameter == 9:
                packet['decoded'] = self.decoder.decode_recording_format(header['payload'])
            elif category == CategoryId.MEDIA and parameter == 1:
                packet['decoded'] = self.decoder.decode_media_transport(header['payload'])
            else:
                packet['decoded'] = self.decoder.decode_parameter(
                    category, parameter, header['data_type'], header['payload']
                )
                
            result['packets'].append(packet)
            
            # Перемещаемся к следующему пакету
            # Заголовок 8 байт + payload + padding до 4 байт
            packet_size = 8 + header['length']
            # Padding to 32-bit
            if packet_size % 4 != 0:
                packet_size += 4 - (packet_size % 4)
            offset += packet_size
            
        result['packet_count'] = len(result['packets'])
        
        self._trigger_callback('camera_control', result)
        return result