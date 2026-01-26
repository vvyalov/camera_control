import asyncio
from bleak import BleakClient
import time

CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

async def check_real_connection():
    """Проверяем реальное подключение"""
    print("=== ПРОВЕРКА РЕАЛЬНОГО ПОДКЛЮЧЕНИЯ ===")
    
    try:
        # Создаём клиент
        client = BleakClient(CAMERA_ADDRESS, timeout=5.0)
        
        # Пробуем подключиться
        print("1. Пытаюсь подключиться...")
        connected = await client.connect()
        print(f"   Результат connect(): {connected}")
        
        # Проверяем статус
        print(f"2. client.is_connected: {client.is_connected}")
        
        if client.is_connected:
            print("3. Пробую прочитать что-нибудь...")
            try:
                # Читаем любую характеристику
                services = client.services
                print(f"   Найдено служб: {len(services.services)}")
                
                # Если есть службы, пытаемся прочитать первую характеристику
                if services.services:
                    first_service = list(services.services.values())[0]
                    if first_service.characteristics:
                        first_char = first_service.characteristics[0]
                        value = await client.read_gatt_char(first_char.uuid)
                        print(f"   Прочитано: {value.hex()}")
                    else:
                        print("   Нет характеристик")
                else:
                    print("   Нет служб")
                    
            except Exception as e:
                print(f"   ❌ Ошибка чтения: {e}")
        else:
            print("3. Нет реального подключения")
        
        # Отключаемся
        print("4. Отключаюсь...")
        await client.disconnect()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        
        # Определяем тип ошибки
        if "timeout" in str(e).lower():
            print("\n⚠️ Таймаут. Камера не отвечает.")
            print("Проверьте:")
            print("- Камера включена")
            print("- Bluetooth на камере: Settings → Connections → Bluetooth → ON")
            print("- Камера не в режиме сна")
        elif "not found" in str(e).lower():
            print("\n⚠️ Устройство не найдено.")
            print("Камера не в режиме Bluetooth-вещания")
        elif "pair" in str(e).lower():
            print("\n⚠️ Проблема с сопряжением.")
            print("На Mac: Системные настройки → Bluetooth")
            print("УДАЛИТЕ камеру из списка устройств")

# Запуск
asyncio.run(check_real_connection())