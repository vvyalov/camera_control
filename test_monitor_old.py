#!/usr/bin/env python3
"""
ПЕРВЫЙ ТЕСТ: Мониторинг сырых сообщений от камеры Blackmagic
Подключается напрямую к камере, показывает сообщения + базовый парсинг
"""

import asyncio
import sys
from datetime import datetime
from bleak import BleakClient
from pathlib import Path
import json

# ================= КОНФИГУРАЦИЯ =================
# Адрес вашей камеры Pocket 6K
CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

# UUID из технического отчета
UUID_NOTIFICATIONS = "b864e140-76a0-416a-bf30-5876504537d9"  # Основной канал
UUID_TELEMETRY = "6d8f2110-86f1-41bf-9afb-451d87e976c8"      # Телеметрия
UUID_STATUS = "7fe8691d-95dc-4fc5-8abd-ca74339b51b9"         # Статус камеры

# Файлы для логов
RAW_LOG = "raw_messages.log"
PARSED_LOG = "parsed_messages.json"
# ================================================

class BMPCCParser:
    """Базовый парсер сообщений Blackmagic BMPCC"""
    
    # Категории из технического отчета
    CATEGORIES = {
        0x00: "EXPOSURE",
        0x01: "CAMERA_SETTINGS", 
        0x03: "SYSTEM",
        0x09: "TELEMETRY",
        0x0A: "COMMANDS",
        0x0C: "LENS"
    }
    
    # Известные параметры (категория:субкатегория -> название)
    KNOWN_PARAMS = {
        (0x00, 0x02): "SHUTTER_SPEED",    # Выдержка
        (0x00, 0x03): "APERTURE",         # Диафрагма
        (0x01, 0x0C): "ISO_LOW",          # ISO (альтернативный)
        (0x01, 0x0E): "ISO_HIGH",         # ISO (основной)
        (0x0C, 0x09): "LENS_NAME",        # Название объектива
        (0x0A, 0x01): "OPERATION_MODE",   # Режим работы
    }
    
    @staticmethod
    def parse_message(data: bytes) -> dict:
        """Парсит сообщение в формате Blackmagic"""
        
        # Если сообщение слишком короткое
        if len(data) < 4:
            return {"type": "raw", "data": data.hex()}
        
        # Проверяем формат FF [LEN] 00 00
        if data[0] == 0xFF and len(data) >= 4:
            length = data[1]
            
            # Проверяем длину
            if len(data) != 4 + length:
                return {"type": "invalid_length", "data": data.hex()}
            
            payload = data[4:]  # Полезные данные
            
            if len(payload) >= 4:
                category = payload[0]
                subcategory = payload[1]
                data_type = payload[2]
                subtype = payload[3]
                value = payload[4:] if len(payload) > 4 else b''
                
                # Определяем название категории
                category_name = BMPCCParser.CATEGORIES.get(category, f"UNKNOWN_0x{category:02X}")
                
                # Определяем название параметра
                param_key = (category, subcategory)
                param_name = BMPCCParser.KNOWN_PARAMS.get(param_key, f"PARAM_0x{subcategory:02X}")
                
                # Пытаемся декодировать значение
                human_value = BMPCCParser._decode_value(category, subcategory, value)
                
                return {
                    "type": "bmpcc_message",
                    "category": category,
                    "category_name": category_name,
                    "subcategory": subcategory,
                    "param_name": param_name,
                    "data_type": data_type,
                    "subtype": subtype,
                    "value_raw": value.hex(),
                    "value_human": human_value,
                    "full_hex": data.hex()
                }
        
        # Если не распознан формат FF
        return {"type": "raw", "data": data.hex()}
    
    @staticmethod
    def _decode_value(category: int, subcategory: int, value: bytes) -> str:
        """Пытается декодировать значение в читаемый вид"""
        
        if not value:
            return ""
        
        # ISO значения (4 байта, little-endian)
        if category == 0x01 and subcategory in [0x0C, 0x0E]:
            if len(value) >= 4:
                iso_value = int.from_bytes(value[:4], 'little')
                return f"ISO {iso_value}"
        
        # Текстовые данные (объектив и т.д.)
        if category == 0x0C and subcategory in [0x09, 0x0A, 0x0B, 0x0C, 0x0F]:
            try:
                text = value.decode('ascii', errors='ignore').strip()
                return text
            except:
                pass
        
        # Числовые значения (выдержка, диафрагма)
        if category == 0x00:
            if subcategory == 0x02 and len(value) >= 4:  # Выдержка
                shutter_value = int.from_bytes(value[:4], 'little')
                return f"1/{shutter_value}" if shutter_value > 0 else "Unknown"
            
            if subcategory == 0x03 and len(value) >= 2:  # Диафрагма
                aperture_raw = int.from_bytes(value[:2], 'little')
                # Пока не знаем точное преобразование
                return f"f/{aperture_raw}"
        
        # По умолчанию - hex
        return f"0x{value.hex()[:20]}..." if len(value.hex()) > 20 else f"0x{value.hex()}"

def log_raw_message(timestamp: str, data: bytes, source: str):
    """Сохраняет сырое сообщение в лог"""
    hex_str = data.hex().upper()
    log_line = f"{timestamp} [{source}] {hex_str}\n"
    
    with open(RAW_LOG, "a", encoding="utf-8") as f:
        f.write(log_line)

def log_parsed_message(timestamp: str, parsed: dict):
    """Сохраняет распарсенное сообщение в JSON"""
    log_entry = {
        "timestamp": timestamp,
        **parsed
    }
    
    # Загружаем существующие логи
    logs = []
    if Path(PARSED_LOG).exists():
        try:
            with open(PARSED_LOG, "r", encoding="utf-8") as f:
                # Читаем как JSON Lines
                for line in f:
                    if line.strip():
                        logs.append(json.loads(line))
        except:
            logs = []
    
    # Добавляем новую запись
    logs.append(log_entry)
    
    # Сохраняем (только последние 1000 записей)
    with open(PARSED_LOG, "w", encoding="utf-8") as f:
        for entry in logs[-1000:]:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

async def main():
    """Основная функция теста"""
    print("=" * 70)
    print("📡 ТЕСТОВЫЙ МОНИТОР BLACKMAGIC BMPCC")
    print("=" * 70)
    print(f"Камера: {CAMERA_ADDRESS}")
    print(f"Время начала: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Логи: {RAW_LOG}, {PARSED_LOG}")
    print("=" * 70)
    
    # Очищаем старые логи
    for log_file in [RAW_LOG, PARSED_LOG]:
        if Path(log_file).exists():
            Path(log_file).unlink()
    
    print("\n🔗 Подключаюсь к камере...")
    
    try:
        async with BleakClient(CAMERA_ADDRESS, timeout=10.0) as client:
            print("✅ Подключено!")
            
            # Получаем сервисы (новый способ)
            services = client.services
            found_channels = []
            
            for service in services.services.values():
                for char in service.characteristics:
                    char_uuid = char.uuid.lower()
                    if UUID_NOTIFICATIONS.lower() in char_uuid or \
                       UUID_TELEMETRY.lower() in char_uuid or \
                       UUID_STATUS.lower() in char_uuid:
                        found_channels.append((char.uuid[-8:], char.properties))
            
            print(f"\n📊 Найдено каналов: {len(found_channels)}")
            for uuid_short, props in found_channels:
                print(f"   {uuid_short}: {props}")
            
            # Подписываемся на основной канал уведомлений
            print(f"\n🔔 Подписываюсь на уведомления...")
            
            # Функция обработки уведомлений
            def handle_notification(sender: str, data: bytes, source: str = "MAIN"):
                """Обработчик уведомлений от камеры"""
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                hex_str = data.hex().upper()
                
                # 1. Сохраняем сырое сообщение
                log_raw_message(timestamp, data, source)
                
                # 2. Парсим сообщение
                parsed = BMPCCParser.parse_message(data)
                
                # 3. Сохраняем распарсенное
                log_parsed_message(timestamp, parsed)
                
                # 4. Выводим в консоль
                print(f"\n[{timestamp}] 📨 {source}: {hex_str[:60]}...")
                
                if parsed["type"] == "bmpcc_message":
                    print(f"   📊 {parsed['category_name']} → {parsed['param_name']}")
                    if parsed["value_human"]:
                        print(f"   🎯 Значение: {parsed['value_human']}")
                elif parsed["type"] == "invalid_length":
                    print(f"   ⚠️ Неверная длина сообщения")
                else:
                    print(f"   🔍 Сырые данные")
            
            # Подписываемся на уведомления
            await client.start_notify(UUID_NOTIFICATIONS, 
                                     lambda s, d: handle_notification(s, d, "MAIN"))
            
            # Пытаемся подписаться на телеметрию (если есть)
            try:
                # Ищем UUID телеметрии
                telemetry_found = False
                for service in services.services.values():
                    for char in service.characteristics:
                        if UUID_TELEMETRY.lower() in char.uuid.lower():
                            await client.start_notify(char.uuid,
                                                     lambda s, d: handle_notification(s, d, "TELEMETRY"))
                            telemetry_found = True
                            print("✅ Подписка на телеметрию")
                            break
                    if telemetry_found:
                        break
                
                if not telemetry_found:
                    print("⚠️ Канал телеметрии не найден")
            except Exception as e:
                print(f"⚠️ Телеметрия: {e}")
            
            # Читаем текущий статус камеры
            try:
                # Ищем UUID статуса
                status_found = False
                for service in services.services.values():
                    for char in service.characteristics:
                        if UUID_STATUS.lower() in char.uuid.lower():
                            status = await client.read_gatt_char(char.uuid)
                            print(f"\n📊 Текущий статус камеры: {status.hex()}")
                            if status == b'\x01':
                                print("   Состояние: Готов")
                            elif status == b'\x03':
                                print("   Состояние: Остановлена")
                            else:
                                print(f"   Состояние: Неизвестно (0x{status.hex()})")
                            status_found = True
                            break
                    if status_found:
                        break
                
                if not status_found:
                    print("⚠️ Канал статуса не найден")
            except Exception as e:
                print(f"⚠️ Не удалось прочитать статус: {e}")
            
            print("\n" + "=" * 70)
            print("🎬 МОНИТОРИНГ АКТИВЕН")
            print("=" * 70)
            print("Сделайте что-то на камере:")
            print("1. Начните/остановите запись")
            print("2. Измените ISO")
            print("3. Измените выдержку/диафрагму")
            print("4. Посмотрите сообщения в консоли")
            print("\nДля остановки нажмите Ctrl+C")
            print("=" * 70)
            
            # Мониторим 30 секунд
            try:
                for i in range(30, 0, -1):
                    print(f"\r⏱️ Осталось: {i:2d} сек | Сообщений получено...", end="", flush=True)
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n\n⏹️ Остановлено пользователем")
            
            # Отписываемся от уведомлений
            try:
                await client.stop_notify(UUID_NOTIFICATIONS)
                print("\n🔕 Отписался от уведомлений")
            except:
                pass
            
    except asyncio.TimeoutError:
        print("❌ Таймаут подключения")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Вывод статистики
    print("\n" + "=" * 70)
    print("📈 СТАТИСТИКА ТЕСТА")
    print("=" * 70)
    
    if Path(RAW_LOG).exists():
        with open(RAW_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
            print(f"Сырых сообщений: {len(lines)}")
    
    if Path(PARSED_LOG).exists():
        with open(PARSED_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
            print(f"Парсированных записей: {len(lines)}")
    
    print(f"\n📁 Логи сохранены:")
    print(f"  {RAW_LOG} - сырые сообщения")
    print(f"  {PARSED_LOG} - парсированные данные (JSON Lines)")
    
    print("\n🔍 Для анализа логов:")
    print(f"  tail -f {RAW_LOG} - следить за сырыми сообщениями")
    print(f"  tail -n 20 {PARSED_LOG} - последние 20 распарсенных")
    
    return True

if __name__ == "__main__":
    # Настройка вывода
    sys.stdout.reconfigure(line_buffering=True)
    
    try:
        success = asyncio.run(main())
        if success:
            print("\n✅ Тест завершён успешно!")
        else:
            print("\n❌ Тест завершён с ошибкой")
    except KeyboardInterrupt:
        print("\n\n⏹️ Остановлено пользователем")