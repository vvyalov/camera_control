#!/usr/bin/env python3
"""
🔬 BLACKMAGIC PROTOCOL INSPECTOR
Сравнивает старый парсер с новой логикой из BlueMagic32 и PROTOCOL.json
Запуск: python3 protocol_inspector.py <ваш_лог_файл.log>
"""

import sys
import json
import math
import os

# ------------------- НОВЫЙ ПАРСЕР (на основе BlueMagic32) -------------------
class BMDProtocolInspector:
    def __init__(self, protocol_json_path=None):
        # Определяем путь к PROTOCOL.json относительно этого файла
        if protocol_json_path is None:
            # Ищем в той же папке, где находится этот скрипт
            script_dir = os.path.dirname(os.path.abspath(__file__))
            protocol_json_path = os.path.join(script_dir, "PROTOCOL.json")
        
        # Загружаем справочник параметров
        try:
            with open(protocol_json_path, 'r', encoding='utf-8') as f:
                self.protocol = json.load(f)
            print(f"✅ Загружен PROTOCOL.json из {protocol_json_path}")
        except FileNotFoundError:
            print(f"❌ Файл не найден: {protocol_json_path}")
            print(f"   Текущая рабочая директория: {os.getcwd()}")
            print(f"   Ищем в: {protocol_json_path}")
            self.protocol = None
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка JSON в файле {protocol_json_path}: {e}")
            self.protocol = None
        except Exception as e:
            print(f"❌ Ошибка загрузки {protocol_json_path}: {e}")
            self.protocol = None
        
        # Карта для быстрого поиска (group_id, param_id) -> имя параметра
        self.param_map = self._build_param_map()
    
    def _build_param_map(self):
        """Создает словарь для поиска параметров по ID"""
        if not self.protocol:
            return {}
        param_map = {}
        for group in self.protocol.get('groups', []):
            group_id = group.get('id')
            for param in group.get('parameters', []):
                param_id = param.get('id')
                param_name = param.get('parameter', 'Unknown')
                param_map[(group_id, param_id)] = param_name
        return param_map
    
    def _parse_timecode_new(self, data):
        """Парсит таймкод согласно BlueMagic32 (кадры:секунды:минуты:часы)"""
        if len(data) < 12:  # Проверяем длину полного пакета
            return "Invalid length"
        
        # В BlueMagic32: байты 8-11 содержат BCD-таймкод
        # pData[8] = кадры, pData[9] = секунды, pData[10] = минуты, pData[11] = часы
        f = (data[8] >> 4) * 10 + (data[8] & 0x0F) if len(data) > 8 else 0
        S = (data[9] >> 4) * 10 + (data[9] & 0x0F) if len(data) > 9 else 0
        M = (data[10] >> 4) * 10 + (data[10] & 0x0F) if len(data) > 10 else 0
        H = (data[11] >> 4) * 10 + (data[11] & 0x0F) if len(data) > 11 else 0
        
        return f"{H:02d}:{M:02d}:{S:02d}:{f:02d}"
    
    def _parse_parameter_new(self, data):
        """Парсит параметры камеры согласно логике controlNotify из BlueMagic32"""
        if len(data) < 8 or data[0] != 0xFF:
            return "Not a BMD packet"
        
        group = data[4]  # category
        param = data[5]  # subcategory
        
        # Узнаем имя параметра из справочника
        param_name = self.param_map.get((group, param), f"Unknown ({group}:{param})")
        
        # Логика из controlNotify для каждого известного параметра
        # Recording format (group=1, param=9) - содержит FPS!
        if group == 1 and param == 9 and len(data) >= 18:
            # Байты 8-9: frameRate (little-endian int16)
            frameRate = data[8] + (data[9] << 8)
            # Байты 10-11: sensorFrameRate (little-endian int16)
            sensorRate = data[10] + (data[11] << 8)
            return f"{param_name}: {frameRate} fps (sensor: {sensorRate} fps)"
        
        # ISO (group=1, param=14)
        elif group == 1 and param == 14 and len(data) >= 12:
            # Байты 8-9: ISO (little-endian int16)
            iso_value = data[8] + (data[9] << 8)
            return f"{param_name}: ISO {iso_value}"
        
        # Shutter (group=1, param=11)
        elif group == 1 and param == 11 and len(data) >= 12:
            # Байты 8-9: shutter value (little-endian int16)
            shutter_raw = data[8] + (data[9] << 8)
            # Это угол затвора, умноженный на 100
            shutter_angle = shutter_raw / 100.0
            return f"{param_name}: {shutter_angle}°"
        
        # Апертура (group=0, param=2) - fixed16 преобразование
        elif group == 0 and param == 2 and len(data) >= 10:
            # Байты 8-9: fixed16 значение (little-endian)
            fixed_val = data[8] + (data[9] << 8)
            # Преобразование fixed16 в f/stop (как в BlueMagic32)
            aperture = math.sqrt(2 ** (fixed_val / 2048.0))
            return f"{param_name}: f/{aperture:.1f}"
        
        # По умолчанию показываем сырые данные
        return f"{param_name}: RAW {data[6:].hex()}"
    
    def parse_packet_new(self, hex_str):
        """Основная функция нового парсера"""
        try:
            data = bytes.fromhex(hex_str)
            
            # Определяем тип пакета по длине и паттерну
            # Таймкод обычно начинается с FF 0B 00 00 09 04 ...
            if len(data) >= 12 and data[0] == 0xFF and data[4] == 0x09 and data[5] == 0x04:
                return {
                    'type': 'timecode',
                    'value': self._parse_timecode_new(data),
                    'method': 'BlueMagic32'
                }
            # Пакет с параметрами (настройки)
            elif len(data) >= 8 and data[0] == 0xFF:
                return {
                    'type': 'parameter',
                    'value': self._parse_parameter_new(data),
                    'method': 'BlueMagic32'
                }
            else:
                return {
                    'type': 'unknown',
                    'value': f"RAW: {hex_str}",
                    'method': 'raw'
                }
                
        except Exception as e:
            return {
                'type': 'error',
                'value': f"Ошибка: {e}",
                'method': 'error'
            }

# ------------------- СРАВНЕНИЕ С ТВОИМ СТАРЫМ ПАРСЕРОМ -------------------
def run_comparison(log_file_path):
    """Сравнивает старый и новый парсер на лог-файле"""
    inspector = BMDProtocolInspector()
    
    print("=" * 80)
    print("🔬 BLACKMAGIC PROTOCOL INSPECTOR")
    print("=" * 80)
    
    # Проверяем, загрузился ли PROTOCOL.json
    if inspector.protocol is None:
        print("❌ НЕ СМОГ ЗАГРУЗИТЬ PROTOCOL.json!")
        print("   Убедись, что файл PROTOCOL.json находится в той же папке, что и этот скрипт.")
        print(f"   Или укажи полный путь: python3 protocol_inspector.py --json /полный/путь/PROTOCOL.json")
        return
    
    # Здесь нужно добавить чтение твоего лог-файла
    # и вызов твоего старого парсера для сравнения
    
    # Пример вывода для теста:
    test_packets = [
        "FF0B00000904020129040000",  # Таймкод
        "FF0E0000010902001800250000000000",  # Recording format (должен содержать FPS)
    ]
    
    for hex_str in test_packets:
        print(f"\n📦 Пакет: {hex_str}")
        result_new = inspector.parse_packet_new(hex_str)
        print(f"   НОВЫЙ парсер ({result_new['method']}): {result_new['value']}")
        # Здесь будет вызов твоего старого парсера
        # print(f"   СТАРЫЙ парсер: {result_old}")
    
    print("\n" + "=" * 80)
    print("📊 Анализ завершен. Сравни выводы выше.")
    print("=" * 80)

if __name__ == "__main__":
    # Проверяем аргументы командной строки
    import argparse
    parser = argparse.ArgumentParser(description='Blackmagic Protocol Inspector')
    parser.add_argument('logfile', nargs='?', help='Путь к лог-файлу')
    parser.add_argument('--json', help='Путь к файлу PROTOCOL.json')
    args = parser.parse_args()
    
    if args.json:
        run_comparison(args.logfile)
    else:
        run_comparison(args.logfile)