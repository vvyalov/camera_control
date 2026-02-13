"""
Blackmagic Camera Monitoring - Constants
Источники: 
- Официальная документация v1.5
- PROTOCOL.json (coral)
- BlueMagic32 (ESP32 implementation)
"""
# Закомментируйте ЭТО:
# from monitors.bm_monitor import something
# from . import something
# from monitors.bm_monitor.anything import *
from enum import Enum, IntEnum, IntFlag
from dataclasses import dataclass
from typing import Tuple

# ==================== BLE UUIDs ====================

# Сервисы
BMD_CAMERA_SERVICE_UUID = "291d567a-6d75-11e6-8b77-86f30ca893d3"
DEVICE_INFO_SERVICE_UUID = "0000180a-0000-1000-8000-00805f9b34fb"

# Характеристики - МОНИТОРИНГ (нотификации)
CHAR_CAMERA_STATUS_UUID = "7fe8691d-95dc-4fc5-8abd-ca74339b51b9"  # Статус камеры
CHAR_TIMECODE_UUID = "6d8f2110-86f1-41bf-9afb-451d87e976c8"      # Таймкод
CHAR_INCOMING_CONTROL_UUID = "b864e140-76a0-416a-bf30-5876504537d9"  # Все настройки

# Характеристики - ЧТЕНИЕ
CHAR_MANUFACTURER_UUID = "00002a29-0000-1000-8000-00805f9b34fb"
CHAR_MODEL_UUID = "00002a24-0000-1000-8000-00805f9b34fb"
CHAR_PROTOCOL_VERSION_UUID = "8f1fd018-b508-456f-8f82-3d392bee2706"


# ==================== CAMERA STATUS FLAGS ====================

class CameraStatus(IntFlag):
    """Статус камеры (8-bit)"""
    NONE = 0x00
    POWER_ON = 0x01          # Камера включена
    CONNECTED = 0x02         # BLE соединение установлено
    PAIRED = 0x04           # Спарен
    VERSIONS_VERIFIED = 0x08  # Версии проверены
    INITIAL_PAYLOAD = 0x10  # Первые данные получены
    READY = 0x20            # Камера готова к работе


# ==================== TRANSPORT MODE ====================

class TransportMode(IntEnum):
    """Режим транспорта (Preview/Play/Record)"""
    PREVIEW = 0
    PLAY = 1
    RECORD = 2
    
    @classmethod
    def to_string(cls, value: int) -> str:
        return {
            0: "PREVIEW",
            1: "PLAY",
            2: "RECORD"
        }.get(value, "UNKNOWN")


# ==================== CODECS ====================

class CodecType(IntEnum):
    """Тип кодека"""
    CINEMADNG = 0
    DNXHD = 1
    PRORES = 2
    BRAW = 3
    
    @classmethod
    def to_string(cls, value: int) -> str:
        return {
            0: "CinemaDNG",
            1: "DNxHD",
            2: "ProRes",
            3: "Blackmagic RAW"
        }.get(value, "UNKNOWN")


class ProResVariant(IntEnum):
    """Варианты ProRes"""
    HQ = 0
    _422 = 1
    LT = 2
    PROXY = 3
    _444 = 4
    _444XQ = 5
    
    @classmethod
    def to_string(cls, value: int) -> str:
        return {
            0: "ProRes HQ",
            1: "ProRes 422",
            2: "ProRes LT",
            3: "ProRes Proxy",
            4: "ProRes 4444",
            5: "ProRes 4444 XQ"
        }.get(value, "UNKNOWN")


class BrawVariant(IntEnum):
    """Варианты Blackmagic RAW"""
    Q0 = 0
    Q5 = 1
    _3_1 = 2
    _5_1 = 3
    _8_1 = 4
    _12_1 = 5
    
    @classmethod
    def to_string(cls, value: int) -> str:
        return {
            0: "BRAW Q0",
            1: "BRAW Q5",
            2: "BRAW 3:1",
            3: "BRAW 5:1",
            4: "BRAW 8:1",
            5: "BRAW 12:1"
        }.get(value, "UNKNOWN")


# ==================== VIDEO ====================

class DynamicRangeMode(IntEnum):
    """Режим динамического диапазона"""
    FILM = 0
    VIDEO = 1
    EXTENDED_VIDEO = 2
    
    @classmethod
    def to_string(cls, value: int) -> str:
        return {
            0: "Film",
            1: "Video",
            2: "Extended Video"
        }.get(value, "UNKNOWN")


class FormatFlags(IntFlag):
    """Флаги формата записи"""
    FILE_M_RATE = 1 << 0
    SENSOR_M_RATE = 1 << 1
    SENSOR_OFF_SPEED = 1 << 2
    INTERLACED = 1 << 3
    WINDOWED_MODE = 1 << 4


# ==================== AUDIO ====================

class AudioInputType(IntEnum):
    """Тип аудиовхода"""
    INTERNAL_MIC = 0
    LINE_LEVEL = 1
    MIC_LOW = 2
    MIC_HIGH = 3
    
    @classmethod
    def to_string(cls, value: int) -> str:
        return {
            0: "Internal Mic",
            1: "Line Level",
            2: "Mic Level (Low)",
            3: "Mic Level (High)"
        }.get(value, "UNKNOWN")


# ==================== MEDIA ====================

class MediaSlotType(IntEnum):
    """Тип носителя"""
    CFAST = 0
    SD = 1
    SSD = 2
    USB = 3
    
    @classmethod
    def to_string(cls, value: int) -> str:
        return {
            0: "CFast",
            1: "SD Card",
            2: "SSD",
            3: "USB"
        }.get(value, "UNKNOWN")


# ==================== COMMAND PROTOCOL ====================

class CommandId(IntEnum):
    """ID команд (SDI/BLE протокол)"""
    CHANGE_CONFIGURATION = 0x00  # Все параметры мониторинга


class DataType(IntEnum):
    """Типы данных в протоколе"""
    VOID_BOOL = 0
    INT8 = 1
    INT16 = 2
    INT32 = 3
    INT64 = 4
    UTF8_STRING = 5
    # 6-127 reserved
    FIXED16_5_11 = 128  # signed 5.11 fixed point


class CategoryId(IntEnum):
    """Группы параметров"""
    LENS = 0
    VIDEO = 1
    AUDIO = 2
    OUTPUT = 3
    DISPLAY = 4
    TALLY = 5
    REFERENCE = 6
    CONFIGURATION = 7
    COLOR_CORRECTION = 8
    # 9 reserved
    MEDIA = 10
    PTZ = 11
    METADATA = 12
    
    @classmethod
    def to_string(cls, value: int) -> str:
        names = {
            0: "Lens",
            1: "Video",
            2: "Audio",
            3: "Output",
            4: "Display",
            5: "Tally",
            6: "Reference",
            7: "Configuration",
            8: "Color Correction",
            10: "Media",
            11: "PTZ",
            12: "Metadata"
        }
        return names.get(value, f"Unknown({value})")


# ==================== ПАРАМЕТРЫ МОНИТОРИНГА ====================
# Словарь: (category, parameter) -> имя, тип, диапазон

@dataclass
class ParamInfo:
    """Информация о параметре мониторинга"""
    name: str
    data_type: DataType
    unit: str = ""
    min_val: float = 0
    max_val: float = 0
    default: float = 0
    enum_class: type = None


MONITOR_PARAMETERS = {
    # LENS (0.x)
    (0, 0): ParamInfo("Focus", DataType.FIXED16_5_11, unit="norm", min_val=0, max_val=1, default=0.5),
    (0, 2): ParamInfo("Aperture_FStop", DataType.FIXED16_5_11, unit="AV", min_val=-1, max_val=16, default=2.8),
    (0, 3): ParamInfo("Aperture_Normalised", DataType.FIXED16_5_11, unit="norm", min_val=0, max_val=1, default=0.5),
    (0, 4): ParamInfo("Aperture_Ordinal", DataType.INT16, min_val=0, max_val=256, default=0),
    (0, 6): ParamInfo("OIS", DataType.VOID_BOOL),
    (0, 7): ParamInfo("Zoom_mm", DataType.INT16, unit="mm", min_val=0, max_val=4000, default=0),
    (0, 8): ParamInfo("Zoom_Normalised", DataType.FIXED16_5_11, unit="norm", min_val=0, max_val=1, default=0),
    
    # VIDEO (1.x)
    (1, 2): ParamInfo("WhiteBalance", DataType.INT16, unit="K", min_val=2500, max_val=10000, default=5600),
    (1, 2): ParamInfo("Tint", DataType.INT16, unit="tint", min_val=-50, max_val=50, default=0),  # index 1
    (1, 5): ParamInfo("Exposure_us", DataType.INT32, unit="us", min_val=1, max_val=42000, default=10000),
    (1, 7): ParamInfo("DynamicRange", DataType.INT8, enum_class=DynamicRangeMode),
    (1, 8): ParamInfo("Sharpening", DataType.INT8, min_val=0, max_val=3, default=1),
    (1, 9): ParamInfo("FrameRate", DataType.INT16, unit="fps", min_val=1, max_val=240, default=24),
    (1, 9): ParamInfo("SensorFrameRate", DataType.INT16, unit="fps", min_val=1, max_val=240, default=24),  # index 1
    (1, 9): ParamInfo("Width", DataType.INT16, unit="px", min_val=640, max_val=8192, default=1920),  # index 2
    (1, 9): ParamInfo("Height", DataType.INT16, unit="px", min_val=480, max_val=4320, default=1080),  # index 3
    (1, 9): ParamInfo("FormatFlags", DataType.INT8, min_val=0, max_val=31, default=0),  # index 4
    (1, 11): ParamInfo("ShutterAngle", DataType.INT32, unit="deg*100", min_val=100, max_val=36000, default=18000),
    (1, 12): ParamInfo("ShutterSpeed", DataType.INT32, unit="1/s", min_val=1, max_val=5000, default=50),
    (1, 13): ParamInfo("Gain_dB", DataType.INT8, unit="dB", min_val=-128, max_val=127, default=0),
    (1, 14): ParamInfo("ISO", DataType.INT32, min_val=0, max_val=2147483647, default=400),
    (1, 16): ParamInfo("NDFilter", DataType.FIXED16_5_11, unit="stops", min_val=0, max_val=16, default=0),
    
    # AUDIO (2.x)
    (2, 0): ParamInfo("MicLevel", DataType.FIXED16_5_11, unit="norm", min_val=0, max_val=1, default=0.5),
    (2, 1): ParamInfo("HeadphoneLevel", DataType.FIXED16_5_11, unit="norm", min_val=0, max_val=1, default=0.5),
    (2, 4): ParamInfo("AudioInputType", DataType.INT8, enum_class=AudioInputType),
    (2, 5): ParamInfo("InputLevelCh0", DataType.FIXED16_5_11, unit="norm", min_val=0, max_val=1, default=0.5),
    (2, 5): ParamInfo("InputLevelCh1", DataType.FIXED16_5_11, unit="norm", min_val=0, max_val=1, default=0.5),
    (2, 6): ParamInfo("PhantomPower", DataType.VOID_BOOL),
    
    # DISPLAY (4.x)
    (4, 0): ParamInfo("Brightness", DataType.FIXED16_5_11, unit="norm", min_val=0, max_val=1, default=0.5),
    (4, 2): ParamInfo("ZebraLevel", DataType.FIXED16_5_11, unit="norm", min_val=0, max_val=1, default=0.7),
    (4, 3): ParamInfo("PeakingLevel", DataType.FIXED16_5_11, unit="norm", min_val=0, max_val=1, default=0.5),
    
    # TALLY (5.x)
    (5, 0): ParamInfo("TallyBrightness", DataType.FIXED16_5_11, unit="norm", min_val=0, max_val=1, default=0.5),
    (5, 1): ParamInfo("FrontTallyBrightness", DataType.FIXED16_5_11, unit="norm", min_val=0, max_val=1, default=0.5),
    (5, 2): ParamInfo("RearTallyBrightness", DataType.FIXED16_5_11, unit="norm", min_val=0, max_val=1, default=0.5),
    
    # MEDIA (10.x)
    (10, 0): ParamInfo("CodecType", DataType.INT8, enum_class=CodecType),
    (10, 0): ParamInfo("CodecVariant", DataType.INT8, min_val=0, max_val=5, default=0),  # index 1
    (10, 1): ParamInfo("TransportMode", DataType.INT8, enum_class=TransportMode),
    (10, 1): ParamInfo("Slot1Type", DataType.INT8, enum_class=MediaSlotType),  # index 3
    (10, 1): ParamInfo("Slot2Type", DataType.INT8, enum_class=MediaSlotType),  # index 4
    (10, 1): ParamInfo("TimeLapse", DataType.VOID_BOOL),  # flag 1<<7 in flags
    
    # PTZ (11.x)
    (11, 0): ParamInfo("PanVelocity", DataType.FIXED16_5_11, unit="norm", min_val=-1, max_val=1, default=0),
    (11, 0): ParamInfo("TiltVelocity", DataType.FIXED16_5_11, unit="norm", min_val=-1, max_val=1, default=0),
    
    # METADATA (12.x)
    (12, 0): ParamInfo("Reel", DataType.INT16, min_val=0, max_val=999, default=0),
    (12, 2): ParamInfo("Scene", DataType.UTF8_STRING),
    (12, 3): ParamInfo("Take", DataType.INT8, min_val=1, max_val=99, default=1),
    (12, 5): ParamInfo("CameraID", DataType.UTF8_STRING),
    (12, 6): ParamInfo("Operator", DataType.UTF8_STRING),
    (12, 8): ParamInfo("Project", DataType.UTF8_STRING),
}

# ==================== ПАКЕТЫ-ТРИГГЕРЫ (VOID) ====================
# Команды, которые не несут данных, но меняют состояние

TRIGGER_PARAMETERS = {
    (0, 1): "InstantAutoFocus",
    (0, 5): "InstantAutoAperture",
    (1, 3): "SetAutoWB",
    (1, 4): "RestoreAutoWB",
    (8, 7): "ColorReset",
    (10, 3): "StillCapture",
    (12, 4): "GoodTake"
}