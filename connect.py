import asyncio
from bleak import BleakClient
import sys

async def connect_to_camera():
    """Подключение к уже спаренной камере"""
    print("=== ПОДКЛЮЧЕНИЕ К КАМЕРЕ ===")
    
    # Читаем адрес камеры
    try:
        with open("selected_camera.txt", "r") as f:
            camera_address = f.read().strip()
    except FileNotFoundError:
        print("❌ Файл 'selected_camera.txt' не найден")
        print("Сначала запустите: python3 scanner.py")
        return
    
    print(f"Адрес камеры: {camera_address}")
    print("\nПредполагается, что камера уже спарена с Mac")
    print("(пароль был введён ранее через системный диалог macOS)")
    
    try:
        async with BleakClient(camera_address, timeout=10.0) as client:
            print("✅ BLE-соединение установлено")
            
            # Идентификация камеры
            print("\n=== ИНФОРМАЦИЯ О КАМЕРЕ ===")
            
            try:
                services = client.services
                
                # Читаем производителя и модель
                for service in services.services.values():
                    for char in service.characteristics:
                        if "2a29" in char.uuid.lower():  # Manufacturer
                            value = await client.read_gatt_char(char.uuid)
                            manufacturer = value.decode('utf-8', errors='ignore').strip()
                            print(f"Производитель: {manufacturer}")
                        
                        if "2a24" in char.uuid.lower():  # Model
                            value = await client.read_gatt_char(char.uuid)
                            model = value.decode('utf-8', errors='ignore').strip()
                            print(f"Модель: {model}")
            except Exception as e:
                print(f"⚠️ Не удалось прочитать детали: {e}")
            
            # Проверяем статус подключения
            print("\n=== СТАТУС ПОДКЛЮЧЕНИЯ ===")
            
            try:
                # Статусная характеристика
                status = await client.read_gatt_char("7fe8691d-95dc-4fc5-8abd-ca74339b51b9")
                print(f"Статус камеры: {status.hex()}")
                
                if status == b'\x01':
                    print("Состояние: Готов к работе")
                else:
                    print(f"Состояние: Неизвестно ({status.hex()})")
                    
            except Exception as e:
                print(f"⚠️ Не удалось прочитать статус: {e}")
            
            print("\n" + "="*50)
            print("✅ КАМЕРА ПОДКЛЮЧЕНА И ГОТОВА К УПРАВЛЕНИЮ")
            print("\nДля управления запустите:")
            print("python3 controller.py")
            
            # Держим соединение активным
            print("\n⏱️ Соединение активно 5 секунд...")
            for i in range(5, 0, -1):
                print(f"{i}...", end=" ", flush=True)
                await asyncio.sleep(1)
            
            print("\n\n✅ Отключаюсь")
            
    except asyncio.TimeoutError:
        print("❌ Таймаут: камера не отвечает")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(connect_to_camera())