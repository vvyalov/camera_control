#!/usr/bin/env python3
"""
САМЫЙ ПРОСТОЙ ТЕСТ
"""

import subprocess
import time

print("Проверка Bluetooth через системные команды...")
print("-" * 50)

# Команда 1: Проверка включен ли Bluetooth
result = subprocess.run(["blueutil", "--power"], 
                       capture_output=True, text=True)
print(f"Bluetooth power: {result.stdout.strip()}")

# Команда 2: Список устройств через system_profiler
print("\nЗапускаем сканирование через system_profiler...")
result = subprocess.run(["system_profiler", "SPBluetoothDataType", "-detailLevel", "basic"], 
                       capture_output=True, text=True)

# Ищем устройства в выводе
output = result.stdout
devices_found = []

# Парсим вывод
lines = output.split('\n')
for line in lines:
    if "Address:" in line or "bluetooth" in line.lower():
        print(f"  {line}")

print("\n" + "=" * 50)
print("Если ничего не найдено, возможно:")
print("1. Bluetooth выключен в системных настройках")
print("2. Нет совместимых устройств рядом")
print("3. Нужно перезапустить Bluetooth службу:")
print("   sudo pkill bluetoothd")