#!/usr/bin/env python3
"""
Blackmagic Camera Monitor - Пример использования
Работает и как скрипт, и как модуль
"""

#!/usr/bin/env python3
import sys
from pathlib import Path
root_dir = str(Path(__file__).parent.parent.parent.parent)
sys.path.insert(0, root_dir)

import asyncio
from typing import Any, Optional
from bleak import BleakClient, BleakScanner

# Импортируем КЛАСС из __init__.py
from monitors.bm_monitor import BlackmagicMonitor

# Импортируем КОНСТАНТЫ напрямую из файла!
from monitors.bm_monitor.constants import (  # type: ignorepy
    
    BMD_CAMERA_SERVICE_UUID,
    CHAR_CAMERA_STATUS_UUID,
    CHAR_TIMECODE_UUID,
    CHAR_INCOMING_CONTROL_UUID
)

# ... остальной код без изменений



class BlackmagicBLEClient:
    """Bleak реализация для Blackmagic камеры"""
    
    def __init__(self, address: Optional[str] = None):
        self.address = address
        self.client: Optional[BleakClient] = None
        self.monitor = BlackmagicMonitor()
        
        # Подписываемся на изменения состояния
        self.monitor.register_state_callback(self.on_state_change)
    
    def on_state_change(self, section: str, param: str, value: Any):
        """Вызывается при любом изменении камеры"""
        if section == 'timecode':
            print(f"\r⏱️  Таймкод: {value}", end='', flush=True)
        elif section == 'parameter' and param == 'TransportMode':
            status = "🔴 REC" if self.monitor.is_recording else "⏹️ STOP"
            print(f"\n{status}")
        elif section == 'parameter' and param == 'ISO':
            print(f"\n📷 ISO: {value}")
        elif section == 'parameter' and param == 'WhiteBalance':
            print(f"\n⚪ WB: {value}K")
        elif section == 'parameter' and param == 'ShutterAngle':
            angle = value / 100
            print(f"\n🎬 Shutter: {angle}°")
    
    def notification_handler(self, characteristic, data: bytes):
        """Обработчик BLE нотификаций"""
        uuid = characteristic.uuid.lower()
        self.monitor.process_notification(uuid, data)
    
    async def connect(self):
        """Подключение к камере"""
        if not self.address:
            print("🔍 Сканирование Blackmagic камер...")
            devices = await BleakScanner.discover()
            for dev in devices:
                if dev.name and ("Pocket Cinema" in dev.name or "Blackmagic" in dev.name):
                    self.address = dev.address
                    print(f"✅ Найдена камера: {dev.name} [{dev.address}]")
                    break
        
        if not self.address:
            print("❌ Камера не найдена")
            return False
        
        print(f"🔗 Подключение к {self.address}...")
        self.client = BleakClient(self.address)
        await self.client.connect()
        print(f"✅ Подключено: {self.client.is_connected}")
        
        try:
            # Чтение информации об устройстве
            manufacturer = await self.client.read_gatt_char("00002a29-0000-1000-8000-00805f9b34fb")
            model = await self.client.read_gatt_char("00002a24-0000-1000-8000-00805f9b34fb")
            
            manufacturer_str = manufacturer.decode('utf-8').strip('\x00')
            model_str = model.decode('utf-8').strip('\x00')
            
            self.monitor.process_device_info(manufacturer_str, model_str)
            print(f"📷 Камера: {manufacturer_str} {model_str}")
            
            # Подписка на нотификации
            await self.client.start_notify(CHAR_CAMERA_STATUS_UUID, self.notification_handler)
            await self.client.start_notify(CHAR_TIMECODE_UUID, self.notification_handler)
            await self.client.start_notify(CHAR_INCOMING_CONTROL_UUID, self.notification_handler)
            
            print("\n📡 Мониторинг запущен. Ждем данные...")
            print("   Нажмите Ctrl+C для выхода\n")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    async def run(self):
        """Запуск мониторинга"""
        if await self.connect():
            try:
                # Держим соединение
                while True:
                    await asyncio.sleep(1)
                    # Раз в секунду показываем сводку
                    summary = self.monitor.state.get_summary()
                    print(f"\r🎬 {summary.get('status', '?')} | "
                          f"⏱️ {self.monitor.current_timecode} | "
                          f"ISO{self.monitor.state.video.iso} | "
                          f"{self.monitor.state.video.white_balance}K | "
                          f"{summary.get('resolution', '?')}", end='', flush=True)
            except KeyboardInterrupt:
                print("\n\n👋 Завершение работы...")
            finally:
                await self.client.disconnect()
        else:
            print("❌ Не удалось подключиться")


async def main():
    client = BlackmagicBLEClient()
    await client.run()


if __name__ == "__main__":
    asyncio.run(main())