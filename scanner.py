import asyncio
import sys
from bleak import BleakScanner, BleakClient

# ================= УРОВНИ СКАНИРОВАНИЯ =================

async def scan_level_1_uuid():
    """Уровень 1: Мгновенный по UUID FFC0"""
    print("\n[УРОВЕНЬ 1] ⚡ МГНОВЕННЫЙ (по UUID)")
    print("Сканирую 3 секунды...")
    
    blackmagic_service_uuid = "0000ffc0-0000-1000-8000-00805f9b34fb"
    
    try:
        devices = await BleakScanner.discover(
            timeout=3.0,
            service_uuids=[blackmagic_service_uuid]
        )
    except:
        devices = []
    
    cameras = []
    for device in devices:
        name = device.name or "Blackmagic Camera"
        cameras.append((name, device.address))
        print(f"✅ {name}")
    
    return cameras

async def scan_level_2_parallel():
    """Уровень 2: Быстрый параллельный"""
    print("\n[УРОВЕНЬ 2] 🚀 БЫСТРЫЙ (параллельный)")
    print("Сканирую 4 секунды...")
    
    # 1. Сначала сканируем все устройства
    devices = await BleakScanner.discover(timeout=4.0)
    
    if not devices:
        return []
    
    print(f"Найдено устройств: {len(devices)}")
    print("Параллельная проверка...")
    
    # 2. Функция проверки одного устройства
    async def check_device(device):
        name = device.name or "Устройство"
        
        # Быстрый фильтр по имени
        if any(non_cam in name.lower() for non_cam in ["iphone", "samsung", "tv", "headphones"]):
            return None
        
        try:
            async with BleakClient(device.address, timeout=1.5) as client:
                await client.connect()
                
                # Только проверяем Manufacturer
                services = client.services
                for service in services.services.values():
                    for char in service.characteristics:
                        if "2a29" in char.uuid.lower():
                            try:
                                value = await client.read_gatt_char(char.uuid)
                                manufacturer = value.decode('utf-8', errors='ignore').strip()
                                
                                if "blackmagic" in manufacturer.lower():
                                    return (name, device.address, manufacturer)
                            except:
                                pass
                
                await client.disconnect()
        except:
            pass
        
        return None
    
    # 3. Запускаем ВСЕ проверки параллельно
    tasks = [check_device(device) for device in devices]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 4. Собираем результаты
    cameras = []
    for result in results:
        if result is not None and not isinstance(result, Exception):
            name, address, manufacturer = result
            cameras.append((name, address))
            print(f"✅ {name}")
    
    return cameras

async def scan_level_3_sequential():
    """Уровень 3: Точный последовательный"""
    print("\n[УРОВЕНЬ 3] 🐢 ТОЧНЫЙ (последовательный)")
    print("Сканирую 5 секунд...")
    
    devices = await BleakScanner.discover(timeout=5.0)
    
    if not devices:
        return []
    
    print(f"Найдено устройств: {len(devices)}")
    print("Последовательная проверка...")
    
    cameras = []
    
    for i, device in enumerate(devices, 1):
        name = device.name or f"Устройство {i}"
        
        # Пропуск по имени
        if any(non_cam in name.lower() for non_cam in ["iphone", "samsung", "tv"]):
            continue
        
        print(f"  Проверяю {i}/{len(devices)}: {name[:20]}...", end="\r")
        
        try:
            async with BleakClient(device.address, timeout=2.0) as client:
                await client.connect()
                
                # Проверяем Manufacturer
                services = client.services
                found = False
                
                for service in services.services.values():
                    for char in service.characteristics:
                        if "2a29" in char.uuid.lower():
                            try:
                                value = await client.read_gatt_char(char.uuid)
                                manufacturer = value.decode('utf-8', errors='ignore').strip()
                                
                                if "blackmagic" in manufacturer.lower():
                                    cameras.append((name, device.address))
                                    print(f"  ✅ {name}")
                                    found = True
                                    break
                            except:
                                pass
                    
                    if found:
                        break
                
                await client.disconnect()
                
        except:
            continue
    
    print(" " * 50, end="\r")  # Очистка строки
    return cameras

# ================= МЕНЮ И ВЫБОР =================

async def progressive_scan():
    """Прогрессивное сканирование с меню"""
    print("=== BLACKMAGIC PROGRESSIVE SCANNER ===")
    
    current_level = 1
    cameras = []
    
    while current_level <= 3:
        # Выполняем сканирование текущего уровня
        if current_level == 1:
            cameras = await scan_level_1_uuid()
        elif current_level == 2:
            cameras = await scan_level_2_parallel()
        else:
            cameras = await scan_level_3_sequential()
        
        # Результаты текущего уровня
        if cameras:
            print(f"\n🎯 Уровень {current_level}: найдено {len(cameras)} камер")
            return cameras
        
        # Если камер не найдено
        print(f"\n❌ Уровень {current_level}: камеры не найдены")
        
        if current_level < 3:
            print(f"\nВыберите действие:")
            print(f"1. Перейти на уровень {current_level + 1} ({(current_level+1)*5} сек)")
            print(f"2. Выход")
            
            try:
                choice = input("\nВаш выбор (1/2): ").strip()
                if choice == "2":
                    print("Выход из сканирования")
                    return []
                elif choice == "1":
                    current_level += 1
                    continue
                else:
                    print("Неверный выбор, продолжаю...")
                    current_level += 1
            except:
                print("Ошибка ввода, продолжаю...")
                current_level += 1
        else:
            # Уровень 3 завершён, камер нет
            print("\nВсе уровни проверены, камеры не найдены")
            return []
    
    return cameras

def select_camera(cameras):
    """Выбор камеры из списка"""
    if not cameras:
        return None
    
    print(f"\n📋 НАЙДЕНО КАМЕР: {len(cameras)}")
    
    for i, (name, address) in enumerate(cameras, 1):
        print(f"{i}. {name}")
        print(f"   {address}")
    
    if len(cameras) == 1:
        print("\n🎯 Автовыбор единственной камеры")
        return cameras[0]
    
    while True:
        try:
            choice = int(input(f"\nВыберите камеру (1-{len(cameras)}): "))
            if 1 <= choice <= len(cameras):
                return cameras[choice-1]
            print("❌ Неверный номер")
        except ValueError:
            print("❌ Введите число")
        except KeyboardInterrupt:
            print("\nОтменено")
            return None

async def main():
    """Основная функция"""
    cameras = await progressive_scan()
    
    if not cameras:
        print("\n❌ Сканирование завершено, камеры не найдены")
        return
    
    # Выбор камеры
    selected = select_camera(cameras)
    if not selected:
        return
    
    name, address = selected
    
    # Сохраняем выбранную камеру
    with open("selected_camera.txt", "w") as f:
        f.write(address)
    
    print(f"\n✅ ВЫБРАНА КАМЕРА: {name}")
    print(f"📁 Адрес сохранён в 'selected_camera.txt'")
    print("\nДля подключения запустите:")
    print("python3 connect.py")

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(main())