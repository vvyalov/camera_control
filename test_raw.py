import asyncio
from bleak import BleakClient
import sys
import logging

# Отключаем логи
logging.getLogger('bleak').setLevel(logging.CRITICAL)

async def test_password_flow():
    """Тест: подключение → пароль → обработка"""
    with open("selected_camera.txt", "r") as f:
        address = f.read().strip()
    
    print(f"=== ТЕСТ ОБРАБОТКИ ПАРОЛЯ ===")
    print(f"Камера: {address}")
    
    # 1. Подключаемся (системное окно закрываем)
    client = BleakClient(address, timeout=10.0, services=None)
    
    try:
        print("\n1. Подключаюсь...")
        await client.connect()
        print("   ✅ Подключено")
        
        # 2. Ждём, пока камера покажет пароль
        print("\n2. Жду пароль от камеры...")
        print("   Смотрите на экран камеры!")
        
        for i in range(10, 0, -1):
            print(f"   {i}...", end=" " if i % 5 != 0 else "\n")
            await asyncio.sleep(1)
        
        # 3. Спрашиваем у пользователя
        print("\n3. Камера показала пароль?")
        print("   Если да — введите 6 цифр")
        print("   Если нет — нажмите Enter")
        
        password = input("\nПароль с камеры (или Enter если нет): ").strip()
        
        if password and len(password) == 6 and password.isdigit():
            print(f"\n4. Получен пароль: {password}")
            print("   Теперь можем его отправить в камеру...")
            
            # Здесь будет код отправки пароля
            print("   [Отправка пароля будет в следующем шаге]")
            
            return True
        else:
            print("\n⚠️ Пароль не получен")
            print("Возможно:")
            print("- Камера не показала пароль")
            print("- Уже спарена с Mac")
            print("- В другом режиме")
            return False
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        await client.disconnect()

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    success = asyncio.run(test_password_flow())
    
    if success:
        print("\n✅ ТЕСТ УСПЕШЕН!")
        print("Камера показала пароль, мы его получили")
        print("Следующий шаг — отправка пароля в камеру")
    else:
        print("\n❌ Тест не удался")