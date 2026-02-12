#!/usr/bin/env python3
"""
🎬 SIMPLE DEBUG - минимальный монитор для отладки
"""

import asyncio
import sys
import os
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from bleak import BleakClient
from protocols.bm import parse_bmpcc_message, UUID_NOTIFICATIONS

CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

async def main():
    print("="*60)
    print("🎬 SIMPLE DEBUG MODE")
    print("="*60)
    
    # Счётчики сообщений по категориям
    counters = {}
    
    async with BleakClient(CAMERA_ADDRESS, timeout=15.0) as client:
        print(f"✅ Подключено к {CAMERA_ADDRESS}")
        
        def handle_data(sender, data):
            try:
                parsed = parse_bmpcc_message(data)
                
                if parsed.get('type') == 'bmpcc_message':
                    cat = parsed.get('category', 0)
                    sub = parsed.get('subcategory', 0)
                    key = f"{cat:02X}:{sub:02X}"
                    
                    counters[key] = counters.get(key, 0) + 1
                    
                    # Показываем ВСЕ сообщения в реальном времени
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    value = parsed.get('value_human', '???')
                    
                    print(f"[{timestamp}] {key}: {value}")
                    
                    # Если это FPS, диафрагма или кодек - выделяем
                    if key in ["01:09", "0C:0A", "10:00", "01:0B", "01:0C"]:
                        print(f"   ⭐ ВАЖНОЕ: {data.hex()[:40]}...")
                
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {parsed.get('type', 'raw')}: {data.hex()[:40]}...")
                    
            except Exception as e:
                print(f"[ERROR] {e}")
                print(f"[ERROR] Data: {data.hex()[:40]}...")
        
        # Подписываемся
        await client.start_notify(UUID_NOTIFICATIONS, handle_data)
        print("✅ Подписка активна")
        print("\n📡 Жду сообщения 15 секунд...")
        print("   Нажми Ctrl+C для остановки")
        print("="*60)
        
        try:
            await asyncio.sleep(15)
        except KeyboardInterrupt:
            print("\n⏹️ Остановлено")
        
        await client.stop_notify(UUID_NOTIFICATIONS)
    
    # Выводим статистику
    print("\n" + "="*60)
    print("📊 СТАТИСТИКА ПОЛУЧЕННЫХ СООБЩЕНИЙ:")
    print("="*60)
    
    for key in sorted(counters.keys()):
        count = counters[key]
        print(f"  {key}: {count}")
    
    print("="*60)
    
    # Проверяем критичные параметры
    critical = {
        "01:09": "FPS",
        "0C:0A": "Диафрагма", 
        "10:00": "Кодек",
        "01:0B": "Выдержка (угол)",
        "01:0C": "Выдержка (скорость)",
        "01:0E": "ISO",
        "09:02": "Оставшееся время"
    }
    
    print("\n🔍 КРИТИЧНЫЕ ПАРАМЕТРЫ:")
    for key, name in critical.items():
        count = counters.get(key, 0)
        status = "✅ ЕСТЬ" if count > 0 else "❌ НЕТ"
        print(f"  {name} ({key}): {status} ({count} сообщений)")
    
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())