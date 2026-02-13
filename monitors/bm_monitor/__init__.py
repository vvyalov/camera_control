"""
Blackmagic Camera Monitoring System
Полная система мониторинга Blackmagic камер через BLE

Источники:
- Официальная документация Blackmagic SDI/Bluetooth Protocol v1.5
- PROTOCOL.json (coral/community)
- BlueMagic32 (ESP32 implementation)

Версия: 1.0.0
"""

__version__ = "1.0.0"
__author__ = "Blackmagic Community"

# ==================== CONSTANTS ====================
from monitors.bm_monitor.constants import (  # type: ignore
    # BLE UUIDs
    BMD_CAMERA_SERVICE_UUID,
    DEVICE_INFO_SERVICE_UUID,
    CHAR_CAMERA_STATUS_UUID,
    CHAR_TIMECODE_UUID,
    CHAR_INCOMING_CONTROL_UUID,
    CHAR_MANUFACTURER_UUID,
    CHAR_MODEL_UUID,
    CHAR_PROTOCOL_VERSION_UUID,
    
    # Enums
    CameraStatus,
    TransportMode,
    CodecType,
    ProResVariant,
    BrawVariant,
    DynamicRangeMode,
    AudioInputType,
    MediaSlotType,
    FormatFlags,
    
    # Protocol
    CommandId,
    DataType,
    CategoryId,
    
    # Parameter definitions
    MONITOR_PARAMETERS,
    TRIGGER_PARAMETERS,
    ParamInfo,
)

# ==================== DECODER ====================
from .decoder import BlackmagicDecoder

# ==================== PARSER ====================
from .parser import BlackmagicParser

# ==================== STATE ====================
from .tables import (
    CameraState,
    CameraStatusState,
    TimecodeState,
    LensState,
    VideoState,
    AudioState,
    DisplayState,
    MediaState,
    MetadataState,
)

# ==================== MONITOR ====================
from .monitor import BlackmagicMonitor

# ==================== UTILS ====================
from .utils import (
    bcd_to_int,
    bcd_to_timecode,
    fixed16_to_float,
    float_to_fixed16,
    bytes_to_int16,
    bytes_to_int32,
    bytes_to_string,
    parse_format_flags,
)

# ==================== ЧТО ДОСТУПНО "ИЗ КОРОБКИ" ====================
__all__ = [
    # Версия
    '__version__',
    
    # UUIDs
    'BMD_CAMERA_SERVICE_UUID',
    'DEVICE_INFO_SERVICE_UUID',
    'CHAR_CAMERA_STATUS_UUID',
    'CHAR_TIMECODE_UUID',
    'CHAR_INCOMING_CONTROL_UUID',
    'CHAR_MANUFACTURER_UUID',
    'CHAR_MODEL_UUID',
    'CHAR_PROTOCOL_VERSION_UUID',
    
    # Enums
    'CameraStatus',
    'TransportMode',
    'CodecType',
    'ProResVariant',
    'BrawVariant',
    'DynamicRangeMode',
    'AudioInputType',
    'MediaSlotType',
    'FormatFlags',
    
    # Protocol
    'CommandId',
    'DataType',
    'CategoryId',
    
    # Parameter info
    'ParamInfo',
    'MONITOR_PARAMETERS',
    'TRIGGER_PARAMETERS',
    
    # Core classes
    'BlackmagicDecoder',
    'BlackmagicParser',
    'BlackmagicMonitor',
    'CameraState',
    
    # State containers
    'CameraStatusState',
    'TimecodeState',
    'LensState',
    'VideoState',
    'AudioState',
    'DisplayState',
    'MediaState',
    'MetadataState',
    
    # Utils
    'bcd_to_int',
    'bcd_to_timecode',
    'fixed16_to_float',
    'float_to_fixed16',
    'bytes_to_int16',
    'bytes_to_int32',
    'bytes_to_string',
    'parse_format_flags',
]

# ==================== КРАТКАЯ ДОКУМЕНТАЦИЯ ====================

def help():
    """Быстрая справка по использованию"""
    print("""
    📡 Blackmagic Camera Monitoring System v1.0.0
    
    БЫСТРЫЙ СТАРТ:
    ---------------
    from monitors.bm_monitor import BlackmagicMonitor
    
    # Создаем монитор
    monitor = BlackmagicMonitor()
    
    # Подписываемся на изменения
    def on_change(section, param, value):
        print(f"{section}.{param} = {value}")
    
    monitor.register_state_callback(on_change)
    
    # BLE клиент передает данные:
    monitor.process_notification(char_uuid, data_bytes)
    
    СОСТОЯНИЕ КАМЕРЫ:
    -----------------
    monitor.state.status          # Статус подключения
    monitor.state.timecode        # Таймкод
    monitor.state.video.iso       # ISO
    monitor.state.media.transport_mode  # REC/PLAY/PREVIEW
    
    Полная документация: README.md
    """)

# ==================== ИНИЦИАЛИЗАЦИЯ ПРИ ИМПОРТЕ ====================

_print_greeting = True  # Отключаем при тестах

if _print_greeting:
    print(f"📷 Blackmagic Camera Monitoring v{__version__} загружен")
    print(f"   Поддерживается {len(MONITOR_PARAMETERS) + len(TRIGGER_PARAMETERS)} параметров")