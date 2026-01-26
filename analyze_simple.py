#!/usr/bin/env python3
"""
Простой анализ логов - без импорта protocol
"""

import json
print("📊 АНАЛИЗ ЛОГОВ КАМЕРЫ")
print("=" * 60)

# Функция для определения типа сообщения
def detect_message_type(hex_str):
    """Определяет тип сообщения по hex строке"""
    if not hex_str:
        return "unknown"
    
    # Формат FF [LEN] 00 00
    if hex_str.startswith('FF') and len(hex_str) >= 8:
        try:
            # Длина данных (2-й байт в hex)
            data_len = int(hex_str[2:4], 16)
            
            # Категория (5-й байт после FF LEN 00 00)
            if len(hex_str) >= 10:
                category = int(hex_str[8:10], 16)
                
                # Подкатегория (6-й байт)
                if len(hex_str) >= 12:
                    subcategory = int(hex_str[10:12], 16)
                    
                    # Выдержка: 00 02
                    if category == 0x00 and subcategory == 0x02:
                        return "shutter"
                    # Диафрагма: 00 03
                    elif category == 0x00 and subcategory == 0x03:
                        return "aperture"
                    # ISO: 01 0E
                    elif category == 0x01 and subcategory == 0x0E:
                        return "iso"
                    # Команды: 0A 01
                    elif category == 0x0A and subcategory == 0x01:
                        return "recording"
            
            return f"other_0x{category:02X}"
        except:
            return "error"
    
    return "raw"

# Анализируем raw_messages.log
print("\n📁 АНАЛИЗ raw_messages.log:")
print("-" * 40)

try:
    with open('raw_messages.log', 'r') as f:
        lines = f.readlines()
    
    print(f"Всего строк в логе: {len(lines)}")
    
    # Статистика по типам
    type_counts = {}
    shutter_values = {}
    aperture_values = {}
    
    for line in lines[-50:]:  # Последние 50 сообщений
        parts = line.strip().split()
        if len(parts) >= 3:
            hex_str = parts[2]
            msg_type = detect_message_type(hex_str)
            
            type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
            
            # Извлекаем значение
            if msg_type == "shutter" and len(hex_str) >= 24:  # FF08... + 8 байт
                # Значение выдержки (байты 12-20 в hex)
                value_hex = hex_str[12:20]
                try:
                    # Little-endian конвертация
                    value = int.from_bytes(bytes.fromhex(value_hex), 'little')
                    shutter_values[value_hex] = shutter_values.get(value_hex, 0) + 1
                except:
                    pass
            
            elif msg_type == "aperture" and len(hex_str) >= 16:  # FF06... + 4 байта
                value_hex = hex_str[12:16]
                try:
                    value = int.from_bytes(bytes.fromhex(value_hex), 'little')
                    aperture_values[value_hex] = aperture_values.get(value_hex, 0) + 1
                except:
                    pass
    
    print("\n📈 СТАТИСТИКА ТИПОВ СООБЩЕНИЙ:")
    for msg_type, count in sorted(type_counts.items()):
        print(f"  {msg_type}: {count}")
    
    print("\n🎯 ЗНАЧЕНИЯ ВЫДЕРЖКИ (последние 50 сообщений):")
    for value_hex, count in shutter_values.items():
        print(f"  {value_hex}: {count} раз")
    
    print("\n🎯 ЗНАЧЕНИЯ ДИАФРАГМЫ (последние 50 сообщений):")
    for value_hex, count in aperture_values.items():
        print(f"  {value_hex}: {count} раз")
    
except FileNotFoundError:
    print("Файл raw_messages.log не найден")

print("\n" + "=" * 60)
