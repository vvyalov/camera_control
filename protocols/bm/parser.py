"""
Парсер сырых сообщений Blackmagic BMPCC v.0.1
"""

from . import constants, decoder

def parse_bmpcc_message(data: bytes) -> dict:
    """
    Парсит сообщение в формате Blackmagic
    
    Args:
        data: Сырые байты от камеры
    
    Returns:
        Словарь с распарсенными данными
    """
    if len(data) < 4:
        return {"type": "raw", "data": data.hex()}
    
    # Проверяем формат FF [LEN] 00 00
    if data[0] == 0xFF and len(data) >= 4:
        length = data[1]
        
        if len(data) != 4 + length:
            return {"type": "invalid_length", "data": data.hex()}
        
        payload = data[4:]
        
        if len(payload) < 4:
            return {"type": "short_payload", "data": data.hex()}
        
        category = payload[0]
        subcategory = payload[1]
        
        # СПЕЦИАЛЬНАЯ ОБРАБОТКА ДЛЯ ТАЙМКОДА (0x09:0x04)
        if category == 0x09 and subcategory == 0x04:
            value = payload[4:] if len(payload) > 4 else b''
            timecode_data = decoder.decode_timecode_bcd(value)
            return {
                "type": "bmpcc_message",
                "category": category,
                "subcategory": subcategory,
                "timecode_data": timecode_data,
                "value_human": f"TC: {timecode_data['hhmmssff']}",
                "full_hex": data.hex(),
                "is_primary": True,
                "param_name": "Таймкод"
            }
        
        data_type = payload[2]
        subtype = payload[3]
        value = payload[4:] if len(payload) > 4 else b''
        
        # Определяем название категории
        category_name = constants.CATEGORY_NAMES.get(category, f"Неизвестная 0x{category:02X}")
        
        # Декодируем значение
        human_value = decoder.decode_value(category, subcategory, value)
        
        # Определяем, является ли параметр основным
        is_primary = (
            (category == 0x01 and subcategory == 0x0C) or  # Выдержка
            (category == 0x01 and subcategory == 0x0E) or  # ISO
            (category == 0x0C and subcategory == 0x0A) or  # Диафрагма
            (category == 0x0A and subcategory == 0x01) or  # Статус записи
            (category == 0x0C and subcategory == 0x0B) or  # Зум
            (category == 0x0C and subcategory == 0x0C)     # Фокус
        )
        
        # Определяем, являются ли данные сырыми
        is_raw = (category == 0x00 or category == 0x09)  # Экспозиция и Телеметрия
        
        return {
            "type": "bmpcc_message",
            "category": category,
            "category_name": category_name,
            "subcategory": subcategory,
            "data_type": data_type,
            "subtype": subtype,
            "value_raw": value.hex(),
            "value_human": human_value,
            "full_hex": data.hex(),
            "timestamp": "",
            "is_primary": is_primary,
            "is_raw": is_raw
        }
    
    # Если не формат FF - это может быть простой статус (один байт)
    if len(data) == 1:
        status_value = data[0]
        status_text = {
            0x01: "Готов",
            0x03: "Остановлена",
        }.get(status_value, f"Неизвестный статус 0x{status_value:02X}")
        
        return {
            "type": "status",
            "value": status_value,
            "value_human": status_text,
            "data": data.hex()
        }
    
    # Если не распознано
    return {"type": "raw", "data": data.hex()}

def format_message_for_log(parsed: dict) -> str:
    """Форматирует сообщение для лога"""
    msg_type = parsed.get('type', 'unknown')
    
    if msg_type == 'bmpcc_message':
        cat = parsed.get('category', 0)
        subcat = parsed.get('subcategory', 0)
        value = parsed.get('value_human', '')
        
        # Определяем префикс
        if parsed.get('is_primary', False):
            prefix = "✅"
        elif parsed.get('is_raw', False):
            prefix = "📊"
        else:
            prefix = "📡"
        
        # Особый формат для таймкода
        if cat == 0x09 and subcat == 0x04 and 'timecode_data' in parsed:
            tc_data = parsed['timecode_data']
            if isinstance(tc_data, dict) and 'hhmmssff' in tc_data:
                return f"✅ [{cat:02X}:{subcat:02X}] TC: {tc_data['hhmmssff']}"
        
        return f"{prefix} [{cat:02X}:{subcat:02X}] {value}"
    
    elif msg_type == 'status':
        return f"🔧 {parsed.get('value_human', '')}"
    
    elif msg_type == 'error':
        return f"❓ Ошибка: {parsed.get('data', '')}"
    
    else:
        return f"❓ {parsed}"
