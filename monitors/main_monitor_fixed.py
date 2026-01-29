#!/usr/bin/env python3
"""
🎬 BLACKMAGIC CAMERA MONITOR v4.0 - ИСПРАВЛЕННЫЙ
"""

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import asyncio
from datetime import datetime
from bleak import BleakClient

from protocols.bm import parse_bmpcc_message
from protocols.bm.constants import UUID_NOTIFICATIONS, UUID_TELEMETRY

# ... ВСТАВЬТЕ ВЕСЬ ОСТАЛЬНОЙ КОД ИЗ ИСХОДНОГО ФАЙЛА ДО метода handle_message ...

# А ВМЕСТО handle_message ВСТАВЬТЕ ИСПРАВЛЕННУЮ ВЕРСИЮ ВЫШЕ

# ... И ВЕСЬ ОСТАЛЬНОЙ КОД ПОСЛЕ метода handle_message ...
