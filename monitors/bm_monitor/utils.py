"""
Blackmagic Camera Monitoring - Утилиты
Декодирование BCD, Fixed16, и т.д.
"""

import struct
from typing import Tuple, Optional


def bcd_to_int(bcd_bytes: bytes) -> int:
    """
    Преобразование BCD (Binary Coded Decimal) в int
    Пример: 0x09125310 -> 9125310 (09:12:53:10)
    """
    result = 0
    for b in bcd_bytes:
        result = result * 100 + ((b >> 4) * 10 + (b & 0x0F))
    return result


def bcd_to_timecode(bcd_bytes: bytes) -> str:
    """
    Преобразование 4 байт BCD в строку таймкода HH:MM:SS:FF
    """
    if len(bcd_bytes) < 4:
        return "00:00:00:00"
    
    hh = ((bcd_bytes[0] >> 4) * 10) + (bcd_bytes[0] & 0x0F)
    mm = ((bcd_bytes[1] >> 4) * 10) + (bcd_bytes[1] & 0x0F)
    ss = ((bcd_bytes[2] >> 4) * 10) + (bcd_bytes[2] & 0x0F)
    ff = ((bcd_bytes[3] >> 4) * 10) + (bcd_bytes[3] & 0x0F)
    
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def fixed16_to_float(value: int) -> float:
    """
    Преобразование signed 5.11 fixed point в float
    Биты: 1 sign, 4 integer, 11 fractional
    Диапазон: -16.0 до 15.9995
    """
    if value >= 0x8000:  # отрицательное
        return -(0x10000 - value) / 2048.0
    else:
        return value / 2048.0


def float_to_fixed16(value: float) -> int:
    """
    Преобразование float в signed 5.11 fixed point
    """
    return int(value * 2048.0) & 0xFFFF


def bytes_to_int16(data: bytes, offset: int = 0, little_endian: bool = True) -> int:
    """2 байта -> int16"""
    if len(data) < offset + 2:
        return 0
    if little_endian:
        return data[offset] + (data[offset + 1] << 8)
    else:
        return (data[offset] << 8) + data[offset + 1]


def bytes_to_int32(data: bytes, offset: int = 0, little_endian: bool = True) -> int:
    """4 байта -> int32"""
    if len(data) < offset + 4:
        return 0
    if little_endian:
        return data[offset] + (data[offset + 1] << 8) + \
               (data[offset + 2] << 16) + (data[offset + 3] << 24)
    else:
        return (data[offset] << 24) + (data[offset + 1] << 16) + \
               (data[offset + 2] << 8) + data[offset + 3]


def bytes_to_string(data: bytes, offset: int = 0, max_len: int = 32) -> str:
    """UTF-8 строка из байт"""
    if offset >= len(data):
        return ""
    end = offset + max_len
    if end > len(data):
        end = len(data)
    # Ищем нулевой терминатор
    for i in range(offset, end):
        if data[i] == 0:
            end = i
            break
    return data[offset:end].decode('utf-8', errors='ignore').strip()


def parse_format_flags(flags: int) -> dict:
    """Разбор флагов формата"""
    return {
        'file_m_rate': bool(flags & 1),
        'sensor_m_rate': bool(flags & 2),
        'sensor_off_speed': bool(flags & 4),
        'interlaced': bool(flags & 8),
        'windowed_mode': bool(flags & 16)
    }