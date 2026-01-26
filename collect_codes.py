#!/usr/bin/env python3
"""
СИСТЕМАТИЧЕСКИЙ СБОР ВСЕХ КОДОВ ВЫДЕРЖКИ И ДИАФРАГМЫ
"""

import asyncio
import json
from datetime import datetime
from bleak import BleakClient
from protocol import parse_bmpcc_message
from protocol.constants import UUID_NOTIFICATIONS, CATEGORY_EXPOSURE
from protocol.constants import SUBCAT_SHUTTER, SUBCAT_APERTURE

CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

# Таблица для сбора всех данных
ALL_CODES = {
    "shutter": {},  # код → значение
    "aperture": {}  # код → значение
}

async def collect_one_setting(setting_name, camera_value):
    """
    Собирает код для одного значения настройки
    """
    print(f"\n🔍 Собираем: {setting_name} = {camera_value}")
    print("Установите это значение на камере, затем нажмите Enter...")
    input("Готово? Нажмите Enter → ")
    
    collected_codes = {"shutter": set(), "aperture": set()}
    
    def handle_notification(sender, data):
        parsed = parse_bmpcc_message(data)
        if parsed["type"] == "bmpcc_message":
            category = parsed.get("category")
            subcategory = parsed.get("subcategory")
            raw_hex = parsed.get("value_raw", "")
            
            # Выдержка
            if category == CATEGORY_EXPOSURE and subcategory == SUBCAT_SHUTTER:
                if len(raw_hex) >= 8:
                    code = int.from_bytes(bytes.fromhex(raw_hex[:8]), 'little')
                    if code not in collected_codes["shutter"]:
                        collected_codes["shutter"].add(code)
                        if code not in ALL_CODES["shutter"]:
                            ALL_CODES["shutter"][code] = camera_value
                            print(f"   ✅ ВЫДЕРЖКА: 0x{code:04X} → {camera_value}")
            
            # Диафрагма
            elif category == CATEGORY_EXPOSURE and subcategory == SUBCAT_APERTURE:
                if len(raw_hex) >= 4:
                    code = int.from_bytes(bytes.fromhex(raw_hex[:4]), 'little')
                    if code not in collected_codes["aperture"]:
                        collected_codes["aperture"].add(code)
                        if code not in ALL_CODES["aperture"]:
                            ALL_CODES["aperture"][code] = camera_value
                            print(f"   ✅ ДИАФРАГМА: 0x{code:04X} → {camera_value}")
    
    try:
        async with BleakClient(
            CAMERA_ADDRESS, 
            timeout=8.0,
            pair_before_connect=False
        ) as client:
            
            await client.start_notify(UUID_NOTIFICATIONS, handle_notification)
            await asyncio.sleep(3)  # Собираем 3 секунды
            
    except Exception as e:
        print(f"   ⚠️ Ошибка: {e}")
    
    return len(collected_codes["shutter"]) > 0 or len(collected_codes["aperture"]) > 0

async def main():
    print("=" * 70)
    print("📋 СИСТЕМАТИЧЕСКИЙ СБОР ВСЕХ КОДОВ")
    print("=" * 70)
    
    # Список значений для сбора
    test_plan = [
        # (Название, Выдержка, Диафрагма)
        ("1/30 + f/5.6", "1/30", "f/5.6"),
        ("1/60 + f/8.0", "1/60", "f/8.0"),
        ("1/125 + f/11", "1/125", "f/11"),
        ("1/250 + f/16", "1/250", "f/16"),
        ("1/500 + f/22", "1/500", "f/22"),
        ("1/1000 + f/2.8", "1/1000", "f/2.8"),
    ]
    
    print("\n📝 ПЛАН СБОРА:")
    for i, (name, shutter, aperture) in enumerate(test_plan, 1):
        print(f"{i}. {name}: Выдержка={shutter}, Диафрагма={aperture}")
    
    print("\n" + "=" * 70)
    
    for name, shutter_val, aperture_val in test_plan:
        success = await collect_one_setting(name, f"{shutter_val}/{aperture_val}")
        if not success:
            print(f"   ⚠️ Не получены данные для {name}")
    
    # Сохраняем результаты
    print("\n" + "=" * 70)
    print("📊 ФИНАЛЬНЫЕ РЕЗУЛЬТАТЫ:")
    print("=" * 70)
    
    if ALL_CODES["shutter"]:
        print(f"\n🎯 ВЫДЕРЖКА (найдено {len(ALL_CODES['shutter'])} кодов):")
        for code, value in sorted(ALL_CODES["shutter"].items()):
            print(f"   0x{code:04X} → {value}")
        
        with open("FINAL_shutter_codes.json", "w") as f:
            json.dump(ALL_CODES["shutter"], f, indent=2, default=str)
    
    if ALL_CODES["aperture"]:
        print(f"\n🎯 ДИАФРАГМА (найдено {len(ALL_CODES['aperture'])} кодов):")
        for code, value in sorted(ALL_CODES["aperture"].items()):
            print(f"   0x{code:04X} → {value}")
        
        with open("FINAL_aperture_codes.json", "w") as f:
            json.dump(ALL_CODES["aperture"], f, indent=2, default=str)
    
    print("\n💾 Все коды сохранены в JSON файлах")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())