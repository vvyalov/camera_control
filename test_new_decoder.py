#!/usr/bin/env python3
"""
Тест обновлённого декодера статуса записи
"""

import sys
sys.path.append('.')

from protocol import decode_recording_status, parse_bmpcc_message

print("🧪 Тест декодера статуса записи:")
print("=" * 50)

# Тест 1: Декодер напрямую
test_data = [
    (bytes.fromhex("000040000103"), "Остановлена"),
    (bytes.fromhex("020040000103"), "Запись 🔴"),
    (bytes.fromhex("010040000103"), "Неизвестный статус (0x01)"),
]

print("\n1. Тест decode_recording_status():")
for data, expected in test_data:
    result = decode_recording_status(data)
    status = "✅" if result == expected else "❌"
    print(f"   {status} {data.hex()} → {result}")

# Тест 2: Через parse_bmpcc_message
print("\n2. Тест через parse_bmpcc_message():")
test_messages = [
    bytes.fromhex("FF0A00000A010102000040000103"),  # Остановлена
    bytes.fromhex("FF0A00000A010102020040000103"),  # Запись
]

for msg in test_messages:
    parsed = parse_bmpcc_message(msg)
    print(f"\n   Сообщение: {msg.hex()[:30]}...")
    print(f"   Категория: {parsed['category_name']}")
    print(f"   Статус: {parsed['value_human']}")

print("\n" + "=" * 50)
print("✅ Тест завершён!")
