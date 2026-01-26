#!/usr/bin/env python3
"""
Монитор с отключённым автошифрованием (для тестов)
"""

import asyncio
import sys
from datetime import datetime
from bleak import BleakClient
from pathlib import Path
import json

from protocol import parse_bmpcc_message
from protocol.constants import UUID_NOTIFICATIONS, UUID_TELEMETRY, UUID_STATUS

CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

async def main():
    print("=" * 70)
    print("📡 МОНИТОР БЕЗ АВТОШИФРОВАНИЯ")
    print("=" * 70)
    
    try:
        # Пробуем подключиться без автошифрования
        async with BleakClient(
            CAMERA_ADDRESS, 
            timeout=15.0,
            pair_before_connect=False  # Не пытаться спариваться автоматически
        ) as client:
            print("✅ Подключено (без автошифрования)!")
            
            # Остальной код как в test_monitor.py
            services = client.services
            
            print(f"\n📊 Найдено сервисов: {len(services.services)}")
            
            # Подписываемся на уведомления
            await client.start_notify(UUID_NOTIFICATIONS, 
                                     lambda s, d: print(f"📨 Получено: {d.hex()[:40]}..."))
            
            print("\n🎬 Слушаю сообщения... (10 секунд)")
            await asyncio.sleep(10)
            
            print("\n✅ Тест завершён")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(main())
