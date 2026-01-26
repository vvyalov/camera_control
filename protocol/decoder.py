"""
Декодер кодов в читаемые значения для Blackmagic Pocket Cinema Camera
"""

from . import tables

def decode_shutter(raw_bytes: bytes) -> str:
    """
    Декодирует байты выдержки в читаемый вид (1/50, 1/100 и т.д.)
    """
    if len(raw_bytes) < 4:
        return f"Недостаточно данных: {raw_bytes.hex()}"
    
    # Конвертируем байты в число (little-endian)
    code = int.from_bytes(raw_bytes[:4], 'little')
    
    # Ищем в таблице известных значений
    if code in tables.SHUTTER_TABLE:
        return tables.SHUTTER_TABLE[code]
    
    # Пробуем вычислить выдержку из кода
    if code == 0:
        return "Выдержка ???"
    
    # Экспериментальная формула
    shutter_sec = code / 173650.0
    
    # Конвертируем в дробь 1/XXX
    if shutter_sec >= 1:
        return f"{shutter_sec:.1f} сек"
    elif shutter_sec > 0:
        shutter_fraction = 1 / shutter_sec
        # Округляем до стандартных значений
        standard_values = [1, 2, 4, 8, 15, 30, 60, 120, 250, 500, 1000, 2000]
        closest = min(standard_values, key=lambda x: abs(x - shutter_fraction))
        return f"1/{closest}"
    else:
        return f"1/??? (код: 0x{code:04X})"

def decode_aperture(raw_bytes: bytes) -> str:
    """
    Декодирует байты диафрагмы для BMPCC 6K
    Полная таблица на основе всех экспериментов
    """
    if len(raw_bytes) < 2:
        return f"Недостаточно данных: {raw_bytes.hex()}"
    
    # Конвертируем в число (little-endian)
    code = int.from_bytes(raw_bytes[:2], 'little')
    
    # ПОЛНАЯ ТАБЛИЦА СООТВЕТСТВИЙ из всех экспериментов
    aperture_table = {
        # Основные значения из последних экспериментов
        0x0000: "f/2.8",    # Начальное значение
        0x2800: "f/1.8",    # f/1.8
        0x5000: "f/2.9",    # f/2.9
        0x7800: "f/3.1",    # f/3.1
        0xA000: "f/3.4",    # Среднее f/3.2-3.5
        0xC800: "f/3.7",    # f/3.7
        0xF000: "f/3.8",    # f/3.8
        0x0119: "f/4.0",    # f/4.0
        0x0141: "f/4.3",    # Среднее f/4.2-4.4
        0x0169: "f/4.7",    # Среднее f/4.6-4.8
        0x0191: "f/5.0",    # f/5.0
        0x01B9: "f/5.0",    # f/5.0
        0x01E1: "f/5.2",    # f/5.2
        
        # Новые коды из последнего эксперимента (4-значные hex)
        0x020A: "f/3.1",    # f/3.1
        0x0232: "f/3.7",    # f/3.7
        0x025A: "f/3.7",    # f/3.7
        0x0282: "f/3.7",    # f/3.7
        0x02AA: "f/3.7",    # f/3.7
        0x02D2: "f/3.7",    # f/3.7
        0x02FA: "f/3.1",    # f/3.1
        0x0323: "f/4.2",    # f/4.2
        0x034B: "f/4.2",    # f/4.2
        0x0373: "f/4.2",    # f/4.2
        0x039B: "f/4.2",    # f/4.2
        0x03C3: "f/4.2",    # f/4.2
        
        # Старые значения для совместимости
        0x0028: "f/1.8",    # Старый код f/1.8
        0x043C: "f/5.6",    # f/5.6
        0x04DC: "f/6.7",    # f/6.7
        0x06BE: "f/11",     # f/11
        0x0800: "f/16",     # f/16
    }
    
    # Сначала ищем точное соответствие
    if code in aperture_table:
        return aperture_table[code]
    
    # Также проверяем таблицу из tables.py
    if code in tables.APERTURE_TABLE:
        return tables.APERTURE_TABLE[code]
    
    # Если код неизвестен
    return f"f/??? (код: 0x{code:04X})"

def decode_aperture_text(raw_bytes: bytes) -> str:
    """
    Декодирует текстовое значение диафрагмы (формат: f1.8, f2.0, f4.2 и т.д.)
    Пример: 0x66312e3830 → "f1.80" → "f/1.8"
    """
    try:
        # Конвертируем hex в ASCII
        text = raw_bytes.decode('ascii', errors='ignore')
        
        # Убираем нулевые символы и пробелы
        text = text.strip('\x00').strip()
        
        if not text:
            return "f/???"
            
        # Проверяем формат
        if text.startswith('f'):
            # Если текст уже в формате f/X.X
            if '/' in text:
                return text
            # Если в формате fX.X
            else:
                # Преобразуем f1.8 → f/1.8
                number = text[1:]  # Убираем 'f'
                return f"f/{number}"
        return text
    except:
        return f"f/??? (0x{raw_bytes.hex()})"

def decode_iso(raw_bytes: bytes) -> str:
    """
    Декодирует ISO (просто число)
    """
    if len(raw_bytes) < 4:
        return f"Недостаточно данных: {raw_bytes.hex()}"
    
    iso_value = int.from_bytes(raw_bytes[:4], 'little')
    return f"ISO {iso_value}"

def decode_lens_name(raw_bytes: bytes) -> str:
    """
    Декодирует название объектива (текст ASCII)
    """
    try:
        # Убираем нулевые байты в конце
        clean_bytes = raw_bytes.rstrip(b'\x00')
        return clean_bytes.decode('ascii', errors='ignore').strip()
    except:
        return f"Бинарные данные: {raw_bytes.hex()[:20]}..."

def decode_recording_status(raw_bytes: bytes) -> str:
    """
    Декодирует статус записи
    Формат: XX0040000103, где XX:
      00 = остановлена
      02 = запись
    """
    if len(raw_bytes) < 6:
        return f"Неизвестный статус: {raw_bytes.hex()}"
    
    status_byte = raw_bytes[0]
    
    if status_byte == 0x00:
        return "Остановлена"
    elif status_byte == 0x02:
        return "Запись 🔴"
    else:
        return f"Неизвестный статус (0x{status_byte:02X})"

def decode_battery(raw_bytes: bytes) -> str:
    """
    Декодирует уровень батареи (предположительно)
    """
    if len(raw_bytes) < 1:
        return "Батарея: неизвестно"
    
    # Предполагаем что первый байт - процент
    battery_percent = raw_bytes[0]
    
    if battery_percent <= 100:
        # Простые уровни
        if battery_percent >= 80:
            level = "🔋"
        elif battery_percent >= 50:
            level = "🔋"
        elif battery_percent >= 20:
            level = "🪫"
        else:
            level = "🪫"
        
        return f"{level} {battery_percent}%"
    else:
        return f"Батарея: 0x{raw_bytes.hex()}"

def decode_focus_distance(raw_bytes: bytes) -> str:
    """
    Декодирует дистанцию фокусировки
    Пример: 0x3238306d6d20746f203239306d6d → "280mm to 290mm"
    """
    try:
        text = raw_bytes.decode('ascii', errors='ignore')
        text = text.strip('\x00').strip()
        
        if not text:
            return "Фокус: ??"
        
        # Если это диапазон (Xmm to Ymm)
        if 'to' in text:
            return f"Фокус: {text}"
        # Если одно значение
        elif text.endswith('mm'):
            return f"Фокус: {text}"
        # Если бесконечность
        elif text == 'Inf':
            return "Фокус: ∞"
        else:
            return f"Фокус: {text}"
    except:
        return f"Фокус: 0x{raw_bytes.hex()}"

def decode_focal_length(raw_bytes: bytes) -> str:
    """
    Декодирует фокусное расстояние (в mm)
    Пример: 0x33326d6d → "32mm"
    """
    try:
        text = raw_bytes.decode('ascii', errors='ignore')
        text = text.strip('\x00').strip()
        
        if not text:
            return "Зум: ??"
        
        if text.endswith('mm'):
            return f"Зум: {text}"
        else:
            # Пробуем извлечь число
            import re
            numbers = re.findall(r'\d+', text)
            if numbers:
                return f"Зум: {numbers[0]}mm"
            return f"Зум: {text}"
    except:
        return f"Зум: 0x{raw_bytes.hex()}"

def decode_value(category: int, subcategory: int, raw_bytes: bytes) -> str:
    """
    Универсальный декодер значения по категории и подкатегории
    """
    from . import constants
    
    # Сначала пробуем декодировать как текст (ASCII)
    try:
        text = raw_bytes.decode('ascii', errors='ignore').strip('\x00').strip()
        if text and len(text) > 1:
            # Если это диафрагма в формате fX.X
            if text.startswith('f') and any(c.isdigit() for c in text):
                if '/' in text:
                    return text  # уже в формате f/X.X
                else:
                    # f1.8 → f/1.8
                    number = text[1:]  # убираем 'f'
                    return f"f/{number}"
            
            # Если это фокусное расстояние
            elif text.endswith('mm'):
                if 'to' in text:
                    return f"Фокус: {text}"
                else:
                    return f"Зум: {text}"
            
            # Если это название объектива
            elif 'Sigma' in text or ('mm' in text and 'f/' in text):
                return text
    except:
        pass  # Не текстовые данные, пробуем дальше
    
    # Категория 0x00 - Экспозиция
    if category == constants.CATEGORY_EXPOSURE:
        if subcategory == constants.SUBCAT_SHUTTER:
            return decode_shutter(raw_bytes)
        elif subcategory == constants.SUBCAT_APERTURE:
            return decode_aperture(raw_bytes)
    
    # Категория 0x01 - Камера
    elif category == constants.CATEGORY_CAMERA:
        if subcategory in [constants.SUBCAT_ISO_HIGH, constants.SUBCAT_ISO_LOW]:
            return decode_iso(raw_bytes)
        elif subcategory == 0x0D:
            return decode_battery(raw_bytes)
    
    # Категория 0x0C - Объектив
    elif category == constants.CATEGORY_LENS:
        if subcategory == constants.SUBCAT_LENS_NAME:
            return decode_lens_name(raw_bytes)
        elif subcategory in [constants.SUBCAT_APERTURE, 0x0A]:  # Диафрагма объектива
            return decode_aperture_text(raw_bytes)
        elif subcategory in [0x0B, 0x0C]:  # Фокусное расстояние и дистанция
            try:
                text = raw_bytes.decode('ascii', errors='ignore').strip('\x00').strip()
                if text:
                    if 'to' in text or text.endswith('mm'):
                        return f"Фокус: {text}"
                    else:
                        return f"Фокус: {text}"
            except:
                pass
    
    # Категория 0x0F - Команды
    elif category == constants.CATEGORY_COMMANDS:
        if subcategory == constants.SUBCAT_RECORDING_STATUS:
            return decode_recording_status(raw_bytes)
    
    # Проверяем имена параметров из таблицы
    param_key = (category, subcategory)
    if param_key in tables.PARAM_NAMES:
        param_name = tables.PARAM_NAMES[param_key]
        
        # Специальная обработка для известных параметров
        if "Диафрагма" in param_name:
            # Пробуем как текст
            try:
                text = raw_bytes.decode('ascii', errors='ignore').strip('\x00').strip()
                if text.startswith('f'):
                    if '/' in text:
                        return text
                    else:
                        return f"f/{text[1:]}"
            except:
                pass
        
        return f"{param_name}: 0x{raw_bytes.hex()}"
    
    # По умолчанию - hex представление
    if len(raw_bytes) == 0:
        return "(пусто)"
    
    # Пробуем показать как текст если похоже на ASCII
    try:
        text = raw_bytes.decode('ascii', errors='ignore').strip('\x00').strip()
        if text and len(text) >= 2:
            return f"Текст: {text}"
    except:
        pass
    
    hex_str = raw_bytes.hex().upper()
    if len(hex_str) > 20:
        return f"0x{hex_str[:20]}..."
    
    return f"0x{hex_str}"