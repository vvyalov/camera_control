#!/usr/bin/env python3
"""
ОТЛАДОЧНЫЙ МОНИТОР - показывает ВСЕ сырые данные
"""

import asyncio
import sys
from datetime import datetime
from bleak import BleakClient
from protocol.constants import UUID_NOTIFICATIONS

CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

async def main():
    print("=" * 70)
    print("🐛 ОТЛАДОЧНЫЙ МОНИТОР - СЫРЫЕ ДАННЫЕ")
    print("=" * 70)
    print("\nИНСТРУКЦИЯ:")
    print("1. Измените ВЫДЕРЖКУ на камере")
    print("2. Посмотрите какие сообщения пришли")
    print("3. Измените ДИАФРАГМУ")
    print("4. Снова посмотрите сообщения")
    print("=" * 70)
    
    message_log = []
    
    def handle_notification(sender, data):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        hex_str = data.hex().upper()
        
        # Сохраняем сообщение
        entry = {
            "time": timestamp,
            "hex": hex_str,
            "length": len(data),
            "first_bytes": hex_str[:20]
        }
        message_log.append(entry)
        
        # Выводим ВСЁ
        print(f"\n[{timestamp}] 📨 ДЛИНА: {len(data)} байт")
        print(f"   HEX: {hex_str}")
        
        # Пытаемся понять что это
        if len(data) >= 4 and data[0] == 0xFF:
            length = data[1]
            print(f"   📊 Формат FF: длина данных = {length}")
            
            if len(data) >= 4 + length:
                payload = data[4:4+length]
                if len(payload) >= 4:
                    cat = payload[0]
                    sub = payload[1]
                    typ = payload[2]
                    subtyp = payload[3]
                    print(f"   🎯 Категория: 0x{cat:02X}, Подкатегория: 0x{sub:02X}")
                    
                    # Определяем тип
                    if cat == 0x00:
                        print(f"   📷 ЭКСПОЗИЦИЯ")
                        if sub == 0x02:
                            print(f"   ⏱️  ВЫДЕРЖКА")
                            if len(payload) >= 8:
                                value = int.from_bytes(payload[4:8], 'little')
                                print(f"   🔢 Значение: {value} (0x{value:04X})")
                        elif sub == 0x03:
                            print(f"   🌅 ДИАФРАГМА")
                            if len(payload) >= 6:
                                value = int.from_bytes(payload[4:6], 'little')
                                print(f"   🔢 Значение: {value} (0x{value:04X})")
    
    print("\n🔗 Подключаюсь к камере...")
    
    try:
        async with BleakClient(
            CAMERA_ADDRESS, 
            timeout=10.0,
            pair_before_connect=False
        ) as client:
            
            print("✅ Подключено!")
            await client.start_notify(UUID_NOTIFICATIONS, handle_notification)
            
            print("\n" + "=" * 70)
            print("🎬 ИЗМЕНЯЙТЕ НАСТРОЙКИ НА КАМЕРЕ И СМОТРИТЕ СООБЩЕНИЯ")
            print("=" * 70)
            print("\nДля остановки нажмите Ctrl+C")
            
            try:
                while True:
                    await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                print("\n\n⏹️ Остановлено")
            
            print(f"\n📊 Всего сообщений: {len(message_log)}")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())