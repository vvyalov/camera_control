#!/usr/bin/env python3
"""
Тест библиотеки protocol
"""

import sys
sys.path.append('.')

from protocol import parse_bmpcc_message, decode_shutter, decode_aperture, decode_iso

# Тестовые данные из логов
test_messages = [
    # Выдержка 1/50
    bytes.fromhex("FF08000000028002910D0000"),
    # Диафрагма f/1.8
    bytes.fromhex("FF060000000380022800"),
    # ISO 400
    bytes.fromhex("FF080000010E030290010000"),
    # Выдержка 1/100
    bytes.fromhex("FF08000000028002F2180000"),
    # Диафрагма f/2.8
    bytes.fromhex("FF06000000038002E101"),
    # ISO 800
    bytes.fromhex("FF080000010E030220030000"),
    # Выдержка 1/200
    bytes.fromhex("FF080000000280021A210000"),
    # Диафрагма f/4.2
    bytes.fromhex("FF060000000380022303"),
    # ISO 1600
    bytes.fromhex("FF080000010E030240060000"),
]

print("=" * 70)
print("🧪 ТЕСТ БИБЛИОТЕКИ PROTOCOL")
print("=" * 70)

for i, data in enumerate(test_messages, 1):
    print(f"\nТест {i}: {data.hex().upper()}")
    
    # Парсим сообщение
    parsed = parse_bmpcc_message(data)
    
    if parsed["type"] == "bmpcc_message":
        print(f"  Категория: {parsed['category_name']}")
        print(f"  Значение: {parsed['value_human']}")
    else:
        print(f"  Тип: {parsed['type']}")
        print(f"  Данные: {parsed['data']}")

print("\n" + "=" * 70)
print("Тест отдельных декодеров:")
print("=" * 70)

# Тест отдельных декодеров
print("\n1. Декодер выдержки:")
print(f"   910D0000 → {decode_shutter(bytes.fromhex('910D0000'))}")
print(f"   F2180000 → {decode_shutter(bytes.fromhex('F2180000'))}")
print(f"   1A210000 → {decode_shutter(bytes.fromhex('1A210000'))}")

print("\n2. Декодер диафрагмы:")
print(f"   2800 → {decode_aperture(bytes.fromhex('2800'))}")
print(f"   E101 → {decode_aperture(bytes.fromhex('E101'))}")
print(f"   2303 → {decode_aperture(bytes.fromhex('2303'))}")

print("\n3. Декодер ISO:")
print(f"   90010000 → {decode_iso(bytes.fromhex('90010000'))}")
print(f"   20030000 → {decode_iso(bytes.fromhex('20030000'))}")
print(f"   40060000 → {decode_iso(bytes.fromhex('40060000'))}")

print("\n" + "=" * 70)
print("✅ ТЕСТ ЗАВЕРШЁН")
print("=" * 70)
