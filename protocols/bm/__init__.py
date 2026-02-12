"""
Пакет protocol - работа с протоколом Blackmagic BMPCC v.0.1
"""

from .parser import parse_bmpcc_message
from .decoder import (
    decode_shutter, 
    decode_aperture, 
    decode_iso, 
    decode_lens_name,
    decode_recording_status,
    decode_value
)
from .constants import (
    UUID_NOTIFICATIONS,
    UUID_TELEMETRY,
    UUID_STATUS,
    CATEGORY_EXPOSURE,
    CATEGORY_CAMERA,
    CATEGORY_SYSTEM,
    CATEGORY_TELEMETRY,
    CATEGORY_COMMANDS,
    CATEGORY_LENS,
    SUBCAT_SHUTTER,
    SUBCAT_APERTURE,
    SUBCAT_ISO_HIGH,
    SUBCAT_ISO_LOW,
    SUBCAT_LENS_NAME,
    SUBCAT_RECORDING_STATUS,
    CATEGORY_NAMES
)
from .tables import (
    SHUTTER_TABLE,
    APERTURE_TABLE,
    RECORDING_STATUS,
    PARAM_NAMES
)

__all__ = [
    'parse_bmpcc_message',
    'decode_shutter',
    'decode_aperture', 
    'decode_iso',
    'decode_lens_name',
    'decode_recording_status',
    'decode_value',
    'UUID_NOTIFICATIONS',
    'UUID_TELEMETRY',
    'UUID_STATUS',
    'CATEGORY_EXPOSURE',
    'CATEGORY_CAMERA',
    'CATEGORY_SYSTEM',
    'CATEGORY_TELEMETRY',
    'CATEGORY_COMMANDS',
    'CATEGORY_LENS',
    'SUBCAT_SHUTTER',
    'SUBCAT_APERTURE',
    'SUBCAT_ISO_HIGH',
    'SUBCAT_ISO_LOW',
    'SUBCAT_LENS_NAME',
    'SUBCAT_RECORDING_STATUS',
    'CATEGORY_NAMES',
    'SHUTTER_TABLE',
    'APERTURE_TABLE',
    'RECORDING_STATUS',
    'PARAM_NAMES',
]

__version__ = "0.1.0"
