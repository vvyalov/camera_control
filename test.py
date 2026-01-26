#!/usr/bin/env python3
"""
ТЕСТ ДЕКОДЕРА ДЛЯ BMPCC 6K
Запустите и меняйте настройки на камере
"""

import asyncio
import json
from datetime import datetime
from bleak import BleakClient
from protocol import parse_bmpcc_message
from protocol.constants import UUID_NOTIFICATIONS

CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

async def test_decoder():
    print("=" * 70)
    print("🧪 ТЕСТ ДЕКОДЕРА BMPCC 6K")
    print("=" * 70)
    print("\nИНСТРУКЦИЯ:")
    print("1. Установите на камере конкретные значения")
    print("2. Проверьте что отображается в консоли")
    print("3. Зафиксируйте несоответствия")
    print("=" * 70)
    
    test_results = {
        "aperture_tests": [],
        "shutter_tests": [],
        "iso_tests": [],
        "other_tests": []
    }
    
    def handle_notification(sender, data):
        parsed = parse_bmpcc_message(data)
        
        if parsed["type"] == "bmpcc_message":
            category = parsed.get("category", "")
            subcategory = parsed.get("subcategory", "")
            cat_name = parsed.get("category_name", "")
            value = parsed.get("value_human", "")
            raw_hex = parsed.get("value_raw", "")
            
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            
            print(f"[{timestamp}] {cat_name}: {value}")
            
            # Сохраняем для анализа
            if "f/" in value or "???" in value:
                test_results["aperture_tests"].append({
                    "time": timestamp,
                    "raw": raw_hex,
                    "displayed": value,
                    "full": data.hex()
                })
            elif "1/" in value:
                test_results["shutter_tests"].append({
                    "time": timestamp,
                    "raw": raw_hex,
                    "displayed": value,
                    "full": data.hex()
                })
            elif "ISO" in value:
                test_results["iso_tests"].append({
                    "time": timestamp,
                    "raw": raw_hex,
                    "displayed": value,
                    "full": data.hex()
                })
            else:
                test_results["other_tests"].append({
                    "time": timestamp,
                    "category": f"0x{category:02X}",
                    "subcategory": f"0x{subcategory:02X}",
                    "value": value,
                    "raw": raw_hex
                })
    
    print("\n🔗 Подключаюсь к камере...")
    
    try:
        async with BleakClient(CAMERA_ADDRESS, timeout=20.0) as client:
            print("✅ Подключено!")
            await client.start_notify(UUID_NOTIFICATIONS, handle_notification)
            
            print("\n" + "=" * 70)
            print("ТЕСТ НАЧАТ")
            print("=" * 70)
            
            print("\n🔍 Сейчас собираю данные...")
            print("Меняйте настройки на камере и наблюдайте за выводом")
            print("\nРекомендую проверить:")
            print("1. Диафрагма: f/1.8, f/2.8, f/4.0, f/5.6, f/8.0")
            print("2. Выдержка: 1/30, 1/60, 1/125, 1/250, 1/1000")
            print("3. ISO: 100, 400, 800, 1600")
            print("\nНажмите Ctrl+C для остановки")
            
            try:
                await asyncio.sleep(30)  # Собираем данные 30 секунд
            except KeyboardInterrupt:
                print("\n⏹️ Тест остановлен пользователем")
            
            # Сохраняем результаты
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"decoder_test_{timestamp}.json"
            
            with open(filename, "w") as f:
                json.dump(test_results, f, indent=2)
            
            print(f"\n💾 Результаты сохранены в {filename}")
            
            # Быстрый анализ
            print("\n📊 СТАТИСТИКА:")
            print(f"  Диафрагма: {len(test_results['aperture_tests'])} измерений")
            print(f"  Выдержка: {len(test_results['shutter_tests'])} измерений")
            print(f"  ISO: {len(test_results['iso_tests'])} измерений")
            print(f"  Другие: {len(test_results['other_tests'])} сообщений")
            
            if test_results["aperture_tests"]:
                print("\n📸 ПОСЛЕДНИЕ ИЗМЕРЕНИЯ ДИАФРАГМЫ:")
                for i, test in enumerate(test_results["aperture_tests"][-5:], 1):
                    print(f"  {i}. {test['raw']} → {test['displayed']}")
            
            if test_results["shutter_tests"]:
                print("\n🕒 ПОСЛЕДНИЕ ИЗМЕРЕНИЯ ВЫДЕРЖКИ:")
                for i, test in enumerate(test_results["shutter_tests"][-5:], 1):
                    print(f"  {i}. {test['raw']} → {test['displayed']}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(test_decoder())