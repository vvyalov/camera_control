#!/usr/bin/env python3
"""
🎬 LIVE DEBUG MONITOR - Сравнение старого и нового парсера в реальном времени
Запуск: python3 live_debug_monitor.py <адрес_камеры>
"""

import asyncio
import sys
import os
from datetime import datetime
from bleak import BleakClient
import json
import math

# ================= НАСТРОЙКИ =================
# Получаем адрес камеры
if len(sys.argv) > 1:
    CAMERA_ADDRESS = sys.argv[1]
elif os.path.exists("selected_camera.txt"):
    with open("selected_camera.txt", "r") as f:
        CAMERA_ADDRESS = f.read().strip()
else:
    print("❌ Адрес камеры не указан!")
    print("Использование: python3 live_debug_monitor.py <адрес_камеры>")
    sys.exit(1)

# ================= ВАЖНО: UUID из BlueMagic32 =================
# Основные характеристики для получения данных
UUID_BMD_CAMERA_SERVICE = "291D567A-6D75-11E6-8B77-86F30CA893D3"

# Характеристики, на которые нужно ПОДПИСАТЬСЯ для получения данных
UUID_INCOMING_CAMERA_CONTROL = "B864E140-76A0-416A-BF30-5876504537D9"  # Основные параметры
UUID_TIMECODE = "6D8F2110-86F1-41BF-9AFB-451D87E976C8"                 # Таймкод
UUID_CAMERA_STATUS = "7FE8691D-95DC-4FC5-8ABD-CA74339B51B9"            # Статус

# Для отправки команд (нам не нужно)
UUID_OUTGOING_CAMERA_CONTROL = "5DD3465F-1AEE-4299-8493-D2ECA2F8E1BB"
UUID_DEVICE_NAME = "FFAC0C52-C9FB-41A0-B063-CC76282EB89C"

# ================= ИМПОРТ СТАРОГО ПАРСЕРА =================
import sys
import os

# Путь к корню проекта
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root.endswith('tests'):
    project_root = os.path.dirname(project_root)  # На уровень выше

print(f"🔄 Путь к проекту: {project_root}")

# Добавляем путь к проекту
sys.path.insert(0, project_root)

try:
    # Теперь правильный импорт
    from protocols.bm.parser import parse_bmpcc_message as parse_old
    print("✅ Старый парсер загружен из protocols.bm.parser")
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("⚠️  Использую заглушку для тестирования")
    
    def parse_old(data):
        return {
            "type": "stub", 
            "data": data.hex(),
            "value_human": "СТАРЫЙ ПАРСЕР (заглушка)"
        }

# ================= НОВЫЙ ПАРСЕР (на основе BlueMagic32) =================
class NewProtocolParser:
    def __init__(self):
        # Загружаем PROTOCOL.json
        protocol_path = os.path.join(os.path.dirname(__file__), "PROTOCOL.json")
        try:
            with open(protocol_path, 'r', encoding='utf-8') as f:
                self.protocol = json.load(f)
            print(f"✅ Новый парсер: загружен PROTOCOL.json")
            
            # Карта параметров для быстрого поиска
            self.param_map = {}
            for group in self.protocol.get('groups', []):
                group_id = group.get('id')
                for param in group.get('parameters', []):
                    param_id = param.get('id')
                    param_name = param.get('parameter', 'Unknown')
                    self.param_map[(group_id, param_id)] = param_name
                    
        except Exception as e:
            print(f"⚠️  Новый парсер: не удалось загрузить PROTOCOL.json: {e}")
            self.protocol = None
            self.param_map = {}
    
    def parse_timecode_new(self, data):
        """Парсит таймкод согласно BlueMagic32 (кадры:секунды:минуты:часы)"""
        if len(data) < 12:
            return "Invalid length"
        
        # pData[8] = кадры, pData[9] = секунды, pData[10] = минуты, pData[11] = часы
        f = (data[8] >> 4) * 10 + (data[8] & 0x0F) if len(data) > 8 else 0
        S = (data[9] >> 4) * 10 + (data[9] & 0x0F) if len(data) > 9 else 0
        M = (data[10] >> 4) * 10 + (data[10] & 0x0F) if len(data) > 10 else 0
        H = (data[11] >> 4) * 10 + (data[11] & 0x0F) if len(data) > 11 else 0
        
        return f"{H:02d}:{M:02d}:{S:02d}:{f:02d}"
    
    def parse_parameter_new(self, data):
        """Парсит параметры согласно BlueMagic32"""
        if len(data) < 8 or data[0] != 0xFF:
            return {"type": "raw", "value": f"RAW: {data.hex()}"}
        
        group = data[4]  # category
        param = data[5]  # subcategory
        param_name = self.param_map.get((group, param), f"Unknown ({group}:{param})")
        
        # Таймкод (09:04)
        if group == 0x09 and param == 0x04:
            return {
                "type": "timecode",
                "value": self.parse_timecode_new(data),
                "group": group,
                "param": param,
                "name": "Timecode"
            }
        
        # Recording format (01:09) - содержит FPS!
        elif group == 0x01 and param == 0x09:
            result = {"type": "parameter", "name": param_name, "group": group, "param": param}
            
            if len(data) >= 18:
                frameRate = data[8] + (data[9] << 8)
                sensorRate = data[10] + (data[11] << 8)
                width = data[12] + (data[13] << 8)
                height = data[14] + (data[15] << 8)
                flags = data[16] if len(data) > 16 else 0
                
                result["value"] = f"{width}x{height} @ {frameRate}fps"
                result["details"] = f"sensor: {sensorRate}fps, flags: 0x{flags:02X}"
            elif len(data) >= 10:
                frameRate = data[8] + (data[9] << 8)
                result["value"] = f"{frameRate} fps"
            else:
                result["value"] = f"RAW: {data[6:].hex()}"
            
            return result
        
        # ISO (01:0E)
        elif group == 0x01 and param == 0x0E and len(data) >= 12:
            iso_value = data[8] + (data[9] << 8)
            return {
                "type": "parameter",
                "name": param_name,
                "value": f"ISO {iso_value}",
                "group": group,
                "param": param
            }
        
        # Shutter (01:0B или 01:0C)
        elif group == 0x01 and param in [0x0B, 0x0C] and len(data) >= 12:
            shutter_raw = data[8] + (data[9] << 8)
            if param == 0x0B:  # Shutter angle
                value = f"{shutter_raw/100.0}°"
            else:  # Shutter speed
                value = f"1/{shutter_raw}"
            
            return {
                "type": "parameter",
                "name": param_name,
                "value": value,
                "group": group,
                "param": param
            }
        
        # Апертура (00:02 или 0C:0A)
        elif (group == 0x00 and param == 0x02) or (group == 0x0C and param == 0x0A):
            if len(data) >= 10:
                fixed_val = data[8] + (data[9] << 8)
                if fixed_val > 0:
                    aperture = math.sqrt(2 ** (fixed_val / 2048.0))
                    value = f"f/{aperture:.1f}"
                else:
                    value = "N/A"
            else:
                value = f"RAW: {data[6:].hex()}"
            
            return {
                "type": "parameter",
                "name": param_name,
                "value": value,
                "group": group,
                "param": param
            }
        
        # Статус записи (0A:01)
        elif group == 0x0A and param == 0x01 and len(data) >= 12:
            status_byte = data[8] if len(data) > 8 else 0
            status = "Запись 🔴" if status_byte == 0x02 else "Стоп ⚪"
            return {
                "type": "parameter",
                "name": "Recording Status",
                "value": status,
                "group": group,
                "param": param
            }
        
        # Общий случай
        return {
            "type": "parameter",
            "name": param_name,
            "value": f"0x{data[6:].hex()}",
            "group": group,
            "param": param
        }
    
    def parse_new(self, data):
        """Основная функция нового парсера"""
        try:
            # Таймкод
            if len(data) >= 12 and data[0] == 0xFF and data[4] == 0x09 and data[5] == 0x04:
                return self.parse_parameter_new(data)
            # Параметры
            elif len(data) >= 8 and data[0] == 0xFF:
                return self.parse_parameter_new(data)
            else:
                return {"type": "raw", "value": f"RAW: {data.hex()}"}
        except Exception as e:
            return {"type": "error", "value": f"Ошибка: {e}"}

# ================= СРАВНИТЕЛЬНЫЙ МОНИТОР =================
class LiveDebugMonitor:
    def __init__(self):
        self.old_parser = parse_old
        self.new_parser = NewProtocolParser()
        self.message_count = 0
        self.differences_count = 0
        
        # Статистика
        self.stats = {
            'total': 0,
            'timecode': 0,
            'parameters': 0,
            'differences': 0,
            'by_category': {}
        }
    
    def format_hex(self, data):
        """Форматирует HEX для вывода"""
        hex_str = data.hex().upper()
        if len(hex_str) > 40:
            return hex_str[:40] + "..."
        return hex_str
    
    def compare_parsers(self, data):
        """Сравнивает два парсера и возвращает результат"""
        self.message_count += 1
        hex_str = self.format_hex(data)
        
        # Парсим старым способом
        try:
            old_result = self.old_parser(data)
            old_type = old_result.get('type', 'unknown')
            old_value = old_result.get('value_human', old_result.get('data', 'N/A'))
        except Exception as e:
            old_result = {"error": str(e)}
            old_type = "error"
            old_value = f"Ошибка: {e}"
        
        # Парсим новым способом
        new_result = self.new_parser.parse_new(data)
        new_type = new_result.get('type', 'unknown')
        new_value = new_result.get('value', 'N/A')
        
        # Определяем категорию для статистики
        if new_type == 'timecode':
            category = 'timecode'
        elif new_type == 'parameter':
            group = new_result.get('group', 0)
            category = f"{group:02X}"
        else:
            category = 'other'
        
        # Собираем статистику
        self.stats['total'] += 1
        self.stats['by_category'][category] = self.stats['by_category'].get(category, 0) + 1
        
        if category == 'timecode':
            self.stats['timecode'] += 1
        elif category not in ['other', 'raw', 'error']:
            self.stats['parameters'] += 1
        
        # Проверяем на различия
        is_different = False
        if old_type != new_type:
            is_different = True
        elif old_value != new_value and 'RAW' not in str(old_value) and 'RAW' not in str(new_value):
            is_different = True
        
        if is_different:
            self.differences_count += 1
            self.stats['differences'] += 1
        
        # Формируем результат
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        result = {
            'timestamp': timestamp,
            'hex': hex_str,
            'old': {'type': old_type, 'value': old_value},
            'new': {'type': new_type, 'value': new_value},
            'different': is_different,
            'category': category
        }
        
        return result
    
    def print_result(self, result):
        """Красиво выводит результат сравнения"""
        color_start = "\033[91m" if result['different'] else ""  # Красный если различаются
        color_end = "\033[0m" if result['different'] else ""
        
        print(f"\n{color_start}[{result['timestamp']}] Сообщение #{self.message_count}{color_end}")
        print(f"HEX: {result['hex']}")
        print(f"📟 СТАРЫЙ: [{result['old']['type']}] {result['old']['value']}")
        print(f"🚀 НОВЫЙ:  [{result['new']['type']}] {result['new']['value']}")
        
        if result['different']:
            print(f"⚠️  ⚠️  ⚠️   РАЗЛИЧИЕ ОБНАРУЖЕНО! ⚠️  ⚠️  ⚠️")
        
        # Показываем статистику каждые 20 сообщений
        if self.message_count % 20 == 0:
            self.print_stats()
    
    def print_stats(self):
        """Печатает статистику"""
        print(f"\n{'='*60}")
        print(f"📊 СТАТИСТИКА (сообщений: {self.message_count})")
        print(f"{'='*60}")
        print(f"Таймкодов: {self.stats['timecode']}")
        print(f"Параметров: {self.stats['parameters']}")
        print(f"Различий: {self.stats['differences']} ({self.stats['differences']/max(self.message_count,1)*100:.1f}%)")
        
        # Категории
        if self.stats['by_category']:
            print(f"\nПо категориям:")
            for cat, count in sorted(self.stats['by_category'].items()):
                cat_name = {
                    'timecode': 'Таймкод',
                    '01': 'Видео',
                    '0C': 'Объектив',
                    '0A': 'Команды',
                    '09': 'Телеметрия',
                    '00': 'Экспозиция'
                }.get(cat, f"Кат.{cat}")
                print(f"  {cat_name}: {count}")
        
        print(f"{'='*60}")

# ================= ОСНОВНАЯ ФУНКЦИЯ =================
async def main():
    monitor = LiveDebugMonitor()
    
    print("="*80)
    print("🎬 LIVE DEBUG MONITOR - Сравнение парсеров в реальном времени")
    print("="*80)
    print(f"Камера: {CAMERA_ADDRESS}")
    print(f"Старт: {datetime.now().strftime('%H:%M:%S')}")
    print("="*80)
    print("ЦВЕТА:")
    print("  \033[91mКрасный\033[0m - обнаружены различия между парсерами")
    print("  Нормальный - парсеры совпадают")
    print("="*80)
    print("\nЖдём данные от камеры...")
    print("Меняйте настройки на камере для генерации сообщений")
    print("="*80 + "\n")
    
    def handle_notification(sender, data):
        """Обработчик уведомлений от камеры"""
        result = monitor.compare_parsers(data)
        monitor.print_result(result)
    
    try:
        async with BleakClient(
            CAMERA_ADDRESS, 
            timeout=20.0,
            pair_before_connect=False
        ) as client:
            print("✅ Подключено к камере!")
            
            # Упрощенный подход: подписываемся напрямую по UUID
            print("🔍 Подписываюсь на характеристики...")
            
            # Преобразуем UUID в формат без дефисов для Bleak
            incoming_uuid = UUID_INCOMING_CAMERA_CONTROL.replace("-", "").lower()
            timecode_uuid = UUID_TIMECODE.replace("-", "").lower()
            status_uuid = UUID_CAMERA_STATUS.replace("-", "").lower()
            
            try:
                await client.start_notify(incoming_uuid, handle_notification)
                print(f"✅ Подписался на Incoming Camera Control")
            except Exception as e:
                print(f"⚠️  Не удалось подписаться на Incoming: {e}")
            
            try:
                await client.start_notify(timecode_uuid, handle_notification)
                print(f"✅ Подписался на Timecode")
            except Exception as e:
                print(f"⚠️  Не удалось подписаться на Timecode: {e}")
            
            try:
                await client.start_notify(status_uuid, handle_notification)
                print(f"✅ Подписался на Camera Status")
            except Exception as e:
                print(f"⚠️  Не удалось подписаться на Status: {e}")
            
            # Отправляем статус "готов"
            try:
                await client.write_gatt_char(status_uuid, b'\x20')
                print("📤 Отправлен статус 'Camera Ready'")
            except Exception as e:
                print(f"⚠️  Не удалось отправить статус: {e}")
            
            print("\n📡 Начинаю получение данных...")
            print("   Меняйте настройки на камере")
            print("   Нажмите Ctrl+C для остановки\n")
            
            # Просто ждем
            try:
                await asyncio.sleep(3600)  # 1 час
            except asyncio.CancelledError:
                print("\n🛑 Остановлено")
                
    except Exception as e:
        print(f"\n❌ Ошибка подключения: {e}")
        import traceback
        traceback.print_exc()
    
    # Финальная статистика
    monitor.print_stats()
    print(f"\n🎬 Сессия завершена. Всего сообщений: {monitor.message_count}")
    print(f"   Различий обнаружено: {monitor.differences_count}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Завершено")