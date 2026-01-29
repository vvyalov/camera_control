# camera_control/protocols/ble/connector.py
import asyncio
from bleak import BleakClient
import sys

class BLECameraConnector:
    """Класс для подключения к BLE камере Blackmagic"""
    
    def __init__(self, camera_address: str = None):
        self.camera_address = camera_address
        self.client = None
        self.is_connected = False
        
    async def connect(self, camera_address: str = None) -> bool:
        """Подключение к уже спаренной камере"""
        if camera_address:
            self.camera_address = camera_address
            
        if not self.camera_address:
            raise ValueError("Адрес камеры не указан")
        
        print(f"Подключение к камере: {self.camera_address}")
        
        try:
            self.client = BleakClient(self.camera_address, timeout=10.0)
            await self.client.connect()
            self.is_connected = True
            
            print("✅ BLE-соединение установлено")
            return True
            
        except asyncio.TimeoutError:
            print("❌ Таймаут: камера не отвечает")
            return False
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    async def disconnect(self):
        """Отключение от камеры"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            print("✅ Отключено от камеры")
    
    async def read_characteristic(self, uuid: str):
        """Чтение характеристики по UUID"""
        if not self.is_connected:
            raise ConnectionError("Не подключено к камере")
        
        try:
            value = await self.client.read_gatt_char(uuid)
            return value
        except Exception as e:
            print(f"❌ Ошибка чтения характеристики {uuid}: {e}")
            return None
    
    async def get_camera_info(self):
        """Получение информации о камере"""
        if not self.is_connected:
            return None
        
        info = {}
        
        try:
            # Производитель
            manufacturer = await self.read_characteristic("00002a29-0000-1000-8000-00805f9b34fb")
            if manufacturer:
                info['manufacturer'] = manufacturer.decode('utf-8', errors='ignore').strip()
            
            # Модель
            model = await self.read_characteristic("00002a24-0000-1000-8000-00805f9b34fb")
            if model:
                info['model'] = model.decode('utf-8', errors='ignore').strip()
                
        except Exception as e:
            print(f"⚠️ Не удалось прочитать информацию о камере: {e}")
        
        return info
    
    async def get_status(self):
        """Получение статуса камеры"""
        try:
            # Статусная характеристика (ваша UUID)
            status = await self.read_characteristic("7fe8691d-95dc-4fc5-8abd-ca74339b51b9")
            return status
        except Exception as e:
            print(f"⚠️ Не удалось прочитать статус: {e}")
            return None

# =========== Старая функция для совместимости ===========
async def connect_to_camera():
    """Функция для обратной совместимости (старый код)"""
    print("=== ПОДКЛЮЧЕНИЕ К КАМЕРЕ ===")
    
    # Читаем адрес камеры
    try:
        with open("selected_camera.txt", "r") as f:
            camera_address = f.read().strip()
    except FileNotFoundError:
        print("❌ Файл 'selected_camera.txt' не найден")
        print("Сначала запустите: python3 scanner.py")
        return
    
    connector = BLECameraConnector(camera_address)
    connected = await connector.connect()
    
    if connected:
        # Получаем информацию
        info = await connector.get_camera_info()
        if info:
            print("\n=== ИНФОРМАЦИЯ О КАМЕРЕ ===")
            for key, value in info.items():
                print(f"{key}: {value}")
        
        # Получаем статус
        status = await connector.get_status()
        if status:
            print(f"\nСтатус камеры: {status.hex()}")
        
        print("\n" + "="*50)
        print("✅ КАМЕРА ПОДКЛЮЧЕНА И ГОТОВА К УПРАВЛЕНИЮ")
        
        # Держим соединение
        print("\n⏱️ Соединение активно 5 секунд...")
        for i in range(5, 0, -1):
            print(f"{i}...", end=" ", flush=True)
            await asyncio.sleep(1)
        
        await connector.disconnect()
        print("\n\n✅ Отключаюсь")

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(connect_to_camera())