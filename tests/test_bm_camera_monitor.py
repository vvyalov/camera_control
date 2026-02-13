#!/usr/bin/env python3
"""
Blackmagic Camera Bluetooth Monitor
Полный монитор с отображением всех параметров камеры
"""

import asyncio
import struct
from bleak import BleakClient, BleakScanner
from datetime import datetime
import sys
import signal
import os

# UUID сервиса камеры Blackmagic
BLACKMAGIC_SERVICE_UUID = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

# UUID характеристик
CAMERA_STATUS_UUID = "7fe8691d-95dc-4fc5-8abd-ca74339b51b9"
TIMECODE_UUID = "6d8f2110-86f1-41bf-9afb-451d87e976c8"
INCOMING_DATA_UUID = "b864e140-76a0-416a-bf30-5876504537d9"

# ========== ТВОЯ ПОЛНАЯ ОРИГИНАЛЬНАЯ КАРТА BLACKMAGIC_MONITOR_MAP ==========
BLACKMAGIC_MONITOR_MAP = [
    # ========== CAMERA STATUS (UUID: 7fe8691d-95dc-4fc5-8abd-ca74339b51b9) ==========
    {
        "uuid": "7fe8691d-95dc-4fc5-8abd-ca74339b51b9",
        "name": "camera_status",
        "description": "Статус камеры (8-bit флаги)",
        "length": 1,
        "parser": "status_flags",
        "fields": [
            {"bit": 0, "name": "power_on", "description": "Камера включена"},
            {"bit": 1, "name": "connected", "description": "BLE соединение"},
            {"bit": 2, "name": "paired", "description": "Спарен"},
            {"bit": 3, "name": "versions_verified", "description": "Версии проверены"},
            {"bit": 4, "name": "initial_payload", "description": "Первый пакет"},
            {"bit": 5, "name": "ready", "description": "Камера готова"}
        ]
    },
    
    # ========== TIMECODE (UUID: 6d8f2110-86f1-41bf-9afb-451d87e976c8) ==========
    {
        "uuid": "6d8f2110-86f1-41bf-9afb-451d87e976c8",
        "name": "timecode",
        "description": "Таймкод HH:MM:SS:FF (BCD)",
        "length": 4,
        "parser": "bcd_timecode",
        "fields": [
            {"byte": 0, "name": "hours", "description": "Часы (0-23)"},
            {"byte": 1, "name": "minutes", "description": "Минуты (0-59)"},
            {"byte": 2, "name": "seconds", "description": "Секунды (0-59)"},
            {"byte": 3, "name": "frames", "description": "Кадры (0-24/30)"}
        ]
    },
    
    # ========== INCOMING CAMERA CONTROL (UUID: b864e140-76a0-416a-bf30-5876504537d9) ==========
    # ========== CATEGORY 0: LENS ==========
    {
        "category": 0,
        "parameter": 0,
        "name": "focus",
        "description": "Фокусировка",
        "type": "fixed16",
        "unit": "norm",
        "min": 0.0,
        "max": 1.0,
        "default": 0.5,
        "interpretation": "0.0 = ближний, 1.0 = дальний"
    },
    {
        "category": 0,
        "parameter": 1,
        "name": "instant_autofocus",
        "description": "Мгновенная автофокусировка",
        "type": "void",
        "interpretation": "триггер"
    },
    {
        "category": 0,
        "parameter": 2,
        "name": "aperture_fstop",
        "description": "Диафрагма (AV)",
        "type": "fixed16",
        "unit": "AV",
        "min": -1.0,
        "max": 16.0,
        "interpretation": "AV = sqrt(2^fstop)"
    },
    {
        "category": 0,
        "parameter": 3,
        "name": "aperture_normalised",
        "description": "Диафрагма (нормализованная)",
        "type": "fixed16",
        "unit": "norm",
        "min": 0.0,
        "max": 1.0,
        "default": 0.5,
        "interpretation": "0.0 = минимум, 1.0 = максимум"
    },
    {
        "category": 0,
        "parameter": 4,
        "name": "aperture_ordinal",
        "description": "Диафрагма (позиция)",
        "type": "int16",
        "min": 0,
        "max": 256,
        "interpretation": "шаг от минимума к максимуму"
    },
    {
        "category": 0,
        "parameter": 5,
        "name": "instant_auto_aperture",
        "description": "Мгновенная авто-диафрагма",
        "type": "void",
        "interpretation": "триггер"
    },
    {
        "category": 0,
        "parameter": 6,
        "name": "ois",
        "description": "Оптическая стабилизация",
        "type": "boolean",
        "interpretation": "true = вкл, false = выкл"
    },
    {
        "category": 0,
        "parameter": 7,
        "name": "zoom_mm",
        "description": "Зум (мм)",
        "type": "int16",
        "unit": "mm",
        "min": 0,
        "max": 4000,
        "interpretation": "абсолютное фокусное расстояние"
    },
    {
        "category": 0,
        "parameter": 8,
        "name": "zoom_normalised",
        "description": "Зум (нормализованный)",
        "type": "fixed16",
        "unit": "norm",
        "min": 0.0,
        "max": 1.0,
        "interpretation": "0.0 = wide, 1.0 = tele"
    },
    {
        "category": 0,
        "parameter": 9,
        "name": "zoom_speed",
        "description": "Скорость зума",
        "type": "fixed16",
        "min": -1.0,
        "max": 1.0,
        "interpretation": "-1.0 = wide быстро, 0 = стоп, +1.0 = tele быстро"
    },
    
    # ========== CATEGORY 1: VIDEO ==========
    {
        "category": 1,
        "parameter": 0,
        "name": "video_mode",
        "description": "Режим видео",
        "type": "int8[5]",
        "fields": [
            {"index": 0, "name": "frame_rate", "unit": "fps"},
            {"index": 1, "name": "m_rate", "description": "0=regular, 1=M-rate"},
            {"index": 2, "name": "dimensions", "description": "0=NTSC, 1=PAL, 2=720, 3=1080, 4=2kDCI, 5=2k16:9, 6=UHD, 7=3k, 8=4kDCI, 9=4k16:9, 10=4.6k2.4:1, 11=4.6k"},
            {"index": 3, "name": "interlaced", "description": "0=progressive, 1=interlaced"},
            {"index": 4, "name": "color_space", "description": "0=YUV"}
        ]
    },
    {
        "category": 1,
        "parameter": 1,
        "name": "gain_legacy",
        "description": "Усиление (до 4.9)",
        "type": "int8",
        "min": 1,
        "max": 128,
        "interpretation": "1x, 2x, 4x, 8x, 16x, 32x, 64x, 128x"
    },
    {
        "category": 1,
        "parameter": 2,
        "name": "white_balance",
        "description": "Баланс белого",
        "type": "int16[2]",
        "fields": [
            {"index": 0, "name": "temperature", "unit": "K", "min": 2500, "max": 10000, "default": 5600},
            {"index": 1, "name": "tint", "min": -50, "max": 50, "default": 0}
        ]
    },
    {
        "category": 1,
        "parameter": 3,
        "name": "set_auto_wb",
        "description": "Установить авто-ББ",
        "type": "void",
        "interpretation": "триггер"
    },
    {
        "category": 1,
        "parameter": 4,
        "name": "restore_auto_wb",
        "description": "Восстановить авто-ББ",
        "type": "void",
        "interpretation": "триггер"
    },
    {
        "category": 1,
        "parameter": 5,
        "name": "exposure_us",
        "description": "Выдержка (микросекунды)",
        "type": "int32",
        "unit": "us",
        "min": 1,
        "max": 42000
    },
    {
        "category": 1,
        "parameter": 6,
        "name": "exposure_ordinal",
        "description": "Выдержка (позиция)",
        "type": "int16",
        "min": 0,
        "interpretation": "шаг от минимума к максимуму"
    },
    {
        "category": 1,
        "parameter": 7,
        "name": "dynamic_range",
        "description": "Динамический диапазон",
        "type": "int8",
        "enum": {
            0: "film",
            1: "video",
            2: "extended_video"
        }
    },
    {
        "category": 1,
        "parameter": 8,
        "name": "sharpening",
        "description": "Резкость",
        "type": "int8",
        "enum": {
            0: "off",
            1: "low",
            2: "medium",
            3: "high"
        }
    },
    {
        "category": 1,
        "parameter": 9,
        "name": "recording_format",
        "description": "Формат записи",
        "type": "int16[5]",
        "fields": [
            {"index": 0, "name": "frame_rate", "unit": "fps"},
            {"index": 1, "name": "sensor_frame_rate", "unit": "fps"},
            {"index": 2, "name": "width", "unit": "px"},
            {"index": 3, "name": "height", "unit": "px"},
            {"index": 4, "name": "flags", "type": "bitfield"}
        ]
    },
    {
        "category": 1,
        "parameter": 10,
        "name": "auto_exposure_mode",
        "description": "Режим авто-экспозиции",
        "type": "int8",
        "enum": {
            0: "manual_trigger",
            1: "iris",
            2: "shutter",
            3: "iris_shutter",
            4: "shutter_iris"
        }
    },
    {
        "category": 1,
        "parameter": 11,
        "name": "shutter_angle",
        "description": "Угол затвора",
        "type": "int32",
        "unit": "deg*100",
        "min": 100,
        "max": 36000,
        "default": 18000
    },
    {
        "category": 1,
        "parameter": 12,
        "name": "shutter_speed",
        "description": "Выдержка (дробь)",
        "type": "int32",
        "unit": "1/s",
        "min": 1,
        "max": 5000,
        "default": 50
    },
    {
        "category": 1,
        "parameter": 13,
        "name": "gain_db",
        "description": "Усиление (дБ)",
        "type": "int8",
        "unit": "dB",
        "min": -128,
        "max": 127,
        "default": 0
    },
    {
        "category": 1,
        "parameter": 14,
        "name": "iso",
        "description": "ISO",
        "type": "int32",
        "min": 0,
        "max": 2147483647,
        "default": 400
    },
    {
        "category": 1,
        "parameter": 15,
        "name": "display_lut",
        "description": "LUT дисплея",
        "type": "int8[2]",
        "fields": [
            {"index": 0, "name": "selected", "enum": {0: "none", 1: "custom", 2: "film_to_video", 3: "film_to_extended"}},
            {"index": 1, "name": "enabled", "type": "boolean"}
        ]
    },
    {
        "category": 1,
        "parameter": 16,
        "name": "nd_filter",
        "description": "ND фильтр",
        "type": "fixed16",
        "unit": "stops",
        "min": 0.0,
        "max": 16.0,
        "default": 0.0
    },
    
    # ========== CATEGORY 2: AUDIO ==========
    {
        "category": 2,
        "parameter": 0,
        "name": "mic_level",
        "description": "Уровень микрофона",
        "type": "fixed16",
        "unit": "norm",
        "min": 0.0,
        "max": 1.0,
        "default": 0.5
    },
    {
        "category": 2,
        "parameter": 1,
        "name": "headphone_level",
        "description": "Уровень наушников",
        "type": "fixed16",
        "unit": "norm",
        "min": 0.1,
        "max": 1.0,
        "default": 0.5
    },
    {
        "category": 2,
        "parameter": 2,
        "name": "headphone_mix",
        "description": "Микшер наушников",
        "type": "fixed16",
        "unit": "norm",
        "min": 0.1,
        "max": 1.0,
        "default": 0.5
    },
    {
        "category": 2,
        "parameter": 3,
        "name": "speaker_level",
        "description": "Уровень динамика",
        "type": "fixed16",
        "unit": "norm",
        "min": 0.1,
        "max": 1.0,
        "default": 0.5
    },
    {
        "category": 2,
        "parameter": 4,
        "name": "input_type",
        "description": "Тип входа",
        "type": "int8",
        "enum": {
            0: "internal_mic",
            1: "line",
            2: "mic_low",
            3: "mic_high"
        }
    },
    {
        "category": 2,
        "parameter": 5,
        "name": "input_levels",
        "description": "Уровни входа",
        "type": "fixed16[2]",
        "fields": [
            {"index": 0, "name": "ch0", "unit": "norm", "min": 0.0, "max": 1.0},
            {"index": 1, "name": "ch1", "unit": "norm", "min": 0.0, "max": 1.0}
        ]
    },
    {
        "category": 2,
        "parameter": 6,
        "name": "phantom_power",
        "description": "Фантомное питание",
        "type": "boolean"
    },
    
    # ========== CATEGORY 3: OUTPUT ==========
    {
        "category": 3,
        "parameter": 0,
        "name": "overlay_enables",
        "description": "Включение оверлеев",
        "type": "uint16_bitfield",
        "fields": [
            {"bit": 0, "name": "display_status"},
            {"bit": 1, "name": "frame_guides"}
        ]
    },
    {
        "category": 3,
        "parameter": 1,
        "name": "frame_guides_style_v3",
        "description": "Стиль направляющих (3.x)",
        "type": "int8",
        "enum": {
            0: "HDTV",
            1: "4:3",
            2: "2.4:1",
            3: "2.39:1",
            4: "2.35:1",
            5: "1.85:1",
            6: "thirds"
        }
    },
    {
        "category": 3,
        "parameter": 2,
        "name": "frame_guides_opacity_v3",
        "description": "Прозрачность направляющих (3.x)",
        "type": "fixed16",
        "unit": "norm",
        "min": 0.1,
        "max": 1.0
    },
    {
        "category": 3,
        "parameter": 3,
        "name": "overlays_v4",
        "description": "Оверлеи (4.0+)",
        "type": "int8[4]",
        "fields": [
            {"index": 0, "name": "frame_guides_style", "enum": {0: "off", 1: "2.4:1", 2: "2.39:1", 3: "2.35:1", 4: "1.85:1", 5: "16:9", 6: "14:9", 7: "4:3", 8: "2:1", 9: "4:5", 10: "1:1"}},
            {"index": 1, "name": "frame_guides_opacity", "min": 0, "max": 100},
            {"index": 2, "name": "safe_area_percent", "min": 0, "max": 100},
            {"index": 3, "name": "grid_style", "type": "bitfield", "bits": {"0": "thirds", "1": "cross_hairs", "2": "center_dot", "3": "horizon"}}
        ]
    },
    
    # ========== CATEGORY 4: DISPLAY ==========
    {
        "category": 4,
        "parameter": 0,
        "name": "brightness",
        "description": "Яркость",
        "type": "fixed16",
        "unit": "norm",
        "min": 0.0,
        "max": 1.0,
        "default": 0.5
    },
    {
        "category": 4,
        "parameter": 1,
        "name": "exposure_focus_tools",
        "description": "Инструменты экспозиции/фокуса",
        "type": "int16_bitfield",
        "fields": [
            {"bit": 0, "name": "zebra"},
            {"bit": 1, "name": "focus_assist"},
            {"bit": 2, "name": "false_color"}
        ]
    },
    {
        "category": 4,
        "parameter": 2,
        "name": "zebra_level",
        "description": "Уровень зебры",
        "type": "fixed16",
        "unit": "norm",
        "min": 0.0,
        "max": 1.0,
        "default": 0.7
    },
    {
        "category": 4,
        "parameter": 3,
        "name": "peaking_level",
        "description": "Уровень пикинга",
        "type": "fixed16",
        "unit": "norm",
        "min": 0.0,
        "max": 1.0,
        "default": 0.5
    },
    {
        "category": 4,
        "parameter": 4,
        "name": "color_bars",
        "description": "Цветные полосы",
        "type": "int8",
        "min": 0,
        "max": 30,
        "interpretation": "0=off, 1-30=вкл с таймаутом (сек)"
    },
    {
        "category": 4,
        "parameter": 5,
        "name": "focus_assist",
        "description": "Ассистент фокуса",
        "type": "int8[2]",
        "fields": [
            {"index": 0, "name": "method", "enum": {0: "peak", 1: "colored_lines"}},
            {"index": 1, "name": "color", "enum": {0: "red", 1: "green", 2: "blue", 3: "white", 4: "black"}}
        ]
    },
    {
        "category": 4,
        "parameter": 6,
        "name": "program_return_feed",
        "description": "Возврат программы",
        "type": "int8",
        "min": 0,
        "max": 30,
        "interpretation": "0=off, 1-30=вкл с таймаутом"
    },
    
    # ========== CATEGORY 5: TALLY ==========
    {
        "category": 5,
        "parameter": 0,
        "name": "tally_brightness",
        "description": "Яркость TALLY (оба)",
        "type": "fixed16",
        "unit": "norm",
        "min": 0.0,
        "max": 1.0,
        "default": 0.5
    },
    {
        "category": 5,
        "parameter": 1,
        "name": "front_tally_brightness",
        "description": "Яркость переднего TALLY",
        "type": "fixed16",
        "unit": "norm",
        "min": 0.0,
        "max": 1.0,
        "default": 0.5
    },
    {
        "category": 5,
        "parameter": 2,
        "name": "rear_tally_brightness",
        "description": "Яркость заднего TALLY",
        "type": "fixed16",
        "unit": "norm",
        "min": 0.0,
        "max": 1.0,
        "default": 0.5
    },
    
    # ========== CATEGORY 6: REFERENCE ==========
    {
        "category": 6,
        "parameter": 0,
        "name": "reference_source",
        "description": "Источник референса",
        "type": "int8",
        "enum": {
            0: "internal",
            1: "program",
            2: "external"
        }
    },
    {
        "category": 6,
        "parameter": 1,
        "name": "reference_offset",
        "description": "Смещение референса",
        "type": "int32",
        "unit": "pixels"
    },
    
    # ========== CATEGORY 7: CONFIGURATION ==========
    {
        "category": 7,
        "parameter": 0,
        "name": "rtc",
        "description": "Часы реального времени",
        "type": "int32[2]",
        "fields": [
            {"index": 0, "name": "time", "format": "BCD", "description": "HHMMSSFF"},
            {"index": 1, "name": "date", "format": "BCD", "description": "YYYYMMDD"}
        ]
    },
    {
        "category": 7,
        "parameter": 1,
        "name": "language",
        "description": "Язык системы",
        "type": "string",
        "length": 2,
        "format": "ISO-639-1"
    },
    {
        "category": 7,
        "parameter": 2,
        "name": "timezone",
        "description": "Часовой пояс",
        "type": "int32",
        "unit": "minutes",
        "interpretation": "смещение от UTC"
    },
    {
        "category": 7,
        "parameter": 3,
        "name": "location",
        "description": "GPS координаты",
        "type": "int64[2]",
        "format": "BCD",
        "fields": [
            {"index": 0, "name": "latitude"},
            {"index": 1, "name": "longitude"}
        ]
    },
    
    # ========== CATEGORY 8: COLOR CORRECTION ==========
    {
        "category": 8,
        "parameter": 0,
        "name": "lift",
        "description": "Lift коррекция",
        "type": "fixed16[4]",
        "fields": [
            {"index": 0, "name": "red", "min": -2.0, "max": 2.0, "default": 0.0},
            {"index": 1, "name": "green", "min": -2.0, "max": 2.0, "default": 0.0},
            {"index": 2, "name": "blue", "min": -2.0, "max": 2.0, "default": 0.0},
            {"index": 3, "name": "luma", "min": -2.0, "max": 2.0, "default": 0.0}
        ]
    },
    {
        "category": 8,
        "parameter": 1,
        "name": "gamma",
        "description": "Gamma коррекция",
        "type": "fixed16[4]",
        "fields": [
            {"index": 0, "name": "red", "min": -4.0, "max": 4.0, "default": 0.0},
            {"index": 1, "name": "green", "min": -4.0, "max": 4.0, "default": 0.0},
            {"index": 2, "name": "blue", "min": -4.0, "max": 4.0, "default": 0.0},
            {"index": 3, "name": "luma", "min": -4.0, "max": 4.0, "default": 0.0}
        ]
    },
    {
        "category": 8,
        "parameter": 2,
        "name": "gain",
        "description": "Gain коррекция",
        "type": "fixed16[4]",
        "fields": [
            {"index": 0, "name": "red", "min": 0.0, "max": 16.0, "default": 1.0},
            {"index": 1, "name": "green", "min": 0.0, "max": 16.0, "default": 1.0},
            {"index": 2, "name": "blue", "min": 0.0, "max": 16.0, "default": 1.0},
            {"index": 3, "name": "luma", "min": 0.0, "max": 16.0, "default": 1.0}
        ]
    },
    {
        "category": 8,
        "parameter": 3,
        "name": "offset",
        "description": "Offset коррекция",
        "type": "fixed16[4]",
        "fields": [
            {"index": 0, "name": "red", "min": -8.0, "max": 8.0, "default": 0.0},
            {"index": 1, "name": "green", "min": -8.0, "max": 8.0, "default": 0.0},
            {"index": 2, "name": "blue", "min": -8.0, "max": 8.0, "default": 0.0},
            {"index": 3, "name": "luma", "min": -8.0, "max": 8.0, "default": 0.0}
        ]
    },
    {
        "category": 8,
        "parameter": 4,
        "name": "contrast",
        "description": "Контраст",
        "type": "fixed16[2]",
        "fields": [
            {"index": 0, "name": "pivot", "min": 0.0, "max": 1.0, "default": 0.5},
            {"index": 1, "name": "adjust", "min": 0.0, "max": 2.0, "default": 1.0}
        ]
    },
    {
        "category": 8,
        "parameter": 5,
        "name": "luma_mix",
        "description": "Luma mix",
        "type": "fixed16",
        "min": 0.0,
        "max": 1.0,
        "default": 1.0
    },
    {
        "category": 8,
        "parameter": 6,
        "name": "color_adjust",
        "description": "Цветокоррекция",
        "type": "fixed16[2]",
        "fields": [
            {"index": 0, "name": "hue", "min": -1.0, "max": 1.0, "default": 0.0},
            {"index": 1, "name": "saturation", "min": 0.0, "max": 2.0, "default": 1.0}
        ]
    },
    {
        "category": 8,
        "parameter": 7,
        "name": "correction_reset",
        "description": "Сброс цветокоррекции",
        "type": "void"
    },
    
    # ========== CATEGORY 10: MEDIA ==========
    {
        "category": 10,
        "parameter": 0,
        "name": "codec",
        "description": "Кодек",
        "type": "int8[2]",
        "fields": [
            {
                "index": 0, "name": "type",
                "enum": {
                    0: "CinemaDNG",
                    1: "DNxHD",
                    2: "ProRes",
                    3: "Blackmagic RAW"
                }
            },
            {
                "index": 1, "name": "variant",
                "enum": {
                    0: {"ProRes": "HQ", "BRAW": "Q0", "CinemaDNG": "uncompressed"},
                    1: {"ProRes": "422", "BRAW": "Q5", "CinemaDNG": "3:1"},
                    2: {"ProRes": "LT", "BRAW": "3:1"},
                    3: {"ProRes": "Proxy", "BRAW": "5:1"},
                    4: {"ProRes": "444", "BRAW": "8:1"},
                    5: {"ProRes": "444XQ", "BRAW": "12:1"}
                }
            }
        ]
    },
    {
        "category": 10,
        "parameter": 1,
        "name": "transport_mode",
        "description": "Режим транспорта",
        "type": "int8[5]",
        "fields": [
            {"index": 0, "name": "mode", "enum": {0: "preview", 1: "play", 2: "record"}},
            {"index": 1, "name": "speed", "min": -128, "max": 127},
            {"index": 2, "name": "flags", "type": "bitfield"},
            {"index": 3, "name": "slot1_type", "enum": {0: "CFast", 1: "SD", 2: "SSD", 3: "USB"}},
            {"index": 4, "name": "slot2_type", "enum": {0: "CFast", 1: "SD", 2: "SSD", 3: "USB"}}
        ]
    },
    {
        "category": 10,
        "parameter": 2,
        "name": "playback_control",
        "description": "Управление воспроизведением",
        "type": "int8",
        "enum": {
            0: "previous",
            1: "next"
        }
    },
    {
        "category": 10,
        "parameter": 3,
        "name": "still_capture",
        "description": "Фотосъемка",
        "type": "void"
    },
    
    # ========== CATEGORY 11: PTZ ==========
    {
        "category": 11,
        "parameter": 0,
        "name": "pan_tilt",
        "description": "Скорость Pan/Tilt",
        "type": "fixed16[2]",
        "fields": [
            {"index": 0, "name": "pan", "min": -1.0, "max": 1.0},
            {"index": 1, "name": "tilt", "min": -1.0, "max": 1.0}
        ]
    },
    {
        "category": 11,
        "parameter": 1,
        "name": "memory_preset",
        "description": "Пресеты памяти",
        "type": "int8[2]",
        "fields": [
            {"index": 0, "name": "command", "enum": {0: "reset", 1: "store", 2: "recall"}},
            {"index": 1, "name": "slot", "min": 0, "max": 5}
        ]
    },
    
    # ========== CATEGORY 12: METADATA ==========
    {
        "category": 12,
        "parameter": 0,
        "name": "reel",
        "description": "Номер рила",
        "type": "int16",
        "min": 0,
        "max": 999
    },
    {
        "category": 12,
        "parameter": 1,
        "name": "scene_tags",
        "description": "Теги сцены",
        "type": "int8[3]",
        "fields": [
            {"index": 0, "name": "shot_type", "enum": {-1: "none", 0: "WS", 1: "CU", 2: "MS", 3: "BCU", 4: "MCU", 5: "ECU"}},
            {"index": 1, "name": "interior_exterior", "enum": {0: "exterior", 1: "interior"}},
            {"index": 2, "name": "day_night", "enum": {0: "night", 1: "day"}}
        ]
    },
    {
        "category": 12,
        "parameter": 2,
        "name": "scene",
        "description": "Название сцены",
        "type": "string",
        "length": 5
    },
    {
        "category": 12,
        "parameter": 3,
        "name": "take",
        "description": "Номер дубля",
        "type": "int8[2]",
        "fields": [
            {"index": 0, "name": "number", "min": 1, "max": 99},
            {"index": 1, "name": "tag", "enum": {1: "none", 0: "PU", 1: "VFX", 2: "SER"}}
        ]
    },
    {
        "category": 12,
        "parameter": 4,
        "name": "good_take",
        "description": "Хороший дубль",
        "type": "void"
    },
    {
        "category": 12,
        "parameter": 5,
        "name": "camera_id",
        "description": "ID камеры",
        "type": "string",
        "length": 29
    },
    {
        "category": 12,
        "parameter": 6,
        "name": "camera_operator",
        "description": "Оператор",
        "type": "string",
        "length": 29
    },
    {
        "category": 12,
        "parameter": 7,
        "name": "director",
        "description": "Режиссер",
        "type": "string",
        "length": 28
    },
    {
        "category": 12,
        "parameter": 8,
        "name": "project_name",
        "description": "Название проекта",
        "type": "string",
        "length": 29
    },
    {
        "category": 12,
        "parameter": 9,
        "name": "lens_type",
        "description": "Тип объектива",
        "type": "string",
        "length": 56
    },
    {
        "category": 12,
        "parameter": 10,
        "name": "lens_iris",
        "description": "Ирис объектива",
        "type": "string",
        "length": 20
    },
    {
        "category": 12,
        "parameter": 11,
        "name": "lens_focal_length",
        "description": "Фокусное расстояние",
        "type": "string",
        "length": 30
    },
    {
        "category": 12,
        "parameter": 12,
        "name": "lens_distance",
        "description": "Дистанция фокуса",
        "type": "string",
        "length": 50
    },
    {
        "category": 12,
        "parameter": 13,
        "name": "lens_filter",
        "description": "Фильтр объектива",
        "type": "string",
        "length": 30
    },
    {
        "category": 12,
        "parameter": 14,
        "name": "slate_mode",
        "description": "Режим слейта",
        "type": "int8",
        "enum": {
            0: "recording",
            1: "playback"
        }
    },
    {
        "category": 12,
        "parameter": 15,
        "name": "slate_target",
        "description": "Цель слейта",
        "type": "string",
        "length": 32
    }
]

class BlackmagicMonitor:
    def __init__(self):
        self.client = None
        self.connected = False
        self.device_data = {
            'timecode': '00:00:00:00',
            'camera_status': 'Нет данных',
            'iso': '--',
            'shutter': '--',
            'aperture': '--',
            'white_balance': '--',
            'frame_rate': '--',
            'resolution': '--',
            'gain': '--',
            'dynamic_range': '--',
            'recording': False,
            'lens': '--',
            'codec': '--',
            'project': '--',
            'camera_id': '--',
            'operator': '--',
            'director': '--'
        }
        self.uuid_map = {}
        self.param_map = {}
        self.running = True
        self.target_address = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"
        
        # Загружаем конфигурацию из карты
        for item in BLACKMAGIC_MONITOR_MAP:
            if 'uuid' in item:
                self.uuid_map[item['uuid'].lower()] = item
            elif 'category' in item:
                key = (item['category'], item['parameter'])
                self.param_map[key] = item
                
    async def scan_for_camera(self):
        """Сканирование камер Blackmagic"""
        print("🔍 Сканирование камер Blackmagic...")
        print("-" * 60)
        
        devices = await BleakScanner.discover(timeout=10)
        camera_devices = []
        
        for device in devices:
            if device.name:
                print(f"  {device.name} - {device.address}")
                
                if self.target_address in str(device.address):
                    camera_devices.append(device)
                    print(f"  ✅ ВАША КАМЕРА: {device.name}")
                elif device.name and ('cam' in device.name.lower() or 'blackmagic' in device.name.lower()):
                    camera_devices.append(device)
                    print(f"  ✅ КАМЕРА: {device.name}")
        
        print("-" * 60)
        return camera_devices
    
    def parse_timecode(self, data):
        """Парсинг BCD таймкода - ТОЧНО РАБОЧАЯ ВЕРСИЯ"""
        try:
            if len(data) >= 12:
                # Байты [8], [9], [10], [11] содержат таймкод
                frames_byte = data[8]   # кадры
                seconds_byte = data[9]   # секунды
                minutes_byte = data[10]  # минуты
                hours_byte = data[11]    # часы
                
                hours = ((hours_byte >> 4) & 0x0F) * 10 + (hours_byte & 0x0F)
                minutes = ((minutes_byte >> 4) & 0x0F) * 10 + (minutes_byte & 0x0F)
                seconds = ((seconds_byte >> 4) & 0x0F) * 10 + (seconds_byte & 0x0F)
                frames = ((frames_byte >> 4) & 0x0F) * 10 + (frames_byte & 0x0F)
                
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
                
            elif len(data) >= 4:
                # Формат: [кадры, секунды, минуты, часы]
                frames = ((data[0] >> 4) & 0x0F) * 10 + (data[0] & 0x0F)
                seconds = ((data[1] >> 4) & 0x0F) * 10 + (data[1] & 0x0F)
                minutes = ((data[2] >> 4) & 0x0F) * 10 + (data[2] & 0x0F)
                hours = ((data[3] >> 4) & 0x0F) * 10 + (data[3] & 0x0F)
                
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
                
        except Exception as e:
            pass
        
        return "00:00:00:00"
    
    def parse_blackmagic_packet(self, data):
        """Парсинг пакета данных Blackmagic"""
        try:
            if len(data) < 8 or data[0] != 0xFF:
                return None
                
            packet = {
                'length': data[1],
                'camera_index': data[2],
                'group': data[4],
                'parameter': data[5],
                'operation': data[6]
            }
            
            # Используем карту для определения параметра
            key = (packet['group'], packet['parameter'])
            
            # Группа 1: Video
            if packet['group'] == 1:
                if packet['parameter'] == 9 and len(data) >= 18:
                    frame_rate = data[8]
                    width = data[12] + (data[13] << 8)
                    height = data[14] + (data[15] << 8)
                    
                    self.device_data['frame_rate'] = f"{frame_rate}fps"
                    self.device_data['resolution'] = f"{width}x{height}"
                    
                elif packet['parameter'] == 14 and len(data) >= 12:
                    iso = struct.unpack('<i', data[8:12])[0]
                    self.device_data['iso'] = f"{iso}"
                    
                elif packet['parameter'] == 11 and len(data) >= 12:
                    shutter = struct.unpack('<i', data[8:12])[0] / 100
                    self.device_data['shutter'] = f"{shutter:.1f}°"
                    
                elif packet['parameter'] == 13 and len(data) >= 9:
                    gain = struct.unpack('<b', data[8:9])[0]
                    self.device_data['gain'] = f"{gain:+d}dB"
                    
                elif packet['parameter'] == 7 and len(data) >= 9:
                    dr = data[8]
                    dr_names = {0: "Film", 1: "Video", 2: "Extended"}
                    self.device_data['dynamic_range'] = dr_names.get(dr, f"{dr}")
                    
                elif packet['parameter'] == 2 and len(data) >= 12:
                    temp = struct.unpack('<h', data[8:10])[0]
                    tint = struct.unpack('<h', data[10:12])[0]
                    self.device_data['white_balance'] = f"{temp}K/{tint:+d}"
            
            # Группа 0: Lens
            elif packet['group'] == 0:
                if packet['parameter'] == 2 and len(data) >= 10:
                    aperture = struct.unpack('<h', data[8:10])[0] / 256.0
                    self.device_data['aperture'] = f"f/{aperture:.1f}"
            
            # Группа 10: Media
            elif packet['group'] == 10:
                if packet['parameter'] == 1 and len(data) >= 9:
                    mode = data[8]
                    self.device_data['recording'] = (mode == 2)
                elif packet['parameter'] == 0 and len(data) >= 10:
                    codec_type = data[8]
                    codec_names = {0: "CinemaDNG", 1: "DNxHD", 2: "ProRes", 3: "BRAW"}
                    self.device_data['codec'] = codec_names.get(codec_type, f"{codec_type}")
            
            # Группа 12: Metadata
            elif packet['group'] == 12:
                if packet['parameter'] == 9 and len(data) > 12:
                    lens_bytes = data[8:]
                    lens = ""
                    for b in lens_bytes:
                        if b == 0:
                            break
                        if 32 <= b <= 126:  # только печатные символы
                            lens += chr(b)
                    if lens:
                        self.device_data['lens'] = lens
                
                elif packet['parameter'] == 5 and len(data) > 12:
                    camera_bytes = data[8:]
                    camera_id = ""
                    for b in camera_bytes:
                        if b == 0:
                            break
                        if 32 <= b <= 126:
                            camera_id += chr(b)
                    if camera_id:
                        self.device_data['camera_id'] = camera_id
                
                elif packet['parameter'] == 8 and len(data) > 12:
                    project_bytes = data[8:]
                    project = ""
                    for b in project_bytes:
                        if b == 0:
                            break
                        if 32 <= b <= 126:
                            project += chr(b)
                    if project:
                        self.device_data['project'] = project
                            
        except Exception as e:
            pass
    
    def parse_status_flags(self, data):
        """Парсинг флагов статуса"""
        if not data or len(data) < 1:
            return "Нет данных"
        
        flags = []
        flag_names = {
            0: "включена",
            1: "BLE",
            2: "спарена",
            3: "версии",
            4: "первый",
            5: "готова"
        }
        
        byte_val = data[0] if isinstance(data, bytes) else data
        
        for bit in range(6):
            if byte_val >> bit & 1:
                flags.append(flag_names.get(bit, f"бит{bit}"))
        
        status_str = f"0x{byte_val:02x}"
        if flags:
            status_str += f" [{', '.join(flags)}]"
        
        return status_str
    
    def notification_handler(self, sender, data):
        """Обработчик входящих уведомлений"""
        char_uuid = sender.uuid.lower() if hasattr(sender, 'uuid') else str(sender).lower()
        
        # Таймкод
        if TIMECODE_UUID in char_uuid:
            self.device_data['timecode'] = self.parse_timecode(data)
        
        # Статус камеры
        elif CAMERA_STATUS_UUID in char_uuid:
            self.device_data['camera_status'] = self.parse_status_flags(data)
        
        # Входящие данные камеры
        elif INCOMING_DATA_UUID in char_uuid:
            self.parse_blackmagic_packet(data)
    
    def clear_screen(self):
        """Очистка экрана"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def print_header(self):
        """Вывод заголовка"""
        print("=" * 70)
        print("   BLACKMAGIC CAMERA MONITOR - Bluetooth")
        print("=" * 70)
        print(f"   Время: {datetime.now().strftime('%H:%M:%S')}")
        print(f"   Статус: {'🟢 ПОДКЛЮЧЕНО' if self.connected else '🔴 ОТКЛЮЧЕНО'}")
        if self.client and hasattr(self.client, 'address') and self.client.address:
            print(f"   Устройство: {self.client.address[:8]}...")
        print("=" * 70)
        print()
    
    def print_device_info(self):
        """Вывод ВСЕЙ информации о камере"""
        
        # Таймкод и запись
        record_icon = "🔴" if self.device_data.get('recording') else "⚫"
        print(f"{record_icon} ТАЙМКОД: {self.device_data.get('timecode', '--:--:--:--')}")
        print(f"📊 СТАТУС: {self.device_data.get('camera_status', 'Нет данных')}")
        print()
        
        # Видео параметры
        print("📹 ВИДЕО:")
        print(f"   🎬 FPS:        {self.device_data.get('frame_rate', '--')}")
        print(f"   📐 Разрешение: {self.device_data.get('resolution', '--')}")
        print(f"   🎚️ ISO:        {self.device_data.get('iso', '--')}")
        print(f"   ⏱️  Выдержка:  {self.device_data.get('shutter', '--')}")
        print(f"   📈 Gain:       {self.device_data.get('gain', '--')}")
        print(f"   🌓 DR:         {self.device_data.get('dynamic_range', '--')}")
        print(f"   ⚖️  WB:         {self.device_data.get('white_balance', '--')}")
        print(f"   🎞️  Кодек:      {self.device_data.get('codec', '--')}")
        print()
        
        # Объектив
        print("🔭 ОБЪЕКТИВ:")
        print(f"   🔘 Диафрагма:  {self.device_data.get('aperture', '--')}")
        print(f"   📷 Модель:     {self.device_data.get('lens', '--')}")
        print()
        
        # Метаданные
        print("📋 МЕТАДАННЫЕ:")
        print(f"   🆔 Камера:     {self.device_data.get('camera_id', '--')}")
        print(f"   🎬 Проект:     {self.device_data.get('project', '--')}")
        print()
    
    def print_controls(self):
        """Вывод подсказок по управлению"""
        print("-" * 70)
        print("УПРАВЛЕНИЕ: Ctrl+C - Выход")
        print("-" * 70)
    
    async def display_loop(self):
        """Основной цикл отображения"""
        while self.running:
            self.clear_screen()
            self.print_header()
            
            if self.connected:
                self.print_device_info()
            else:
                print("\n   ⚠️ ОЖИДАНИЕ ПОДКЛЮЧЕНИЯ К КАМЕРЕ...\n")
                print("   Убедитесь что:")
                print("   • Камера включена")
                print("   • Bluetooth активирован (Menu → Setup → Bluetooth → On)")
                print("   • Камера не подключена к другому устройству")
            
            self.print_controls()
            await asyncio.sleep(0.5)
    
    async def connect_to_camera(self, device):
        """Подключение к камере"""
        try:
            print(f"\n🔄 Подключение к {device.name}...")
            
            async with BleakClient(device, timeout=30.0, disconnected_callback=self.on_disconnect) as client:
                self.client = client
                self.connected = True
                
                print(f"✅ Подключено успешно!")
                print("\n🔌 Получение данных камеры...")
                
                # Подписываемся на характеристики
                for service in client.services:
                    for char in service.characteristics:
                        if 'notify' in char.properties:
                            try:
                                await client.start_notify(char.uuid, self.notification_handler)
                            except:
                                pass
                        
                        if 'read' in char.properties:
                            try:
                                value = await client.read_gatt_char(char.uuid)
                                if value and len(value) > 0:
                                    self.notification_handler(char, value)
                            except:
                                pass
                
                print("🎬 Мониторинг запущен. Нажмите Ctrl+C для выхода.\n")
                
                while self.running and self.connected:
                    await asyncio.sleep(1)
                    
        except Exception as e:
            print(f"\n❌ Ошибка подключения: {e}")
            self.connected = False
            self.client = None
    
    def on_disconnect(self, client):
        """Callback при отключении"""
        self.connected = False
        self.client = None
    
    async def run(self):
        """Основная функция"""
        display_task = asyncio.create_task(self.display_loop())
        
        while self.running:
            try:
                cameras = await self.scan_for_camera()
                
                if cameras:
                    await self.connect_to_camera(cameras[0])
                else:
                    print("\n⏳ Камера не найдена. Повторное сканирование через 5 секунд...")
                    await asyncio.sleep(5)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"\n❌ Ошибка: {e}")
                if self.running:
                    await asyncio.sleep(3)
        
        display_task.cancel()
    
    def stop(self):
        """Остановка монитора"""
        self.running = False

async def main():
    monitor = BlackmagicMonitor()
    
    def signal_handler():
        print("\n\n👋 Завершение работы...")
        monitor.stop()
    
    try:
        loop = asyncio.get_event_loop()
        for sig in [signal.SIGINT, signal.SIGTERM]:
            loop.add_signal_handler(sig, signal_handler)
    except:
        pass
    
    try:
        await monitor.run()
    except asyncio.CancelledError:
        pass
    finally:
        print("\nМонитор остановлен")

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║            BLACKMAGIC CAMERA BLUETOOTH MONITOR           ║
║                    Полная версия v1.0                    ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Выход...")