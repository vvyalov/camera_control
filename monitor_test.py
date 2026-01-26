#!/usr/bin/env python3
"""
ПРОСТОЙ МОНИТОР КАМЕРЫ BMPCC 6K
Без сложных фильтров
"""

import asyncio
from bleak import BleakClient
from protocol import parse_bmpcc_message
from protocol.constants import UUID_NOTIFICATIONS

CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

async def simple_monitor():
    print("=" * 70)
    print("🎥 ПРОСТОЙ МОНИТОР BMPCC 6K")
    print("=" * 70)
    print("\nПодключаюсь к камере...")
    
    last_display = {}
    
    def handle_notification(sender, data):
        try:
            parsed = parse_bmpcc_message(data)
            
            if parsed["type"] == "bmpcc_message":
                cat_name = parsed.get("category_name", "Неизвестно")
                value = parsed.get("value_human", "")
                
                if cat_name and value:
                    # Обновляем только если изменилось
                    if last_display.get(cat_name) != value:
                        last_display[cat_name] = value
                        
                        # Показываем только важные параметры
                        if any(x in cat_name for x in ["Диафрагма", "Выдержка", "ISO", "Запись", "Объектив"]):
                            print(f"📡 {cat_name}: {value}")
        except Exception as e:
            print(f"⚠️  Ошибка обработки: {e}")
    
    try:
        async with BleakClient(CAMERA_ADDRESS, timeout=20.0) as client:
            print("✅ Подключено!")
            print("\n⏳ Жду данные с камеры...")
            print("Меняйте настройки и наблюдайте за выводом")
            print("Ctrl+C для выхода\n")
            
            await client.start_notify(UUID_NOTIFICATIONS, handle_notification)
            
            # Просто ждем
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n👋 Остановлено")
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(simple_monitor())