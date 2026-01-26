"""
Парсер сырых сообщений Blackmagic BMPCC
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
        data_type = payload[2]
        subtype = payload[3]
        value = payload[4:] if len(payload) > 4 else b''
        
        # Определяем название категории
        category_name = constants.CATEGORY_NAMES.get(category, f"Неизвестная 0x{category:02X}")
        
        # Декодируем значение
        human_value = decoder.decode_value(category, subcategory, value)
        
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
            "timestamp": ""  # Добавится позже при обработке
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
