import asyncio
from bleak import BleakClient

async def control_camera():
    """Управление подключенной камерой"""
    try:
        with open("selected_camera.txt", "r") as f:
            camera_address = f.read().strip()
    except:
        print("❌ Сначала выберите камеру: python3 scanner.py")
        return
    
    print(f"=== УПРАВЛЕНИЕ КАМЕРОЙ ===")
    print("Будет реализовано в следующем шаге...")
    print(f"Адрес камеры: {camera_address}")

if __name__ == "__main__":
    asyncio.run(control_camera())