# compare_monitors.py
import asyncio
import sys
import os
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from bleak import BleakClient
from protocols.bm import parse_bmpcc_message
from protocols.bm.constants import UUID_NOTIFICATIONS, UUID_TELEMETRY

CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

async def main():
    print("🔍 СРАВНЕНИЕ МОНИТОРОВ")
    print("Запускаю ОБА обработчика одновременно...")
    
    try:
        async with BleakClient(CAMERA_ADDRESS, timeout=10.0) as client:
            print("✅ Подключено!")
            
            counts = {'simple': 0, 'unified': 0}
            
            # ПРОСТОЙ обработчик (как debug_all_data.py)
            def simple_handler(sender, data):
                counts['simple'] += 1
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"\r[{timestamp}] Простой: {counts['simple']}", end="")
            
            # Unified monitor обработчик
            from monitors.unified_monitor import DebugMonitor
            monitor = DebugMonitor()
            
            def unified_handler(sender, data):
                counts['unified'] += 1
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"\r[{timestamp}] Unified: {counts['unified']}", end="")
                try:
                    parsed = parse_bmpcc_message(data)
                    monitor.process_message(parsed, data)
                except:
                    pass
            
            # Подписываемся
            await client.start_notify(UUID_NOTIFICATIONS, simple_handler)
            await client.start_notify(UUID_TELEMETRY, simple_handler)
            
            print("\n📡 Слушаю 10 секунд...")
            await asyncio.sleep(10)
            
            print(f"\n\n📊 РЕЗУЛЬТАТЫ:")
            print(f"  Простой обработчик: {counts['simple']} сообщений")
            print(f"  Unified обработчик: {counts['unified']} сообщений")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())