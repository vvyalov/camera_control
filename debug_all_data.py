#!/usr/bin/env python3
"""
Отладочный монитор - показывает ВСЕ данные
"""

import os
import sys
import asyncio
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from bleak import BleakClient
from protocols.bm import parse_bmpcc_message
from protocols.bm.constants import UUID_NOTIFICATIONS, UUID_TELEMETRY

CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

async def main():
    print("🔍 ОТЛАДОЧНЫЙ МОНИТОР - ВСЕ ДАННЫЕ")
    print(f"Камера: {CAMERA_ADDRESS}")
    
    try:
        async with BleakClient(CAMERA_ADDRESS, timeout=10.0) as client:
            print("✅ Подключено!")
            
            message_count = 0
            
            def handle_notification(sender, data):
                nonlocal message_count
                message_count += 1
                
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                hex_data = data.hex()
                
                print(f"\n[{timestamp}] #{message_count}: {len(data)} байт")
                print(f"   HEX: {hex_data}")
                
                try:
                    parsed = parse_bmpcc_message(data)
                    print(f"   Parsed: {parsed}")
                    
                    # Подробно для BMPCC сообщений
                    if parsed.get('type') == 'bmpcc_message':
                        cat = parsed.get('category')
                        subcat = parsed.get('subcategory')
                        print(f"   → Категория: 0x{cat:02X}, Подкатегория: 0x{subcat:02X}")
                        
                except Exception as e:
                    print(f"   ❌ Parse error: {e}")
            
            # Подписываемся
            await client.start_notify(UUID_NOTIFICATIONS, handle_notification)
            await client.start_notify(UUID_TELEMETRY, handle_notification)
            
            print(f"\n📡 Слушаю 30 секунд...")
            print("ИЗМЕНЯЙ НАСТРОЙКИ НА КАМЕРЕ!")
            print("-" * 60)
            
            for i in range(30, 0, -1):
                print(f"\r⏱️ {i:2d} сек | Сообщений: {message_count:3d}", end="")
                await asyncio.sleep(1)
            
            print(f"\n\n📊 ИТОГО: {message_count} сообщений")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
