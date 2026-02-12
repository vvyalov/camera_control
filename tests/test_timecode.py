"""
FINAL FPS Monitor - работает с правильным каналом
"""

import asyncio
import time
import sys
from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic

# ПРАВИЛЬНЫЕ UUID
UUID_TELEMETRY = "b864e140-76a0-416a-bf30-5876504537d9"    # НАСТРОЙКИ (FPS, выдержка, ISO)
UUID_NOTIFICATIONS = "6d8f2110-86f1-41bf-9afb-451d87e976c8"  # ТАЙМ-КОД

def parse_bmpcc_message(data: bytes):
    """Парсер сообщений Blackmagic"""
    if len(data) < 4 or data[0] != 0xFF:
        return None
    
    length = data[1]
    if len(data) != 4 + length:
        return None
    
    payload = data[4:]
    if len(payload) < 4:
        return None
    
    category = payload[0]
    subcategory = payload[1]
    value = payload[4:] if len(payload) > 4 else b''
    
    return {
        'category': f"{category:02X}:{subcategory:02X}",
        'category_hex': category,
        'subcategory_hex': subcategory,
        'value': value,
        'raw_hex': data.hex().upper(),
        'timestamp': time.strftime("%H:%M:%S")
    }

class FinalFPSMonitor:
    def __init__(self, camera_address):
        self.camera_address = camera_address
        self.client = None
        self.fps = "?"
        self.shutter = "?"
        self.iso = "?"
        self.aperture = "?"
        self.recording = "⚪"
        self.message_count = 0
        self.running = True
    
    async def handle_telemetry(self, sender: BleakGATTCharacteristic, data: bytes):
        """Обработчик TELEMETRY (настройки)"""
        self.message_count += 1
        parsed = parse_bmpcc_message(data)
        
        if not parsed:
            return
        
        cat = parsed['category']
        value = parsed['value']
        
        # FPS (01:09)
        if cat == "01:09" and len(value) >= 2:
            fps_val = int.from_bytes(value[0:2], 'little')
            self.fps = str(fps_val)
        
        # Выдержка (01:0C)
        elif cat == "01:0C" and len(value) >= 4:
            shutter_val = int.from_bytes(value[:4], 'little')
            self.shutter = f"1/{shutter_val}"
        
        # ISO (01:0E)
        elif cat == "01:0E" and len(value) >= 4:
            iso_val = int.from_bytes(value[:4], 'little')
            self.iso = f"ISO {iso_val}"
        
        # Диафрагма (00:03)
        elif cat == "00:03" and len(value) >= 2:
            # Упрощённая версия - покажем код
            aperture_code = int.from_bytes(value[:2], 'little')
            self.aperture = f"f/{aperture_code:04X}"
        
        # Статус записи (0A:01)
        elif cat == "0A:01" and len(value) >= 1:
            status = value[0]
            self.recording = "🔴" if status == 0x02 else "⚪"
        
        # Обновляем дисплей
        self.update_display()
    
    async def handle_timecode(self, sender: BleakGATTCharacteristic, data: bytes):
        """Обработчик тайм-кода (опционально)"""
        pass  # Пока не обрабатываем
    
    def update_display(self):
        """Обновляет отображение в консоли"""
        display = (
            f"\r🎬 FPS: {self.fps:>3} | "
            f"⏱️  1/{self.shutter.split('/')[-1]:>3} | "
            f"📷 {self.iso:>7} | "
            f"🔢 {self.aperture:>7} | "
            f"{self.recording} | "
            f"📡 #{self.message_count:04d}"
        )
        print(display, end="", flush=True)
    
    async def connect_and_monitor(self):
        """Основная функция"""
        print("=" * 60)
        print("🎬 BLACKMAGIC CAMERA MONITOR - РАБОЧАЯ ВЕРСИЯ")
        print("=" * 60)
        print(f"Камера: {self.camera_address}")
        print("=" * 60)
        
        try:
            self.client = BleakClient(self.camera_address)
            await self.client.connect()
            print("✅ Подключено!")
            
            # Подписываемся на TELEMETRY (настройки)
            print("📡 Подписка на настройки камеры...")
            await self.client.start_notify(UUID_TELEMETRY, self.handle_telemetry)
            print("✅ Телеметрия включена")
            
            # Опционально: подписка на тайм-код
            try:
                await self.client.start_notify(UUID_NOTIFICATIONS, self.handle_timecode)
                print("✅ Тайм-код включен")
            except:
                print("⚠️  Тайм-код не доступен")
            
            print("\n" + "=" * 60)
            print("Ожидание данных...")
            print("-" * 60)
            
            # Инициализируем дисплей
            self.update_display()
            
            # Главный цикл
            while self.running:
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Остановка...")
            self.running = False
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
        finally:
            if self.client and self.client.is_connected:
                print("\n🔌 Отключение...")
                await self.client.stop_notify(UUID_TELEMETRY)
                try:
                    await self.client.stop_notify(UUID_NOTIFICATIONS)
                except:
                    pass
                await self.client.disconnect()
            print("\n👋 Монитор остановлен")

async def main():
    """Основная функция"""
    # Читаем адрес
    try:
        with open("selected_camera.txt", "r") as f:
            camera_address = f.read().strip()
    except FileNotFoundError:
        print("❌ Файл selected_camera.txt не найден")
        print("Запустите сначала сканирование камер")
        return
    
    monitor = FinalFPSMonitor(camera_address)
    await monitor.connect_and_monitor()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Программа завершена")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)