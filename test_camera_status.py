#!/usr/bin/env python3
"""
ЧТЕНИЕ СТАТУСА КАМЕРЫ BLACKMAGIC В РЕАЛЬНОМ ВРЕМЕНИ
Читает все доступные данные и сохраняет в файл
"""

import asyncio
import sys
import json
import time
from datetime import datetime
from bleak import BleakClient
from pathlib import Path

# ================= КОНФИГУРАЦИЯ =================
CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"
STATUS_FILE = "camera_status.json"
LOG_FILE = "status_changes.log"
# ================================================

def create_status_snapshot():
    """Создаёт снимок статуса для сравнения"""
    return {
        "timestamp": datetime.now().isoformat(),
        "camera_address": CAMERA_ADDRESS,
        "characteristics": {}
    }

def bytes_to_readable(data):
    """Конвертирует байты в читаемые форматы"""
    if not data:
        return {"hex": "", "text": "", "raw": []}
    
    # Пробуем как текст
    text = ""
    try:
        text = data.decode('utf-8', errors='ignore').strip()
    except:
        pass
    
    # Пробуем как числа
    numbers = list(data)
    
    return {
        "hex": data.hex(),
        "text": text,
        "raw": numbers,
        "length": len(data)
    }

async def read_all_characteristics(client, snapshot):
    """Читает все характеристики камеры"""
    print("\n" + "="*70)
    print("📡 ЧТЕНИЕ ДАННЫХ С КАМЕРЫ")
    print("="*70)
    
    try:
        services = client.services
        print(f"📊 Найдено служб: {len(services.services)}")
        
        all_chars = []
        
        for service_idx, service in enumerate(services.services.values()):
            service_uuid = service.uuid
            
            for char_idx, char in enumerate(service.characteristics):
                char_uuid = char.uuid
                char_props = char.properties
                
                char_info = {
                    "service_uuid": service_uuid,
                    "char_uuid": char_uuid,
                    "properties": char_props,
                    "value": None,
                    "readable": None
                }
                
                # Сохраняем в снимок
                key = f"{service_uuid[-8:]}_{char_uuid[-8:]}"
                
                if "read" in char_props:
                    try:
                        value = await client.read_gatt_char(char_uuid)
                        readable = bytes_to_readable(value)
                        
                        char_info["value"] = value.hex() if value else ""
                        char_info["readable"] = readable
                        
                        snapshot["characteristics"][key] = {
                            "service": service_uuid,
                            "characteristic": char_uuid,
                            "properties": char_props,
                            "value_hex": value.hex() if value else "",
                            "value_text": readable["text"],
                            "value_raw": readable["raw"],
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Вывод в консоль
                        print(f"\n[{service_idx}.{char_idx}] {char_uuid[-12:]}")
                        print(f"   Свойства: {char_props}")
                        if value:
                            print(f"   HEX: {value.hex()}")
                            if readable['text']:
                                print(f"   Текст: '{readable['text']}'")
                            if readable['raw']:
                                print(f"   Числа: {readable['raw']}")
                        else:
                            print(f"   Значение: пусто")
                        
                    except Exception as e:
                        print(f"\n[{service_idx}.{char_idx}] {char_uuid[-12:]}")
                        print(f"   ❌ Не прочитано: {e}")
                        snapshot["characteristics"][key] = {
                            "error": str(e),
                            "timestamp": datetime.now().isoformat()
                        }
                else:
                    print(f"\n[{service_idx}.{char_idx}] {char_uuid[-12:]}")
                    print(f"   Свойства: {char_props} (только запись)")
                    snapshot["characteristics"][key] = {
                        "properties": char_props,
                        "note": "write_only",
                        "timestamp": datetime.now().isoformat()
                    }
                
                all_chars.append(char_info)
        
        return all_chars
        
    except Exception as e:
        print(f"❌ Ошибка при чтении: {e}")
        return []

def load_previous_status():
    """Загружает предыдущий статус для сравнения"""
    if Path(STATUS_FILE).exists():
        try:
            with open(STATUS_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def compare_statuses(prev, current):
    """Сравнивает два снимка статуса"""
    if not prev:
        print("\n🆕 Первый снимок статуса")
        return []
    
    changes = []
    
    prev_chars = prev.get("characteristics", {})
    curr_chars = current.get("characteristics", {})
    
    # Проверяем изменения в существующих характеристиках
    for key in set(prev_chars.keys()) & set(curr_chars.keys()):
        prev_val = prev_chars[key].get("value_hex", "")
        curr_val = curr_chars[key].get("value_hex", "")
        
        if prev_val != curr_val:
            changes.append({
                "characteristic": key,
                "from": prev_val,
                "to": curr_val,
                "timestamp": datetime.now().isoformat()
            })
    
    # Новые характеристики
    for key in set(curr_chars.keys()) - set(prev_chars.keys()):
        changes.append({
            "characteristic": key,
            "change": "new",
            "value": curr_chars[key].get("value_hex", ""),
            "timestamp": datetime.now().isoformat()
        })
    
    # Удалённые характеристики
    for key in set(prev_chars.keys()) - set(curr_chars.keys()):
        changes.append({
            "characteristic": key,
            "change": "removed",
            "timestamp": datetime.now().isoformat()
        })
    
    return changes

def log_changes(changes):
    """Логирует изменения в файл"""
    if not changes:
        return
    
    print("\n" + "="*70)
    print("🔄 ОБНАРУЖЕНЫ ИЗМЕНЕНИЯ:")
    print("="*70)
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "changes": changes
    }
    
    # Вывод в консоль
    for change in changes:
        if "from" in change:
            print(f"📝 {change['characteristic']}: {change['from']} → {change['to']}")
        elif change.get("change") == "new":
            print(f"🆕 {change['characteristic']}: новое значение {change['value']}")
        elif change.get("change") == "removed":
            print(f"🗑️  {change['characteristic']}: удалено")
    
    # Сохраняем в лог-файл
    try:
        log_data = []
        if Path(LOG_FILE).exists():
            with open(LOG_FILE, 'r') as f:
                log_data = json.load(f)
        
        log_data.append(log_entry)
        
        with open(LOG_FILE, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"\n📁 Изменения сохранены в {LOG_FILE}")
        
    except Exception as e:
        print(f"⚠️ Не удалось сохранить лог: {e}")

def save_status_snapshot(snapshot):
    """Сохраняет снимок статуса в файл"""
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Снимок статуса сохранён в {STATUS_FILE}")
    except Exception as e:
        print(f"❌ Не удалось сохранить статус: {e}")

async def main():
    """Основная функция"""
    print("="*70)
    print("📷 BLACKMAGIC CAMERA STATUS READER")
    print("="*70)
    print(f"Камера: {CAMERA_ADDRESS}")
    print(f"Время: {datetime.now().strftime('%H:%M:%S')}")
    print("="*70)
    
    # Загружаем предыдущий статус
    previous_status = load_previous_status()
    
    try:
        print("\n🔗 Подключаюсь к камере...")
        async with BleakClient(CAMERA_ADDRESS, timeout=10.0) as client:
            print("✅ Подключено!")
            
            # Создаём новый снимок
            current_snapshot = create_status_snapshot()
            
            # Читаем все данные
            await read_all_characteristics(client, current_snapshot)
            
            # Сохраняем снимок
            save_status_snapshot(current_snapshot)
            
            # Сравниваем с предыдущим
            if previous_status:
                changes = compare_statuses(previous_status, current_snapshot)
                log_changes(changes)
            
            print("\n" + "="*70)
            print("🎬 ЧТО ДЕЛАТЬ ДАЛЬШЕ:")
            print("="*70)
            print("1. Измените настройки на камере (ISO, запись, фокус и т.д.)")
            print("2. Запустите этот скрипт снова:")
            print("   python3 camera_status.py")
            print("3. Смотрите, какие значения изменились в разделе 'ОБНАРУЖЕНЫ ИЗМЕНЕНИЯ'")
            print("4. Повторяйте, пока не поймём, за что каждая характеристика отвечает")
            print("="*70)
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # Настройка вывода
    sys.stdout.reconfigure(line_buffering=True)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️ Остановлено пользователем")