import asyncio
from bleak import BleakClient

# Адрес вашей камеры
CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

async def test_all_characteristics():
    """Тестируем все характеристики камеры"""
    print(f"Тестирую камеру: {CAMERA_ADDRESS}")
    
    try:
        async with BleakClient(CAMERA_ADDRESS, timeout=10.0) as client:
            print("✅ Подключено")
            
            services = client.services
            print(f"\nНайдено служб: {len(services.services)}")
            
            # Проходим по всем службам и характеристикам
            for service in services.services.values():
                print(f"\n[Служба] {service.uuid}")
                
                for char in service.characteristics:
                    print(f"  [Характеристика] {char.uuid}")
                    
                    # Пробуем прочитать характеристику
                    try:
                        if "read" in char.properties:
                            value = await client.read_gatt_char(char.uuid)
                            if value:
                                print(f"    📖 Значение: {value.hex()}")
                                # Пробуем декодировать как текст
                                try:
                                    text = value.decode('utf-8', errors='ignore').strip()
                                    if text:
                                        print(f"    📝 Текст: '{text}'")
                                except:
                                    pass
                    except Exception as e:
                        print(f"    ❌ Не прочитано: {e}")
            
            print("\n" + "="*50)
            print("Тестирование завершено")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

# Запуск
print("=== ТЕСТ ВСЕХ ХАРАКТЕРИСТИК КАМЕРЫ ===")
asyncio.run(test_all_characteristics())