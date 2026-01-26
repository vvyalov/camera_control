#!/usr/bin/env python3
"""
Систематический сбор кодов выдержки и диафрагмы BMPCC
"""

import asyncio
import json
from datetime import datetime
from bleak import BleakClient, BleakError

# Предполагаем, что эти импорты у тебя уже работают
from protocol import parse_bmpcc_message
from protocol.constants import UUID_NOTIFICATIONS

CAMERA_ADDRESS = "E7D0FD32-5393-2B54-61EE-F21174E0D7B0"


async def main():
    print("═" * 70)
    print("🔍 СБОР КОДОВ ВЫДЕРЖКИ И ДИАФРАГМЫ (Blackmagic Pocket Cinema Camera)")
    print("═" * 70)

    print("\nИНСТРУКЦИЯ:")
    print("  1. Запустите скрипт")
    print("  2. Меняйте выдержку и диафрагму на камере")
    print("  3. Ждите 2–4 секунды после каждого изменения")
    print("  4. Для выхода → Ctrl+C")
    print("═" * 70)

    # Хранилища: код → информация
    shutter_map = {}
    aperture_map = {}

    # Для подавления дубликатов уведомлений
    last_raw_bytes = None

    def notification_handler(sender, data: bytearray):
        nonlocal last_raw_bytes
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if data == last_raw_bytes:
            return  # дубликат
        last_raw_bytes = data

        try:
            parsed = parse_bmpcc_message(data)
        except Exception as parse_err:
            print(f"[{ts}] Ошибка парсинга: {parse_err!r}  raw = {data.hex().upper()}")
            return

        parsed["timestamp"] = ts
        category = parsed.get("category_name", "").lower()
        value_human = parsed.get("value_human", "").strip()
        value_raw_str = parsed.get("value_raw", "")

        # ─── Выдержка ───────────────────────────────────────────────────────
        if "shutter" in category or "выдержка" in category or "1/" in value_human:
            code = None
            # Попытка 1: из строки value_raw (если она hex)
            if len(value_raw_str) >= 4:
                try:
                    code = int(value_raw_str[:4], 16)
                except ValueError:
                    pass

            # Попытка 2: из байтов (часто более надёжно)
            if code is None and len(data) >= 6:
                code = int.from_bytes(data[2:4], "big")

            if code is not None and code not in shutter_map:
                shutter_map[code] = {
                    "hex": f"0x{code:04X}",
                    "value": value_human,
                    "first_seen": ts,
                    "raw_hex": data.hex().upper(),
                }
                print(f"[{ts}] 📸 Выдержка → {value_human:>8}   код = 0x{code:04X}")

        # ─── Диафрагма ──────────────────────────────────────────────────────
        if "aperture" in category or "диафрагма" in category or "f/" in value_human:
            code = None
            if len(value_raw_str) >= 4:
                try:
                    code = int(value_raw_str[:4], 16)
                except ValueError:
                    pass

            if code is None and len(data) >= 5:
                code = int.from_bytes(data[1:3], "big")

            if code is not None and code not in aperture_map:
                aperture_map[code] = {
                    "hex": f"0x{code:04X}",
                    "value": value_human,
                    "first_seen": ts,
                    "raw_hex": data.hex().upper(),
                }
                print(f"[{ts}] ⚙️ Диафрагма → {value_human:>6}   код = 0x{code:04X}")

    print(f"\nПодключаемся → {CAMERA_ADDRESS}")

    try:
        async with BleakClient(CAMERA_ADDRESS, timeout=18.0) as client:
            print("✅ Подключение успешно")

            await client.start_notify(UUID_NOTIFICATIONS, notification_handler)
            print("\nОжидаю уведомлений... Меняйте настройки на камере\n")

            try:
                await asyncio.sleep(3600)  # долгое ожидание, прерывается Ctrl+C
            except KeyboardInterrupt:
                print("\n\nПрервано (Ctrl+C)")

            await client.stop_notify(UUID_NOTIFICATIONS)

    except BleakError as e:
        print(f"Ошибка BLE: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {type(e).__name__}: {e}")

    # ─── Результаты и сохранение ────────────────────────────────────────────
    print("\n" + "═" * 70)
    print("РЕЗУЛЬТАТЫ")
    print("═" * 70)

    def save_and_print(name, data_dict):
        if not data_dict:
            print(f"→ {name}: ничего не найдено")
            return

        # Сортировка по численному значению (где возможно)
        def sort_key(item):
            val = item[1]["value"]
            try:
                if "/" in val:
                    return float(val.split("/")[1])
                if "f/" in val:
                    return float(val[2:])
            except:
                return 999999

        sorted_items = sorted(data_dict.items(), key=sort_key)

        print(f"\n{name} — найдено {len(sorted_items)} значений:")
        for code, info in sorted_items:
            print(f"  {info['hex']:>8} → {info['value']:>10}  (первый раз: {info['first_seen']})")

        fname = f"{name.lower().replace(' ', '_')}_codes.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in sorted_items}, f, ensure_ascii=False, indent=2)
        print(f"  → сохранено в {fname}")

    save_and_print("Выдержка", shutter_map)
    save_and_print("Диафрагма", aperture_map)

    print("\nГотово!")


if __name__ == "__main__":
    asyncio.run(main())