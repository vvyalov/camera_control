#!/usr/bin/env python3
"""
🔍 BLACKMAGIC PROTOCOL DEBUGGER v2.0
Логгирует ВСЕ сообщения от камеры для анализа протокола
Использует исправленный протокол с разделением на ОСНОВНЫЕ/СЫРЫЕ данные
"""

import os
import sys

# ================= КРИТИЧЕСКИ ВАЖНО =================
# Добавляем путь к проекту для импорта protocols
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
# ====================================================

import asyncio
from datetime import datetime
from collections import defaultdict
from bleak import BleakClient

# ================= ИСПРАВЛЕННЫЕ ИМПОРТЫ =================
from protocols.bm import parse_bmpcc_message
from protocols.bm.parser import format_message_for_log
from protocols.bm.constants import UUID_NOTIFICATIONS

# ================= КОНФИГУРАЦИЯ =================
# Получаем адрес камеры из аргументов
import sys
if len(sys.argv) > 1:
    CAMERA_ADDRESS = sys.argv[1]
elif os.path.exists("selected_camera.txt"):
    with open("selected_camera.txt", "r") as f:
        CAMERA_ADDRESS = f.read().strip()
else:
    print("❌ Адрес камеры не указан!")
    print("Использование: python3 unified_monitor.py <адрес_камеры>")
    sys.exit(1)

LOG_FILE = "camera_debug.log"
# ================================================

class DebugMonitor:
    """Отладочный монитор протокола камеры"""
    
    def __init__(self):
        self.message_count = 0
        self.start_time = datetime.now()
        self.logging_active = True
        
        # Статистика с учётом типов данных
        self.stats = {
            'total': 0,
            'primary': 0,      # Основные параметры (✅)
            'raw': 0,          # Сырые данные (📊)
            'other': 0,        # Остальное (📡)
            'errors': 0,
            'by_category': defaultdict(int),
            'by_type': defaultdict(int),
        }
        
        # Последние значения для основных параметров
        self.last_values = {
            'shutter': None,
            'aperture': None,
            'iso': None,
            'recording': None,
            'zoom': None,
            'focus': None,
        }
        
        # Открываем лог-файл
        self.log_file = open(LOG_FILE, 'a', encoding='utf-8')
        self._write_header()
    
    def _write_header(self):
        """Записывает заголовок в лог-файл"""
        self.log_file.write(f"\n{'='*80}\n")
        self.log_file.write(f"BLACKMAGIC DEBUG SESSION v2.0\n")
        self.log_file.write(f"Время начала: {self.start_time}\n")
        self.log_file.write(f"Камера: {CAMERA_ADDRESS}\n")
        self.log_file.write(f"{'='*80}\n\n")
        self.log_file.write("ПРЕФИКСЫ:\n")
        self.log_file.write("  ✅ - Основные параметры (выдержка, диафрагма, ISO, статус записи)\n")
        self.log_file.write("  📊 - Сырые данные (00:xx, 09:xx) - НЕ для отображения в мониторе\n")
        self.log_file.write("  📡 - Остальные параметры\n")
        self.log_file.write("  ❓ - Неизвестные/ошибочные данные\n")
        self.log_file.write("  🔧 - Служебные сообщения\n")
        self.log_file.write(f"{'='*80}\n\n")
        self.log_file.flush()
