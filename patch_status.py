import sys

# Читаем исходный файл
with open('test_monitor.py', 'r') as f:
    content = f.read()

# Находим и заменяем класс CameraStatus
old_class = '''class CameraStatus:
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
        
        # Обновляем соответствующие поля
        # (позже добавим больше параметров)
        
        self.last_update = datetime.now()
    
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
        if self.recording:
            lines.append(f"🎥 ЗАПИСЬ: ВКЛ")
        else:
            lines.append(f"🎥 ЗАПИСЬ: ВЫКЛ")
            
        if self.last_update:
            lines.append(f"⏰ Обновлено: {self.last_update.strftime('%H:%M:%S')}")
            
        lines.append("=" * 40)
        return "\\n".join(lines)'''

new_class = '''class CameraStatus:
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
        return "\\n".join(lines)'''

# Заменяем
content = content.replace(old_class, new_class)

# Добавляем импорт констант в начало класса
import_line = 'from protocol.constants import CATEGORY_EXPOSURE, CATEGORY_CAMERA, CATEGORY_LENS, SUBCAT_SHUTTER, SUBCAT_APERTURE, SUBCAT_ISO_HIGH, SUBCAT_LENS_NAME'
content = content.replace('from protocol import parse_bmpcc_message', 
                         'from protocol import parse_bmpcc_message\n' + import_line)

# Сохраняем
with open('test_monitor.py', 'w') as f:
    f.write(content)

print("✅ Класс CameraStatus обновлён!")
