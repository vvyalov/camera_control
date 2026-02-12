"""
🎬 Blackmagic Camera Dashboard - Расширенная версия
С отображением всех параметров из протокола
"""

import asyncio
import sys
import time
from datetime import datetime
from collections import deque
from bleak import BleakClient, BleakScanner
import signal

CAMERA_UUID = "EFBF6DD4-6058-CF36-1421-68F5AECB6CAA"

class ExtendedCameraDashboard:
    def __init__(self):
        self.client = None
        
        # Основные данные
        self.free_timecode = "00:00:00:00"
        self.clip_timecode = "00:00:00:00"
        self.record_duration = "00:00:00:00"
        self.is_recording = False
        self.frame_rate = 0
        self.resolution = "?"
        
        # Настройки камеры (Группа 1: Video)
        self.white_balance = 0
        self.tint = 0
        self.shutter = 0
        self.shutter_type = "angle"  # "angle" или "speed"
        self.iso = 0
        self.dynamic_range = ""
        self.video_sharpening = ""
        self.auto_exposure_mode = ""
        self.gain = 0
        self.nd_filter = ""
        self.display_lut = ""
        
        # Настройки вывода (Группа 3: Output)
        self.overlay_enables = ""
        self.frame_guides_style = ""
        self.frame_guides_opacity = ""
        
        # Настройки дисплея (Группа 4: Display)
        self.display_brightness = ""
        self.exposure_focus_tools = ""
        self.zebra_level = ""
        self.peaking_level = ""
        self.color_bar_enable = ""
        self.focus_assist = ""
        self.program_return_feed = ""
        
        # Настройки медиа (Группа 10: Media)
        self.codec = ""
        self.codec_quality = ""
        self.transport_mode = "preview"
        self.transport_speed = 0
        self.transport_flags = 0
        self.slot1_medium = ""
        self.slot2_medium = ""
        
        # Метаданные (Группа 12)
        self.lens_model = ""
        self.aperture = ""
        self.focal_length = ""
        self.next_clip_name = ""
        
        # История клипов
        self.clip_history = deque(maxlen=5)
        self.next_clip_number = 1
        self.last_clip_duration = "00:00:00:00"
        
        # Статистика
        self.packets_received = 0
        self.last_update = time.time()
        self.connected = False
        
        # Для расчета длительности
        self.record_start_time = None
        
    def decode_timecode(self, data):
        """Декодирует таймкод из BCD формата"""
        if len(data) >= 12:
            try:
                frames = (data[8] >> 4) * 10 + (data[8] & 0x0F)
                seconds = (data[9] >> 4) * 10 + (data[9] & 0x0F)
                minutes = (data[10] >> 4) * 10 + (data[10] & 0x0F)
                hours = (data[11] >> 4) * 10 + (data[11] & 0x0F)
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
            except:
                pass
        return "00:00:00:00"
    
    def decode_string(self, data, start_idx=8):
        """Декодирует строку из байтов"""
        try:
            text = ""
            for i in range(start_idx, len(data)):
                if data[i] == 0:
                    break
                text += chr(data[i])
            return text.strip()
        except:
            return ""
    
    def decode_packet(self, data):
        """Декодирует пакет данных камеры"""
        if len(data) < 8 or data[0] != 0xFF:
            return None
        
        group = data[4]
        param = data[5]
        
        # ГРУППА 1: Video
        if group == 1:
            if param == 2 and len(data) >= 12:  # White Balance
                wbL = data[8]
                wbH = data[9] << 8
                self.white_balance = wbL + wbH
                
                tintL = data[10]
                tintH = data[11] << 8
                self.tint = tintL + tintH
                return "WHITE_BALANCE"
            
            elif param == 7 and len(data) >= 9:  # Dynamic Range Mode
                mode = data[8]
                modes = {0: "Film", 1: "Video", 2: "Extended Video"}
                self.dynamic_range = modes.get(mode, "Unknown")
                return "DYNAMIC_RANGE"
            
            elif param == 8 and len(data) >= 9:  # Video Sharpening Level
                level = data[8]
                levels = {0: "Off", 1: "Low", 2: "Medium", 3: "High"}
                self.video_sharpening = levels.get(level, "Unknown")
                return "VIDEO_SHARPENING"
            
            elif param == 9 and len(data) >= 18:  # Frame rate + resolution
                self.frame_rate = data[8]
                width = data[12] + (data[13] << 8)
                height = data[14] + (data[15] << 8)
                self.resolution = f"{width}x{height}"
                
                # Байт 16: flags (бит 4 = windowed mode)
                flags = data[16]
                if flags & 0x10:
                    self.resolution += " (windowed)"
                
                return "FRAME_RATE"
            
            elif param == 10 and len(data) >= 9:  # Auto Exposure Mode
                mode = data[8]
                modes = {
                    0: "Manual Trigger",
                    1: "Iris",
                    2: "Shutter",
                    3: "Iris + Shutter",
                    4: "Shutter + Iris"
                }
                self.auto_exposure_mode = modes.get(mode, "Unknown")
                return "AUTO_EXPOSURE"
            
            elif param == 11 and len(data) >= 12:  # Shutter Angle
                shutterL = data[8]
                shutterH = data[9] << 8
                self.shutter = (shutterL + shutterH) / 100.0
                self.shutter_type = "angle"
                return "SHUTTER"
            
            elif param == 12 and len(data) >= 12:  # Shutter Speed
                shutterL = data[8]
                shutterH = data[9] << 8
                self.shutter = shutterL + shutterH
                self.shutter_type = "speed"
                return "SHUTTER_SPEED"
            
            elif param == 13 and len(data) >= 9:  # Gain (dB)
                self.gain = data[8]
                if self.gain > 127:  # Обработка отрицательных значений
                    self.gain -= 256
                return "GAIN"
            
            elif param == 14 and len(data) >= 12:  # ISO
                isoL = data[8]
                isoH = data[9] << 8
                self.iso = isoL + isoH
                return "ISO"
            
            elif param == 15 and len(data) >= 10:  # Display LUT
                selected_lut = data[8]
                enabled = data[9]
                self.display_lut = f"{'On' if enabled else 'Off'} (LUT {selected_lut})"
                return "DISPLAY_LUT"
            
            elif param == 16 and len(data) >= 10:  # ND Filter
                ndL = data[8]
                ndH = data[9] << 8
                nd_value = (ndL + ndH) / 65536.0
                self.nd_filter = f"f/{nd_value:.1f}"
                return "ND_FILTER"
        
        # ГРУППА 3: Output
        elif group == 3:
            if param == 0 and len(data) >= 10:  # Overlay Enables
                overlayL = data[8]
                overlayH = data[9] << 8
                overlay_flags = overlayL + overlayH
                
                overlays = []
                if overlay_flags & 0x01: overlays.append("Status")
                if overlay_flags & 0x02: overlays.append("Frame Guides")
                
                self.overlay_enables = ", ".join(overlays) if overlays else "None"
                return "OVERLAY_ENABLES"
            
            elif param == 1 and len(data) >= 9:  # Frame Guides Style
                style = data[8]
                styles = {
                    0: "HDTV", 1: "4:3", 2: "2.4:1", 3: "2.39:1",
                    4: "2.35:1", 5: "1.85:1", 6: "Thirds"
                }
                self.frame_guides_style = styles.get(style, "Unknown")
                return "FRAME_GUIDES_STYLE"
            
            elif param == 2 and len(data) >= 10:  # Frame Guides Opacity
                opacityL = data[8]
                opacityH = data[9] << 8
                opacity = (opacityL + opacityH) / 65536.0
                self.frame_guides_opacity = f"{opacity:.1%}"
                return "FRAME_GUIDES_OPACITY"
        
        # ГРУППА 4: Display
        elif group == 4:
            if param == 0 and len(data) >= 10:  # Brightness
                brightnessL = data[8]
                brightnessH = data[9] << 8
                brightness = (brightnessL + brightnessH) / 65536.0
                self.display_brightness = f"{brightness:.0%}"
                return "DISPLAY_BRIGHTNESS"
            
            elif param == 1 and len(data) >= 10:  # Exposure and Focus Tools
                toolsL = data[8]
                toolsH = data[9] << 8
                tools_flags = toolsL + toolsH
                
                tools = []
                if tools_flags & 0x01: tools.append("Zebra")
                if tools_flags & 0x02: tools.append("Focus Assist")
                if tools_flags & 0x04: tools.append("False Color")
                
                self.exposure_focus_tools = ", ".join(tools) if tools else "None"
                return "EXPOSURE_FOCUS_TOOLS"
            
            elif param == 2 and len(data) >= 10:  # Zebra Level
                zebraL = data[8]
                zebraH = data[9] << 8
                zebra = (zebraL + zebraH) / 65536.0
                self.zebra_level = f"{zebra:.0%}"
                return "ZEBRA_LEVEL"
            
            elif param == 3 and len(data) >= 10:  # Peaking Level
                peakingL = data[8]
                peakingH = data[9] << 8
                peaking = (peakingL + peakingH) / 65536.0
                self.peaking_level = f"{peaking:.0%}"
                return "PEAKING_LEVEL"
            
            elif param == 4 and len(data) >= 9:  # Color Bar Enable
                timeout = data[8]
                if timeout == 0:
                    self.color_bar_enable = "Disabled"
                else:
                    self.color_bar_enable = f"Enabled ({timeout}s)"
                return "COLOR_BAR"
            
            elif param == 6 and len(data) >= 9:  # Program Return Feed Enable
                timeout = data[8]
                if timeout == 0:
                    self.program_return_feed = "Disabled"
                else:
                    self.program_return_feed = f"Enabled ({timeout}s)"
                return "PROGRAM_RETURN_FEED"
        
        # ГРУППА 10: Media
        elif group == 10:
            if param == 0 and len(data) >= 12:  # Codec
                basic_codec = data[8]
                codec_variant = data[9]
                
                codec_names = {0: "RAW", 1: "DNxHD", 2: "ProRes", 3: "BRAW"}
                quality_names = {
                    0: ["Q0", "HQ", "Q0", "HQ"],
                    1: ["Q5", "422", "Q5", "LT"],
                    2: ["3:1", "LT", "3:1", "Proxy"],
                    3: ["5:1", "Proxy", "5:1", "444"],
                    4: ["8:1", "444", "8:1", "444XQ"],
                    5: ["12:1", "444XQ", "12:1", ""]
                }
                
                codec_name = codec_names.get(basic_codec, "Unknown")
                quality_name = quality_names.get(codec_variant, ["Unknown"])[basic_codec]
                
                self.codec = f"{codec_name} {quality_name}".strip()
                return "CODEC"
            
            elif param == 1 and len(data) >= 13:  # Transport Mode
                transport_mode = data[8]
                transport_speed = data[9]
                transport_flags = data[10]
                slot1 = data[11]
                slot2 = data[12]
                
                # Режим транспорта
                modes = {0: "preview", 1: "play", 2: "record"}
                self.transport_mode = modes.get(transport_mode, "unknown")
                self.is_recording = (transport_mode == 2)
                
                # Скорость
                self.transport_speed = transport_speed
                
                # Флаги
                self.transport_flags = transport_flags
                
                # Носители
                slot_names = {0: "CFast", 1: "SD Card", 2: "SSD", 3: "USB"}
                self.slot1_medium = slot_names.get(slot1, "Unknown")
                self.slot2_medium = slot_names.get(slot2, "Unknown")
                
                # Обработка начала/конца записи
                if self.is_recording and not hasattr(self, '_was_recording'):
                    self.record_start_time = time.time()
                    self.clip_timecode = "00:00:00:00"
                elif not self.is_recording and hasattr(self, '_was_recording') and self._was_recording:
                    # Запись закончилась - добавляем в историю
                    if self.clip_timecode != "00:00:00:00":
                        self.clip_history.appendleft({
                            "number": len(self.clip_history) + 1,
                            "duration": self.clip_timecode
                        })
                        self.next_clip_number += 1
                
                self._was_recording = self.is_recording
                return "TRANSPORT_MODE"
        
        # ГРУППА 12: Metadata
        elif group == 12:
            if param == 9:  # Lens Model
                self.lens_model = self.decode_string(data)
                return "LENS_MODEL"
            
            elif param == 10:  # Aperture
                self.aperture = self.decode_string(data)
                return "APERTURE"
            
            elif param == 11:  # Focal Length
                self.focal_length = self.decode_string(data)
                return "FOCAL_LENGTH"
            
            elif param == 15:  # Next Clip Name
                self.next_clip_name = self.decode_string(data)
                return "NEXT_CLIP_NAME"
        
        return None
    
    def handle_timecode(self, data):
        """Обработчик таймкода"""
        new_timecode = self.decode_timecode(data)
        
        if new_timecode != self.free_timecode:
            self.free_timecode = new_timecode
            
            # Обновляем клип-таймкод если идет запись
            if self.is_recording:
                self.clip_timecode = new_timecode
                
                # Рассчитываем длительность записи
                if self.record_start_time:
                    elapsed = time.time() - self.record_start_time
                    hours = int(elapsed // 3600)
                    minutes = int((elapsed % 3600) // 60)
                    seconds = int(elapsed % 60)
                    frames = int((elapsed - int(elapsed)) * self.frame_rate) if self.frame_rate > 0 else 0
                    self.record_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
            
            self.update_display()
    
    def handle_camera_data(self, data):
        """Обработчик данных камеры"""
        self.packets_received += 1
        decoded = self.decode_packet(data)
        if decoded:
            self.update_display()
    
    async def send_command(self, data):
        """Отправляет команду на камеру"""
        try:
            for service in self.client.services:
                if "291d567a" in service.uuid.lower():
                    for char in service.characteristics:
                        if "5dd3465f" in char.uuid.lower():
                            await self.client.write_gatt_char(char.uuid, data)
                            return True
        except:
            pass
        return False
    
    def clear_screen(self):
        """Очищает экран"""
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.flush()
    
    def draw_box(self, x, y, width, height, title=""):
        """Рисует рамку с заголовком"""
        # Верхняя граница
        sys.stdout.write(f"\033[{y};{x}H╔{'═' * (width - 2)}╗")
        
        # Заголовок
        if title:
            title_pos = x + (width - len(title) - 4) // 2
            sys.stdout.write(f"\033[{y};{title_pos}H {title} ")
        
        # Боковые границы
        for i in range(1, height - 1):
            sys.stdout.write(f"\033[{y + i};{x}H║")
            sys.stdout.write(f"\033[{y + i};{x + width - 1}H║")
        
        # Нижняя граница
        sys.stdout.write(f"\033[{y + height - 1};{x}H╚{'═' * (width - 2)}╝")
    
    def draw_divider(self, x, y, width):
        """Рисует разделитель"""
        sys.stdout.write(f"\033[{y};{x}H{'─' * width}")
    
    def update_display(self):
        """Обновляет весь дисплей"""
        self.clear_screen()
        
        screen_width = 80
        screen_height = 24
        
        # Верхний заголовок
        sys.stdout.write("\033[1;1H" + "═" * screen_width)
        status = "🔴 RECORDING" if self.is_recording else "⚪ STANDBY"
        title = f"🎬 BLACKMAGIC DASHBOARD | {status} | 📦 {self.packets_received}"
        title_x = (screen_width - len(title)) // 2
        sys.stdout.write(f"\033[2;{title_x}H{title}")
        sys.stdout.write("\033[3;1H" + "═" * screen_width)
        
        # Первая строка: Timecode + Camera Settings
        self.draw_box(2, 5, 38, 8, "⏱️ TIMECODE")
        self.draw_divider(4, 6, 34)
        
        sys.stdout.write(f"\033[7;4H  FREE TC: {self.free_timecode}")
        sys.stdout.write(f"\033[8;4H  CLIP TC: {self.clip_timecode}")
        
        self.draw_box(42, 5, 38, 8, "📷 CAMERA")
        self.draw_divider(44, 6, 34)
        
        # Camera settings - 4 строки
        shutter_display = f"{self.shutter}{'°' if self.shutter_type == 'angle' else ''}" if self.shutter else "—"
        sys.stdout.write(f"\033[7;44H  Shutter:  {shutter_display}")
        sys.stdout.write(f"\033[8;44H  Aperture: {self.aperture if self.aperture else '—'}")
        sys.stdout.write(f"\033[9;44H  ISO:      {self.iso if self.iso else '—'}")
        sys.stdout.write(f"\033[10;44H  FPS:      {self.frame_rate if self.frame_rate else '—'}")
        
        # Вторая строка: Video Settings + Output Settings
        self.draw_box(2, 14, 38, 10, "🎥 VIDEO SETTINGS")
        self.draw_divider(4, 15, 34)
        
        # Video settings - 8 строк
        row = 16
        if self.white_balance:
            sys.stdout.write(f"\033[{row};4H  WB:       {self.white_balance}K")
            row += 1
        if self.dynamic_range:
            sys.stdout.write(f"\033[{row};4H  DR Mode:  {self.dynamic_range}")
            row += 1
        if self.auto_exposure_mode:
            sys.stdout.write(f"\033[{row};4H  AE Mode:  {self.auto_exposure_mode}")
            row += 1
        if self.display_lut:
            sys.stdout.write(f"\033[{row};4H  LUT:      {self.display_lut}")
            row += 1
        if self.nd_filter:
            sys.stdout.write(f"\033[{row};4H  ND Filter:{self.nd_filter}")
            row += 1
        if self.video_sharpening:
            sys.stdout.write(f"\033[{row};4H  Sharpen:  {self.video_sharpening}")
            row += 1
        
        self.draw_box(42, 14, 38, 10, "📺 OUTPUT SETTINGS")
        self.draw_divider(44, 15, 34)
        
        # Output settings
        row = 16
        if self.overlay_enables:
            sys.stdout.write(f"\033[{row};44H  Overlays: {self.overlay_enables}")
            row += 1
        if self.frame_guides_style:
            sys.stdout.write(f"\033[{row};44H  Guides:   {self.frame_guides_style}")
            row += 1
        if self.frame_guides_opacity:
            sys.stdout.write(f"\033[{row};44H  Opacity:  {self.frame_guides_opacity}")
            row += 1
        if self.display_brightness:
            sys.stdout.write(f"\033[{row};44H  Bright:   {self.display_brightness}")
            row += 1
        
        # Третья строка: Media Info + Clips History
        self.draw_box(2, 25, 38, 10, "📁 MEDIA INFO")
        self.draw_divider(4, 26, 34)
        
        # Media info
        row = 27
        if self.codec:
            sys.stdout.write(f"\033[{row};4H  Codec:    {self.codec}")
            row += 1
        if self.transport_mode:
            mode_display = self.transport_mode.capitalize()
            if self.transport_speed:
                mode_display += f" ({self.transport_speed}x)"
            sys.stdout.write(f"\033[{row};4H  Mode:     {mode_display}")
            row += 1
        if self.slot1_medium:
            sys.stdout.write(f"\033[{row};4H  Slot 1:   {self.slot1_medium}")
            row += 1
        if self.slot2_medium:
            sys.stdout.write(f"\033[{row};4H  Slot 2:   {self.slot2_medium}")
            row += 1
        if self.next_clip_name:
            sys.stdout.write(f"\033[{row};4H  Next:     {self.next_clip_name[:20]}")
            row += 1
        
        self.draw_box(42, 25, 38, 10, "🎬 CLIPS HISTORY")
        self.draw_divider(44, 26, 34)
        
        # Clips history
        row = 27
        if self.clip_history:
            for clip in list(self.clip_history)[:4]:
                sys.stdout.write(f"\033[{row};44H  Clip {clip['number']:2d}: {clip['duration']}")
                row += 1
        else:
            sys.stdout.write(f"\033[{row};44H  No clips recorded")
        
        # Нижний бар
        sys.stdout.write(f"\033[36;1H" + "─" * screen_width)
        
        # Информация о камере
        info_parts = []
        if self.lens_model:
            info_parts.append(f"📸 {self.lens_model[:20]}...")
        if self.focal_length:
            info_parts.append(f"🔍 {self.focal_length}")
        if self.resolution != "?":
            info_parts.append(f"📐 {self.resolution}")
        
        info_line = " | ".join(info_parts) if info_parts else "No camera info"
        sys.stdout.write(f"\033[37;2H{info_line}")
        
        # Статус бар
        current_time = datetime.now().strftime("%H:%M:%S")
        if self.is_recording:
            status_text = f"🔴 REC {self.record_duration} | 🕒 {current_time}"
        else:
            status_text = f"⚪ STANDBY | 🕒 {current_time}"
        
        sys.stdout.write(f"\033[37;{screen_width - len(status_text) - 1}H{status_text}")
        
        sys.stdout.flush()
        self.last_update = time.time()
    
    async def request_all_data(self):
        """Запрашивает все данные с камеры"""
        if not self.connected:
            return
        
        commands = [
            # Frame rate and resolution
            bytes([0xFF, 0x01, 0x00, 0x00, 0x01, 0x09, 0x00, 0x00]),
            # Transport mode
            bytes([0xFF, 0x01, 0x00, 0x00, 0x0A, 0x01, 0x00, 0x00]),
            # White balance
            bytes([0xFF, 0x01, 0x00, 0x00, 0x01, 0x02, 0x00, 0x00]),
            # ISO
            bytes([0xFF, 0x01, 0x00, 0x00, 0x01, 0x0E, 0x00, 0x00]),
            # Shutter
            bytes([0xFF, 0x01, 0x00, 0x00, 0x01, 0x0B, 0x00, 0x00]),
            # Lens model
            bytes([0xFF, 0x01, 0x00, 0x00, 0x0C, 0x09, 0x00, 0x00]),
        ]
        
        for cmd in commands:
            await self.send_command(cmd)
            await asyncio.sleep(0.1)
    
    async def run_dashboard(self):
        """Запускает дашборд"""
        signal.signal(signal.SIGINT, lambda s, f: self._shutdown())
        
        print("🔍 Поиск Blackmagic камеры...")
        
        try:
            device = await BleakScanner.find_device_by_address(CAMERA_UUID)
            if not device:
                print(f"❌ Камера {CAMERA_UUID} не найдена")
                return
            
            print(f"✅ Найдена: {device.name}")
            
            self.client = BleakClient(device)
            await self.client.connect(timeout=15.0)
            self.connected = True
            print("✅ Подключено!\n")
            
            # Начальная отрисовка
            self.update_display()
            print("\n🔄 Настройка обработчиков...")
            
            # Настройка BLE обработчиков
            for service in self.client.services:
                if "291d567a" in service.uuid.lower():
                    for char in service.characteristics:
                        if "6d8f2110" in char.uuid.lower():  # Timecode
                            await self.client.start_notify(char.uuid, 
                                                          lambda s, d: self.handle_timecode(d))
                        
                        elif "b864e140" in char.uuid.lower():  # Camera Data
                            await self.client.start_notify(char.uuid,
                                                          lambda s, d: self.handle_camera_data(d))
            
            print("✅ Обработчики настроены")
            print("\n🔄 Запрос начальных данных...")
            
            # Запрос начальных данных
            await self.request_all_data()
            
            print("\n✅ Дашборд запущен!")
            print("   Нажмите Ctrl+C для выхода\n")
            
            # Главный цикл
            request_counter = 0
            while True:
                await asyncio.sleep(1)
                request_counter += 1
                
                if request_counter >= 15:
                    await self.request_all_data()
                    request_counter = 0
                
                if time.time() - self.last_update > 3:
                    self.update_display()
                    
        except KeyboardInterrupt:
            print("\n\n🛑 Остановлено пользователем")
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self._shutdown()
    
    async def _shutdown(self):
        """Завершение работы"""
        self.clear_screen()
        print("\n" + "="*60)
        print("📊 ФИНАЛЬНАЯ СТАТИСТИКА:")
        print("="*60)
        print(f"Пакетов получено: {self.packets_received}")
        print(f"Частота кадров: {self.frame_rate} fps")
        print(f"Разрешение: {self.resolution}")
        print(f"Объектив: {self.lens_model}")
        print(f"Кодек: {self.codec}")
        print(f"Записанных клипов: {len(self.clip_history)}")
        print("="*60)
        
        if self.client and self.client.is_connected:
            await self.client.disconnect()
        
        sys.exit(0)

def main():
    """Точка входа"""
    try:
        import bleak
    except ImportError:
        print("❌ Установите библиотеку: pip install bleak")
        sys.exit(1)
    
    dashboard = ExtendedCameraDashboard()
    
    try:
        asyncio.run(dashboard.run_dashboard())
    except KeyboardInterrupt:
        print("\n👋 Выход")

if __name__ == "__main__":
    main()