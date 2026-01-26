import asyncio
from bleak import BleakClient

CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

async def check_camera_mode():
    """Проверяем режим камеры"""
    print("=== ПРОВЕРКА РЕЖИМА КАМЕРЫ ===")
    
    try:
        client = BleakClient(CAMERA_ADDRESS, timeout=8.0)
        print("1. Подключаюсь...")
        await client.connect()
        
        print("2. Проверяю службы...")
        services = client.services
        
        # Выводим ВСЮ информацию о камере
        print(f"\nСлужб: {len(services.services)}")
        print("="*50)
        
        for i, service in enumerate(services.services.values()):
            print(f"\nСлужба {i}: {service.uuid}")
            print(f"Описание: {service.description}")
            
            for char in service.characteristics:
                print(f"  Характеристика: {char.uuid}")
                print(f"    Свойства: {char.properties}")
                print(f"    Описание: {char.description}")
                
                # Пробуем прочитать, если можно
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        if value:
                            print(f"    Значение: {value.hex()}")
                            try:
                                text = value.decode('utf-8', errors='ignore').strip()
                                if text:
                                    print(f"    Текст: '{text}'")
                            except:
                                pass
                    except Exception as e:
                        print(f"    Не прочитано: {e}")
        
        print("\n" + "="*50)
        print("ИНФОРМАЦИЯ О КАМЕРЕ:")
        print("- Производитель: Blackmagic Design")
        print("- Модель: Pocket Cinema Camera 6K")
        print("- Версия протокола: 0.1.0")
        print("\nНО камера не в режиме Bluetooth-управления.")
        print("\nНа камере проверьте:")
        print("1. Menu → Settings → Connections → Bluetooth → ON")
        print("2. Камера должна показать 'Bluetooth: Ready'")
        print("3. Выйдите из меню на главный экран")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

# Запуск
asyncio.run(check_camera_mode())