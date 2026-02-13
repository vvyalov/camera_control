"""
Blackmagic Camera Monitoring - Декодер
Преобразует сырые данные пакета в значения параметров
"""

from typing import Dict, Any, Tuple, Optional
from monitors.bm_monitor.constants import (
    DataType, MONITOR_PARAMETERS, TRIGGER_PARAMETERS,
    CategoryId, ParamInfo
)
from .utils import (
    fixed16_to_float, bytes_to_int16, bytes_to_int32,
    bytes_to_string, parse_format_flags
)


class BlackmagicDecoder:
    """Декодер параметров Blackmagic камеры"""
    
    @staticmethod
    def decode_packet_header(data: bytes) -> Optional[Dict]:
        """
        Декодирование заголовка пакета SDI/BLE
        Формат: [dest:1][len:1][cmd:1][res:1][cat:1][param:1][type:1][op:1]
        """
        if len(data) < 8:
            return None
            
        header = {
            'destination': data[0],
            'length': data[1],
            'command': data[2],
            'reserved': data[3],
            'category': data[4],
            'parameter': data[5],
            'data_type': data[6],
            'operation': data[7],
            'payload': data[8:8 + data[1]] if data[1] > 0 else b''
        }
        return header
    
    @staticmethod
    def decode_parameter(category: int, parameter: int, 
                         data_type: int, payload: bytes) -> Dict[str, Any]:
        """
        Декодирование параметра по категории и типу данных
        """
        result = {
            'category': category,
            'parameter': parameter,
            'raw': payload.hex(),
            'valid': False,
            'value': None,
            'display': None,
            'unit': ''
        }
        
        # Проверяем триггеры (void-команды)
        if (category, parameter) in TRIGGER_PARAMETERS:
            result['trigger'] = TRIGGER_PARAMETERS[(category, parameter)]
            result['valid'] = True
            return result
        
        # Получаем информацию о параметре
        param_key = (category, parameter)
        if param_key not in MONITOR_PARAMETERS:
            # Некоторые параметры имеют индексы
            result['valid'] = False
            result['error'] = 'Unknown parameter'
            return result
            
        info = MONITOR_PARAMETERS[param_key]
        result['name'] = info.name
        result['unit'] = info.unit
        
        # Декодируем по типу данных
        try:
            if data_type == DataType.VOID_BOOL:
                result['value'] = bool(payload[0]) if payload else False
                result['display'] = 'ON' if result['value'] else 'OFF'
                result['valid'] = True
                
            elif data_type == DataType.INT8:
                if len(payload) >= 1:
                    val = payload[0]
                    if val > 127:
                        val = val - 256  # signed
                    result['value'] = val
                    result['display'] = str(val)
                    result['valid'] = True
                    
            elif data_type == DataType.INT16:
                if len(payload) >= 2:
                    val = bytes_to_int16(payload, 0, little_endian=True)
                    result['value'] = val
                    result['display'] = str(val)
                    result['valid'] = True
                    
            elif data_type == DataType.INT32:
                if len(payload) >= 4:
                    val = bytes_to_int32(payload, 0, little_endian=True)
                    result['value'] = val
                    result['display'] = str(val)
                    result['valid'] = True
                    
            elif data_type == DataType.UTF8_STRING:
                result['value'] = bytes_to_string(payload)
                result['display'] = result['value']
                result['valid'] = True
                
            elif data_type == DataType.FIXED16_5_11:
                if len(payload) >= 2:
                    val_raw = bytes_to_int16(payload, 0, little_endian=True)
                    val_float = fixed16_to_float(val_raw)
                    result['value'] = val_float
                    result['display'] = f"{val_float:.3f}"
                    result['valid'] = True
                    
        except Exception as e:
            result['error'] = str(e)
            result['valid'] = False
            
        return result
    
    @staticmethod
    def decode_recording_format(payload: bytes) -> Dict[str, Any]:
        """
        Специальный декодер для Recording Format (1.9)
        Имеет 5 индексов: frame_rate, sensor_rate, width, height, flags
        """
        result = {
            'category': 1,
            'parameter': 9,
            'name': 'RecordingFormat',
            'valid': False,
            'values': {}
        }
        
        if len(payload) >= 10:  # 5 x int16 = 10 байт
            try:
                frame_rate = bytes_to_int16(payload, 0, little_endian=True)
                sensor_rate = bytes_to_int16(payload, 2, little_endian=True)
                width = bytes_to_int16(payload, 4, little_endian=True)
                height = bytes_to_int16(payload, 6, little_endian=True)
                flags = payload[8] if len(payload) > 8 else 0
                
                result['values'] = {
                    'frame_rate': frame_rate,
                    'sensor_frame_rate': sensor_rate,
                    'width': width,
                    'height': height,
                    'flags': flags,
                    'flags_parsed': parse_format_flags(flags)
                }
                result['display'] = f"{width}x{height} @ {frame_rate}fps"
                result['valid'] = True
                
            except Exception as e:
                result['error'] = str(e)
                
        return result
    
    @staticmethod
    def decode_media_transport(payload: bytes) -> Dict[str, Any]:
        """
        Декодер для Media Transport (10.1)
        Содержит mode, speed, flags, slot1, slot2
        """
        result = {
            'category': 10,
            'parameter': 1,
            'name': 'TransportMode',
            'valid': False,
            'values': {}
        }
        
        if len(payload) >= 5:
            try:
                mode = payload[0]
                speed = payload[1] if payload[1] < 128 else payload[1] - 256
                flags = payload[2]
                slot1 = payload[3]
                slot2 = payload[4] if len(payload) > 4 else 0
                
                from monitors.bm_monitor.constants import TransportMode, MediaSlotType
                
                result['values'] = {
                    'mode': mode,
                    'mode_name': TransportMode.to_string(mode),
                    'speed': speed,
                    'flags': flags,
                    'time_lapse': bool(flags & (1 << 7)),
                    'loop': bool(flags & 1),
                    'play_all': bool(flags & 2),
                    'slot1_type': slot1,
                    'slot1_name': MediaSlotType.to_string(slot1) if slot1 in MediaSlotType._value2member_map_ else 'Unknown',
                    'slot2_type': slot2,
                    'slot2_name': MediaSlotType.to_string(slot2) if slot2 in MediaSlotType._value2member_map_ else 'Unknown'
                }
                result['display'] = f"{result['values']['mode_name']}"
                result['valid'] = True
                
            except Exception as e:
                result['error'] = str(e)
                
        return result