#!/usr/bin/env python3
"""
УЛУЧШЕННЫЙ МОНИТОР BLACKMAGIC BMPCC
Использует библиотеку protocol для парсинга
"""

import asyncio
import sys
from datetime import datetime
from bleak import BleakClient
from pathlib import Path
import json

# Импортируем нашу библиотеку
from protocol import parse_bmpcc_message
from protocol.constants import CATEGORY_EXPOSURE, CATEGORY_CAMERA, CATEGORY_LENS, SUBCAT_SHUTTER, SUBCAT_APERTURE, SUBCAT_ISO_HIGH, SUBCAT_LENS_NAME
from protocol.constants import UUID_NOTIFICATIONS, UUID_TELEMETRY, UUID_STATUS

# ================= КОНФИГУРАЦИЯ =================
CAMERA_ADDRESS = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

# Файлы для логов
RAW_LOG = "raw_messages.log"
PARSED_LOG = "parsed_messages.json"
# ================================================

class CameraStatus:
    """Текущий статус камеры"""
    def __init__(self):
        self.iso = None
        self.shutter = None
        self.aperture = None
        self.recording = False
        self.lens_name = None
        self.battery = None
        self.last_update = None
        
    def update_from_message(self, parsed: dict):
        """Обновляет статус из распаршенного сообщения"""
        if parsed["type"] != "bmpcc_message":
            return
        
        category = parsed["category"]
        subcategory = parsed["subcategory"]
        value = parsed["value_human"]
        
        # Обновляем поля в зависимости от типа сообщения
        if category == CATEGORY_EXPOSURE:
            if subcategory == SUBCAT_SHUTTER and "1/" in value:
                self.shutter = value
            elif subcategory == SUBCAT_APERTURE and "f/" in value:
                self.aperture = value
                
        elif category == CATEGORY_CAMERA:
            if subcategory == SUBCAT_ISO_HIGH and "ISO" in value:
                self.iso = value
                
        elif category == CATEGORY_LENS:
            if subcategory == SUBCAT_LENS_NAME:
                self.lens_name = value
        
        # TODO: Добавить определение статуса записи
        # Пока предполагаем, что если приходят сообщения - камера не записывает
        self.recording = False
        
        self.last_update = parsed.get("timestamp", "")
    
    def __str__(self):
        """Красивый вывод статуса"""
        lines = []
        lines.append("📷 СТАТУС КАМЕРЫ")
        lines.append("=" * 40)
        
        if self.iso:
            lines.append(f"📊 ISO: {self.iso}")
        if self.shutter:
            lines.append(f"⏱️  Выдержка: {self.shutter}")
        if self.aperture:
            lines.append(f"🌅 Диафрагма: {self.aperture}")
        if self.lens_name:
            lines.append(f"🔍 Объектив: {self.lens_name}")
        if self.battery:
            lines.append(f"🔋 Батарея: {self.battery}%")
            
        if self.recording:
            lines.append(f"🎥 ЗАПИСЬ: ВКЛ 🔴")
        else:
            lines.append(f"🎥 ЗАПИСЬ: ВЫКЛ")
            
        if self.last_update:
            lines.append(f"⏰ Обновлено: {self.last_update}")
            
        lines.append("=" * 40)
        return "\n".join(lines)

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
    """Основная функция"""
    print("=" * 70)
    print("📡 УЛУЧШЕННЫЙ МОНИТОР BLACKMAGIC BMPCC")
    print("=" * 70)
    print(f"Камера: {CAMERA_ADDRESS}")
    print(f"Время начала: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Использует библиотеку: protocol v0.1.0")
    print("=" * 70)
    
    # Очищаем старые логи
    for log_file in [RAW_LOG, PARSED_LOG]:
        if Path(log_file).exists():
            Path(log_file).unlink()
    
    # Создаём объект статуса
    status = CameraStatus()
    
    def handle_notification(sender: str, data: bytes, source: str = "MAIN"):
        """Обработчик уведомлений от камеры"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # 1. Сохраняем сырое сообщение
        log_raw_message(timestamp, data, source)
        
        # 2. Парсим с помощью нашей библиотеки
        parsed = parse_bmpcc_message(data)
        parsed["timestamp"] = timestamp
        parsed["source"] = source
        
        # 3. Сохраняем распарсенное
        log_parsed_message(timestamp, parsed)
        
        # 4. Обновляем статус камеры
        status.update_from_message(parsed)
        
        # 5. Выводим в консоль (только важные параметры)
        if parsed["type"] == "bmpcc_message":
            category = parsed["category_name"]
            value = parsed["value_human"]
            
            # Выводим только интересующие нас параметры
            if "ISO" in value or "1/" in value or "f/" in value:
                print(f"\n[{timestamp}] 📨 {source}")
                print(f"   📊 {category} → {value}")
                
                # Показываем общий статус каждые 5 сообщений
                if hash(timestamp) % 5 == 0:
                    print(f"\n{status}")
        
        elif parsed["type"] == "status":
            print(f"\n[{timestamp}] ⚡ СТАТУС: {parsed['value_human']}")
    
    print("\n🔗 Подключаюсь к камере...")
    
    try:
        async with BleakClient(CAMERA_ADDRESS, timeout=10.0) as client:
            print("✅ Подключено!")
            
            # Получаем сервисы
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
            await client.start_notify(UUID_NOTIFICATIONS, 
                                     lambda s, d: handle_notification(s, d, "MAIN"))
            
            # Пытаемся подписаться на телеметрию
            try:
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
            
            print("\n" + "=" * 70)
            print("🎬 МОНИТОРИНГ АКТИВЕН")
            print("=" * 70)
            print("Сделайте что-то на камере:")
            print("1. Измените ISO/выдержку/диафрагму")
            print("2. Начните/остановите запись")
            print("3. Посмотрите как меняется статус в консоли")
            print("\nДля остановки нажмите Ctrl+C")
            print("=" * 70)
            
            # Мониторим пока не нажмут Ctrl+C
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n\n⏹️ Остановлено пользователем")
            
            # Отписываемся
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
    print(f"  {PARSED_LOG} - парсированные данные")
    
    print(f"\n{status}")
    
    return True

if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    
    try:
        success = asyncio.run(main())
        if success:
            print("\n✅ Мониторинг завершён успешно!")
        else:
            print("\n❌ Мониторинг завершён с ошибкой")
    except KeyboardInterrupt:
        print("\n\n⏹️ Остановлено пользователем")
