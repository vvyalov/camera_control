#!/usr/bin/env python3
"""
🎬 BLACKMAGIC CAMERA MONITOR v4.0
Профессиональный двухколоночный layout
"""

import os
import sys

# ================= КРИТИЧЕСКИ ВАЖНО =================
# Добавляем путь к проекту для импорта protocols
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
# ====================================================

import asyncio
from datetime import datetime
from bleak import BleakClient

# Теперь импорты должны работать
from protocols.bm import parse_bmpcc_message
from protocols.bm.constants import UUID_NOTIFICATIONS, UUID_TELEMETRY

# ================= КОНФИГУРАЦИЯ =================
# Получаем адрес камеры из аргументов
if len(sys.argv) > 1:
    CAMERA_ADDRESS = sys.argv[1]
elif os.path.exists("selected_camera.txt"):
    with open("selected_camera.txt", "r") as f:
        CAMERA_ADDRESS = f.read().strip()
else:
    print("❌ Адрес камеры не указан!")
    print("Использование: python3 main_monitor.py <адрес_камеры>")
    sys.exit(1)

REFRESH_RATE = 0.1  # 10 раз в секунду
# ================================================

class CameraMonitor:
    """Монитор камеры с двухколоночным layout"""
    
    def __init__(self):
        # Основные значения
        self.values = {
            'timecode': "—",        # CLIP TC (09:04)
            'global_timecode': "—", # GLOBAL TC (из UUID_TELEMETRY)
            'shutter': "—",
            'aperture': "—",
            'iso': "—",
            'lens': "—",
            'zoom': "—",
            'focus': "—",
        }
        
        # Блок записи
        self.recording_status = "⚪"  # ⚪ или 🔴
        self.recording_duration = "00:00:00:00"
        self.current_clip_start = None
        
        # История клипов
        self.clips = []  # Список строк в формате "HH:MM:SS:сс"
        
        # Оставшееся время на диске
        self.remaining_time = "00:00:00:00"
        
        # Статистика
        self.is_connected = False
        self.start_time = datetime.now()
        self.message_count = 0
        
        # Отладка
        self.show_raw = False
        self.paused = False
        
    def clear_screen(self):
        """Очищает экран"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def draw_header(self):
        """Рисует заголовок"""
        session_time = datetime.now() - self.start_time
        hours = session_time.seconds // 3600
        minutes = (session_time.seconds % 3600) // 60
        seconds = session_time.seconds % 60
        
        print("╔══════════════════════════════════════════════════════════════════════════╗")
        print("║ 🎬 BLACKMAGIC CAMERA MONITOR v4.0".ljust(77) + "║")
        print("╠══════════════════════════════════════════════════════════════════════════╣")
        
        status = "✅ CONNECTED" if self.is_connected else "❌ DISCONNECTED"
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        print(f"║ Status: {status:18} | Session: {time_str:8} | Msgs: {self.message_count:6} ║")
        print("╚══════════════════════════════════════════════════════════════════════════╝")
    
    def draw_timecode_section(self):
        """Рисует секцию таймкода"""
        # Отображаем оба таймкода
        clip_tc = self.values['timecode']
        global_tc = self.values['global_timecode']
        
        if clip_tc != "—" or global_tc != "—":
            # Используем clip_tc как основной, если он есть
            tc = clip_tc if clip_tc != "—" else global_tc
            tc_type = "CLIP" if clip_tc != "—" else "GLOBAL"
            
            try:
                hh, mm, ss, cc = map(int, tc.split(':'))
                day_percent = (hh * 3600 + mm * 60 + ss + cc/100) / 86400 * 100
                
                bar_length = 15
                filled = int(day_percent * bar_length / 100)
                bar = "█" * filled + "░" * (bar_length - filled)
                
                print(f"  TC: {tc} [{bar}] {day_percent:.0f}%")
                print(f"     ({tc_type} TIMECODE)")
            except:
                print(f"  TC: {tc}")
                print(f"     ({tc_type} TIMECODE)")
        else:
            print("  TC: —")
    
    def draw_recording_section(self):
        """Рисует секцию записи"""
        # Обновляем длительность если идет запись
        if self.current_clip_start and self.recording_status == "🔴":
            elapsed = datetime.now() - self.current_clip_start
            hours = elapsed.seconds // 3600
            minutes = (elapsed.seconds % 3600) // 60
            seconds = elapsed.seconds % 60
            hundredths = int(elapsed.microseconds / 10000)
            self.recording_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{hundredths:02d}"
        
        print(f"  REC: {self.recording_status} {self.recording_duration}")
    
    def draw_clips_section(self):
        """Рисует секцию истории клипов"""
        if self.clips:
            # Показываем последние 3 клипа
            clips_to_show = self.clips[-3:]
            for i, clip in enumerate(reversed(clips_to_show), 1):
                clip_num = len(self.clips) - len(clips_to_show) + i
                print(f"  Clip {clip_num:2}: {clip}")
        else:
            print("  No clips")
            print()
            print()
    
    def draw_camera_section(self):
        """Рисует секцию настроек камеры"""
        print(f"  Shutter:  {self.values['shutter']}")
        print(f"  Aperture: {self.values['aperture']}")
        print(f"  ISO:      {self.values['iso']}")
    
    def draw_remaining_section(self):
        """Рисует секцию оставшегося времени"""
        print(f"  REM: {self.remaining_time}")
    
    def draw_lens_section(self):
        """Рисует секцию объектива"""
        print(f"  Lens:  {self.values['lens']}")
        print(f"  Zoom:  {self.values['zoom']}")
        print(f"  Focus: {self.values['focus']}")
    
    def draw_dashboard(self):
        """Рисует всю панель приборов"""
        self.clear_screen()
        self.draw_header()
        print()
        
        # Верхняя строка
        print(" " * 2 + "╔══════════════════════════════╦══════════════════════════════╗")
        print(" " * 2 + "║ ⏱️ TIMECODE                 ║ 🎬 RECORDING                 ║")
        print(" " * 2 + "║ ──────────────────────────── ║ ──────────────────────────── ║")
        
        # Таймкод и запись
        print(" " * 2 + "║", end="")
        self.draw_timecode_section()
        print(" " * (30 - 28) + "║", end="")
        self.draw_recording_section()
        print(" " * (30 - 28) + "║")
        
        print(" " * 2 + "║                              ║                              ║")
        
        # Средняя строка
        print(" " * 2 + "╠══════════════════════════════╬══════════════════════════════╣")
        print(" " * 2 + "║ 📁 CLIPS HISTORY            ║ 📷 CAMERA                   ║")
        print(" " * 2 + "║ ──────────────────────────── ║ ──────────────────────────── ║")
        
        # История клипов и настройки
        print(" " * 2 + "║", end="")
        self.draw_clips_section()
        print(" " * (30 - 28) + "║", end="")
        self.draw_camera_section()
        print(" " * (30 - 28) + "║")
        
        # Нижняя строка
        print(" " * 2 + "╠══════════════════════════════╬══════════════════════════════╣")
        print(" " * 2 + "║ 💾 DISK REMAINING           ║ 🎥 LENS                     ║")
        print(" " * 2 + "║ ──────────────────────────── ║ ──────────────────────────── ║")
        
        # Оставшееся время и объектив
        print(" " * 2 + "║", end="")
        self.draw_remaining_section()
        print(" " * (30 - 15) + "║", end="")
        self.draw_lens_section()
        print(" " * (30 - 28) + "║")
        
        print(" " * 2 + "╚══════════════════════════════╩══════════════════════════════╝")
        
        # Подвал
        print()
        print("═" * 62)
        print("Controls: [Q]uit [R]aw data [P]ause [C]lear [F]PS toggle")
        print("═" * 62)
    
    def handle_message(self, parsed_data, raw_data):
        """Обрабатывает сообщение от камеры"""
        self.message_count += 1
        
        msg_type = parsed_data.get('type', '')
        
        # ГЛОБАЛЬНЫЙ таймкод (из UUID_TELEMETRY)
        if msg_type == 'global_timecode':
            timecode_data = parsed_data.get('timecode', {})
            if isinstance(timecode_data, dict):
                tc_value = timecode_data.get('hhmmsscc', '—')
                self.values['global_timecode'] = tc_value
                
                if self.show_raw:
                    tc_type = parsed_data.get('is_global_tc', False)
                    source = "GLOBAL" if tc_type else "UNKNOWN"
                    print(f"[{source} TC] {tc_value}")
            return  # ← ВЫХОДИМ, это не BMPCC сообщение
        
        # Статус (standalone сообщение)
        elif msg_type == 'status':
            if self.show_raw:
                status_text = parsed_data.get('value_human', '')
                print(f"[STATUS] {status_text}")
            return
        
        # RAW сообщение (отладка)
        elif msg_type == 'raw':
            if self.show_raw:
                data_hex = parsed_data.get('data', '')
                print(f"[RAW DATA] {data_hex[:20]}...")
            return
        
        # Остальной код для BMPCC сообщений...
        if msg_type != 'bmpcc_message':
            return
        
        category = parsed_data.get('category')
        subcategory = parsed_data.get('subcategory')
        value_human = parsed_data.get('value_human', '')
        
        # Сырые данные для отладки
        if self.show_raw:
            try:
                from protocols.bm.parser import format_message_for_log
                log_line = format_message_for_log(parsed_data)
                if "✅" in log_line or "09:04" in log_line or "0A:01" in log_line:
                    print(log_line)
            except ImportError:
                pass
        
        # Таймкод КЛИПА (09:04)
        if category == 0x09 and subcategory == 0x04:
            if 'timecode_data' in parsed_data:
                tc_data = parsed_data['timecode_data']
                if isinstance(tc_data, dict):
                    self.values['timecode'] = tc_data.get('hhmmsscc', '—')
        
        # Статус записи (0A:01)
        elif category == 0x0A and subcategory == 0x01:
            if "🔴" in value_human:
                self.recording_status = "🔴"
                if self.current_clip_start is None:
                    self.current_clip_start = datetime.now()
                    self.recording_duration = "00:00:00:00"
            else:
                self.recording_status = "⚪"
                if self.current_clip_start:
                    # Сохраняем клип
                    elapsed = datetime.now() - self.current_clip_start
                    hours = elapsed.seconds // 3600
                    minutes = (elapsed.seconds % 3600) // 60
                    seconds = elapsed.seconds % 60
                    hundredths = int(elapsed.microseconds / 10000)
                    
                    clip_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{hundredths:02d}"
                    self.clips.append(clip_duration)
                    
                    # Ограничиваем историю
                    if len(self.clips) > 10:
                        self.clips.pop(0)
                    
                    self.current_clip_start = None
        
        # Оставшееся время (09:02)
        elif category == 0x09 and subcategory == 0x02:
            if "Осталось:" in value_human:
                time_str = value_human.replace("Осталось:", "").strip()
                if ":" in time_str:
                    parts = time_str.split(":")
                    if len(parts) >= 2:
                        minutes = int(parts[0])
                        seconds = int(parts[1])
                        self.remaining_time = f"00:{minutes:02d}:{seconds:02d}:00"
        
        # Выдержка (01:0C)
        elif category == 0x01 and subcategory == 0x0C:
            self.values['shutter'] = value_human.replace('Выдержка: ', '')
        
        # ISO (01:0E)
        elif category == 0x01 and subcategory == 0x0E:
            self.values['iso'] = value_human.replace('ISO ', '')
        
        # Диафрагма (0C:0A)
        elif category == 0x0C and subcategory == 0x0A:
            self.values['aperture'] = value_human.replace('Диафрагма: ', '')
        
        # Зум (0C:0B)
        elif category == 0x0C and subcategory == 0x0B:
            self.values['zoom'] = value_human.replace('Зум: ', '')
        
        # Фокус (0C:0C)
        elif category == 0x0C and subcategory == 0x0C:
            self.values['focus'] = value_human.replace('Фокус: ', '')
        
        # Название объектива (0C:09)
        elif category == 0x0C and subcategory == 0x09:
            self.values['lens'] = value_human.replace('Объектив: ', '')

async def keyboard_handler(monitor):
    """Обработчик клавиатуры"""
    while True:
        try:
            await asyncio.sleep(0.05)
            
            if sys.platform == 'win32':
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                else:
                    continue
            else:
                import select
                if select.select([sys.stdin], [], [], 0)[0]:
                    key = sys.stdin.read(1).lower()
                else:
                    continue
            
            if key == 'q':
                print("\n🛑 Stopping...")
                return True
            elif key == 'r':
                monitor.show_raw = not monitor.show_raw
                status = "ON" if monitor.show_raw else "OFF"
                print(f"\n📊 Raw data: {status}")
            elif key == 'p':
                monitor.paused = not monitor.paused
                status = "⏸️ PAUSED" if monitor.paused else "▶️ RESUMED"
                print(f"\n{status}")
            elif key == 'c':
                monitor.clear_screen()
                print("\n🧹 Screen cleared")
            elif key == 'f':
                print("\n🎯 FPS toggle not implemented yet")
            
        except Exception:
            continue

async def main():
    """Основная функция"""
    monitor = CameraMonitor()
    
    print("=" * 62)
    print("🎬 BLACKMAGIC CAMERA MONITOR v4.0")
    print("=" * 62)
    print(f"Camera: {CAMERA_ADDRESS[:17]}...")
    print(f"Start: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 62)
    
    try:
        async with BleakClient(
            CAMERA_ADDRESS, 
            timeout=20.0,
            pair_before_connect=False
        ) as client:
            monitor.is_connected = True
            
            def handle_notification(sender, data):
                """Обработчик уведомлений от камеры"""
                try:
                    parsed = parse_bmpcc_message(data)
                    monitor.handle_message(parsed, data)
                except Exception:
                    pass
            
            # Подписываемся на оба канала
            await client.start_notify(UUID_NOTIFICATIONS, handle_notification)
            await client.start_notify(UUID_TELEMETRY, handle_notification)
            
            print("✅ Connected to camera!")
            print("📡 Receiving data...")
            
            await asyncio.sleep(1)
            
            # Запускаем обработчик клавиатуры
            keyboard_task = asyncio.create_task(keyboard_handler(monitor))
            
            # Основной цикл обновления
            try:
                while True:
                    if not monitor.paused:
                        monitor.draw_dashboard()
                    
                    if keyboard_task.done():
                        if keyboard_task.result():
                            break
                    
                    await asyncio.sleep(REFRESH_RATE)
                    
            except KeyboardInterrupt:
                print("\n\n⏹️ Interrupted (Ctrl+C)")
            
            await client.stop_notify(UUID_NOTIFICATIONS)
            await client.stop_notify(UUID_TELEMETRY)
            
    except Exception as e:
        print(f"\n❌ Connection error: {e}")
        monitor.is_connected = False
        monitor.draw_dashboard()
    
    # Финальная статистика
    print("\n" + "=" * 62)
    print("📊 SESSION SUMMARY:")
    print(f"   Duration: {datetime.now() - monitor.start_time}")
    print(f"   Messages: {monitor.message_count}")
    print(f"   Clips: {len(monitor.clips)}")
    print("=" * 62)
    print("🎬 Monitor stopped")
    print("=" * 62)

if __name__ == "__main__":
    if sys.platform != 'win32':
        import tty, termios
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 User exit")
    except Exception as e:
        print(f"\n⚠️ Unexpected error: {e}")
    finally:
        if sys.platform != 'win32':
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)