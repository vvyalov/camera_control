#!/usr/bin/env python3
"""
ИСПРАВЛЕННЫЙ ТЕСТ С ПРАВИЛЬНЫМ ПАРСИНГОМ LITTLE-ENDIAN
"""

import asyncio
import json
from datetime import datetime
from bleak import BleakClient
from protocol import parse_bmpcc_message
from protocol.constants import UUID_NOTIFICATIONS

CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

def parse_little_endian_4byte(hex_str):
    """Парсит 4 байта little-endian"""
    if len(hex_str) < 8:
        return None
    # Берем первые 8 символов (4 байта)
    bytes_hex = hex_str[:8]
    # Конвертируем с учётом little-endian
    return int.from_bytes(bytes.fromhex(bytes_hex), 'little')

def parse_little_endian_2byte(hex_str):
    """Парсит 2 байта little-endian"""
    if len(hex_str) < 4:
        return None
    bytes_hex = hex_str[:4]
    return int.from_bytes(bytes.fromhex(bytes_hex), 'little')

async def main():
    print("=" * 70)
    print("🔍 ИСПРАВЛЕННЫЙ ТЕСТ (LITTLE-ENDIAN)")
    print("=" * 70)
    
    shutter_data = {}
    aperture_data = {}
    
    def handle_notification(sender, data):
        timestamp = datetime.now().strftime("%H:%M:%S")
        parsed = parse_bmpcc_message(data)
        
        if parsed["type"] == "bmpcc_message":
            raw_hex = parsed.get("value_raw", "")
            human_val = parsed.get("value_human", "")
            
            # Выдержка (4 байта)
            if "Выдержка" in parsed.get("category_name", "") and raw_hex:
                code = parse_little_endian_4byte(raw_hex)
                if code and code not in shutter_data:
                    shutter_data[code] = {
                        "hex_code": f"0x{code:04X}",
                        "raw_hex": raw_hex,
                        "human_value": human_val,
                        "timestamp": timestamp
                    }
                    print(f"[{timestamp}] 📝 ВЫДЕРЖКА: 0x{code:04X} ({raw_hex[:8]}) → {human_val}")
            
            # Диафрагма (2 байта)
            elif "Диафрагма" in parsed.get("category_name", "") and raw_hex:
                code = parse_little_endian_2byte(raw_hex)
                if code and code not in aperture_data:
                    aperture_data[code] = {
                        "hex_code": f"0x{code:04X}",
                        "raw_hex": raw_hex[:4],
                        "human_value": human_val,
                        "timestamp": timestamp
                    }
                    print(f"[{timestamp}] 📝 ДИАФРАГМА: 0x{code:04X} ({raw_hex[:4]}) → {human_val}")
    
    print("\n🔗 Подключаюсь к камере...")
    
    try:
        async with BleakClient(
            CAMERA_ADDRESS, 
            timeout=15.0,
            pair_before_connect=False
        ) as client:
            
            print("✅ Подключено!")
            await client.start_notify(UUID_NOTIFICATIONS, handle_notification)
            
            print("\n" + "=" * 70)
            print("🎬 УСТАНОВИТЕ НА КАМЕРЕ:")
            print("1. Выдержка: 1/30")
            print("2. Диафрагма: f/5.6 (или что показывает камера)")
            print("3. Подождите 3 секунды")
            print("4. Запишите коды")
            print("=" * 70)
            
            await asyncio.sleep(10)
            
            print("\n📊 ПРЕДВАРИТЕЛЬНЫЕ РЕЗУЛЬТАТЫ:")
            print(f"   Выдержка: {len(shutter_data)} кодов")
            print(f"   Диафрагма: {len(aperture_data)} кодов")
            
            if shutter_data:
                print("\n📈 КОДЫ ВЫДЕРЖКИ:")
                for code, info in sorted(shutter_data.items()):
                    print(f"   0x{code:04X} → {info['human_value']}")
            
            if aperture_data:
                print("\n📈 КОДЫ ДИАФРАГМЫ:")
                for code, info in sorted(aperture_data.items()):
                    print(f"   0x{code:04X} → {info['human_value']}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())