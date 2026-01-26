"""
Константы протокола Blackmagic BMPCC
"""

# UUID каналов
UUID_NOTIFICATIONS = "b864e140-76a0-416a-bf30-5876504537d9"
UUID_TELEMETRY = "6d8f2110-86f1-41bf-9afb-451d87e976c8"
UUID_STATUS = "7fe8691d-95dc-4fc5-8abd-ca74339b51b9"

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