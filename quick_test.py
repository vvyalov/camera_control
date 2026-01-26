#!/usr/bin/env python3
"""
Быстрый тест для сбора данных
"""

import asyncio
from datetime import datetime
from bleak import BleakClient

CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"
UUID_NOTIFICATIONS = "b864e140-76a0-416a-bf30-5876504537d9"

async def main():
    print("=" * 60)
    print("⚡ БЫСТРЫЙ ТЕСТ - 10 СЕКУНД")
    print("=" * 60)
    print("\nИзмените на камере:")
    print("1. Выдержку (например 1/60)")
    print("2. Диафрагму (например f/4.0)")
    print("=" * 60)
    
    messages = []
    
    def handle_notification(sender, data):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        hex_str = data.hex().upper()
        messages.append((timestamp, hex_str))
        
        # Показываем ВСЁ что приходит
        print(f"[{timestamp}] {hex_str[:40]}...")
    
    print("\n🔗 Подключаюсь...")
    
    try:
        async with BleakClient(
            CAMERA_ADDRESS, 
            timeout=10.0,
            pair_before_connect=False
        ) as client:
            
            print("✅ Подключено!")
            await client.start_notify(UUID_NOTIFICATIONS, handle_notification)
            
            # Собираем 10 секунд
            print("\n📡 Собираю данные 10 секунд...")
            for i in range(10, 0, -1):
                print(f"\r⏱️  Осталось: {i} сек", end="")
                await asyncio.sleep(1)
            
            print("\n\n📊 РЕЗУЛЬТАТЫ:")
            print(f"Получено сообщений: {len(messages)}")
            
            # Анализируем что получили
            shutter_count = 0
            aperture_count = 0
            
            for timestamp, hex_str in messages:
                # Простой анализ формата
                if hex_str.startswith("FF"):
                    if len(hex_str) >= 12:
                        # Смотрим категорию и подкатегорию
                        cat_sub = hex_str[8:12]  # Байты 4-5
                        if cat_sub == "0002":
                            shutter_count += 1
                            value = hex_str[12:20] if len(hex_str) >= 20 else "???"
                            print(f"  🕒 ВЫДЕРЖКА: {value} ({timestamp})")
                        elif cat_sub == "0003":
                            aperture_count += 1
                            value = hex_str[12:16] if len(hex_str) >= 16 else "???"
                            print(f"  🌅 ДИАФРАГМА: {value} ({timestamp})")
            
            print(f"\n🎯 ИТОГ:")
            print(f"  Сообщений выдержки: {shutter_count}")
            print(f"  Сообщений диафрагмы: {aperture_count}")
            
            if shutter_count == 0:
                print("\n⚠️  ВНИМАНИЕ: Не получено сообщений о выдержке!")
                print("   Возможные причины:")
                print("   1. Камера не отправляет выдержку при изменении")
                print("   2. Формат сообщений другой")
                print("   3. Проблема с подключением")
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
