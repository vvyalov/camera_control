"""
Константы протокола Blackmagic BMPCC v.0.1
"""

# UUID каналов
UUID_BLACKMAGIC_SERVICE = "291d567a-6d75-11e6-8b77-86f30ca893d3"

# Характеристики с разными свойствами
UUID_NOTIFY_CHAR = "6d8f2110-86f1-41bf-9afb-451d87e976c8"      # notify
UUID_INDICATE_CHAR = "b864e140-76a0-416a-bf30-5876504537d9"     # indicate  
UUID_RW_CHAR = "7fe8691d-95dc-4fc5-8abd-ca74339b51b9"           # read/write/notify
UUID_WRITE_CHAR = "5dd3465f-1aee-4299-8493-d2eca2f8e1bb"        # write only
UUID_WRITE_CHAR_2 = "ffac0c52-c9fb-41a0-b063-cc76282eb89c"      # write only
UUID_READ_CHAR = "8f1fd018-b508-456f-8f82-3d392bee2706"         # read only

# Для обратной совместимости
UUID_NOTIFICATIONS = UUID_NOTIFY_CHAR  # Основной для данных = "6d8f2110-86f1-41bf-9afb-451d87e976c8"
UUID_TELEMETRY = UUID_INDICATE_CHAR    # Дополнительный = "b864e140-76a0-416a-bf30-5876504537d9"
UUID_STATUS = UUID_RW_CHAR             # Статус = "7fe8691d-95dc-4fc5-8abd-ca74339b51b9"

# Категории параметров
CATEGORY_EXPOSURE = 0x00      # Экспозиция
CATEGORY_CAMERA = 0x01        # Настройки камеры
CATEGORY_SYSTEM = 0x03        # Системные настройки
CATEGORY_TELEMETRY = 0x09     # Телеметрия
CATEGORY_COMMANDS = 0x0A      # Команды/Состояния
CATEGORY_LENS = 0x0C          # Объектив

# Подкатегории (известные)
SUBCAT_SHUTTER = 0x02         # Выдержка: 00028002
SUBCAT_APERTURE = 0x03        # Диафрагма: 00038002
SUBCAT_ISO_HIGH = 0x0E        # ISO (основной): 010E0302
SUBCAT_ISO_LOW = 0x0C         # ISO (альтернативный): 010C0302
SUBCAT_LENS_NAME = 0x09       # Название объектива: 0C090502

# Статус записи
SUBCAT_RECORDING_STATUS = 0x01  # 0A010102...

# Названия категорий для отображения
CATEGORY_NAMES = {
    0x00: "Экспозиция",
    0x01: "Настройки камеры", 
    0x03: "Система",
    0x09: "Телеметрия",
    0x0A: "Команды",
    0x0C: "Объектив",
}
