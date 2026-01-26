import asyncio
from bleak import BleakScanner
from bleak import BleakClient

async def find_blackmagic_cameras():
    """Находит ВСЕ камеры Blackmagic поблизости"""
    print("=== ПОИСК КАМЕР BLACKMAGIC ===")
    print("Сканирую 10 секунд...")
    
    # Сканируем все устройства
    devices = await BleakScanner.discover(timeout=10.0)
    
    cameras = []  # Список найденных камер
    
    print(f"\nНайдено устройств: {len(devices)}")
    print("-" * 50)
    
    for i, device in enumerate(devices, 1):
        device_address = device.address
        device_name = device.name or "Без имени"
        
        print(f"{i:2d}. {device_name[:20]:20} ({device_address})")
    
    print("\n" + "="*50)
    print("Проверяю, какие из них Blackmagic...")
    print("(Это займёт время)")
    
    # Проверяем каждый девайс на Blackmagic
    for i, device in enumerate(devices, 1):
        device_address = device.address
        device_name = device.name or f"Устройство {i}"
        
        # Пропускаем очевидно не камеры
        if not device_name and "iphone" in device_name.lower():
            continue
            
        try:
            # Быстрая проверка подключением
            async with BleakClient(device_address, timeout=3.0) as client:
                await client.connect()
                
                # Ищем службу Device Information
                services = client.services
                found_blackmagic = False
                manufacturer = ""
                
                for service in services.services.values():
                    for char in service.characteristics:
                        # Manufacturer Name Characteristic (0x2A29)
                        if "2a29" in char.uuid.lower():
                            try:
                                value = await client.read_gatt_char(char.uuid)
                                manufacturer = value.decode('utf-8', errors='ignore').strip()
                                
                                if "blackmagic" in manufacturer.lower():
                                    found_blackmagic = True
                                    print(f"✅ {device_name} - {manufacturer}")
                                    cameras.append((device_address, device_name, manufacturer))
                            except:
                                pass
                
                await client.disconnect()
                
                if not found_blackmagic:
                    print(f"  ✗ {device_name} - не Blackmagic")
                    
        except Exception as e:
            # Не удалось подключиться - пропускаем
            print(f"  ! {device_name} - не отвечает")
            continue
    
    # Результаты
    print("\n" + "="*50)
    print("ИТОГ:")
    
    if not cameras:
        print("❌ Камеры Blackmagic не найдены")
        print("\nВозможные причины:")
        print("1. Камеры выключены")
        print("2. Bluetooth на камерах не активирован")
        print("3. Камеры находятся далеко")
        return []
    
    print(f"✅ Найдено камер Blackmagic: {len(cameras)}")
    for i, (address, name, manufacturer) in enumerate(cameras, 1):
        print(f"\n{i}. {name}")
        print(f"   Адрес: {address}")
        print(f"   Производитель: {manufacturer}")
    
    print("\n" + "="*50)
    print("Для подключения скопируйте адрес нужной камеры:")
    for address, name, _ in cameras:
        print(f"  '{address}'  # {name}")
    
    return cameras

# Запуск
if __name__ == "__main__":
    found_cameras = asyncio.run(find_blackmagic_cameras())