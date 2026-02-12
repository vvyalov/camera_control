# core/camera_controller.py
"""
🎬 КОНТРОЛЛЕР КАМЕРЫ ДЛЯ GUI
Объединяет main_monitor.py и camera_interface.py
"""

import asyncio
import threading
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from bleak import BleakClient

# Импортируем ваши модули
from protocols.bm import (
    parse_bmpcc_message,
    UUID_NOTIFICATIONS,
    UUID_TELEMETRY,
    UUID_TIMECODE,
    UUID_WRITE_CHAR,
    decode_timecode_bcd,
    decode_frame_rate_resolution,
    decode_recording_time_remaining,
    decode_transport_mode,
    decode_codec,
    decode_white_balance,
    decode_dynamic_range,
    decode_shutter,
    decode_iso,
    decode_aperture_text,
    decode_lens_name,
    decode_focal_length,
    decode_recording_status,
    decode_nd_filter,
    decode_display_lut
)

class CameraController:
    """Контроллер камеры для GUI с полной поддержкой протокола Blackmagic"""
    
    def __init__(self):
        # ============ СОСТОЯНИЕ КАМЕРЫ ============
        self.address = None
        self.client = None
        self.connected = False
        self.connection_thread = None
        self.loop = None
        
        # ============ ДАННЫЕ ИЗ MAIN_MONITOR ============
        
        # Таймкод и время
        self.timecode = {
            'free_tc': "00:00:00:00",
            'clip_tc': "00:00:00:00",
            'display_tc': "00:00:00:00",
            'fps': 25,
            'tc_source': "internal",
            'last_tc_update': None
        }
        
        # Настройки видео
        self.video = {
            'shutter': "1/50",
            'shutter_type': "speed",
            'aperture': "f/2.8",
            'iso': "ISO 400",
            'white_balance': 5600,
            'tint': 0,
            'dynamic_range': "Film",
            'display_lut': "Off",
            'nd_filter': "None",
            'video_sharpening': "Off",
            'auto_exposure': "Manual"
        }
        
        # Метаданные объектива
        self.lens = {
            'model': "Sigma 18-35mm f/1.8",
            'focal_length': "18mm",
            'focus_distance': "∞",
            'zoom': "18mm"
        }
        
        # Медиа и запись
        self.media = {
            'codec': "BRAW 8:1",
            'codec_type': "BRAW",
            'codec_quality': "8:1",
            'transport_mode': "preview",
            'transport_speed': 1,
            'slot1_medium': "CFast",
            'slot2_medium': "None",
            'is_recording': False,
            'recording_status': "⚪",
            'recording_duration': "00:00:00:00",
            'remaining_time': "01:23:45:00",
            'remaining_seconds': 5025
        }
        
        # Разрешение
        self.resolution = "1920x1080"
        self.resolution_width = 1920
        self.resolution_height = 1080
        
        # История клипов
        self.clip_history = []
        self.next_clip_number = 1
        self.record_start_time = None
        self.last_frame_time = None
        
        # Статистика
        self.message_count = 0
        self.start_time = datetime.now()
        
        # ============ КОЛБЭКИ ДЛЯ GUI ============
        self.on_connected = None
        self.on_disconnected = None
        self.on_data_update = None
        self.on_recording_change = None
        self.on_timecode_update = None
        
    # ============ УПРАВЛЕНИЕ ПОДКЛЮЧЕНИЕМ ============
    
    def connect(self, address: str, callback: Optional[Callable] = None) -> bool:
        """Подключение к камере в отдельном потоке"""
        self.address = address
        self.on_connected = callback
        
        # Создаем поток для asyncio
        self.connection_thread = threading.Thread(target=self._run_async_connection, daemon=True)
        self.connection_thread.start()
        return True
    
    def _run_async_connection(self):
        """Запуск асинхронного подключения в потоке"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._connect_and_monitor())
        except Exception as e:
            print(f"[ERROR] Connection error: {e}")
            self.connected = False
            if self.on_disconnected:
                self.root.after(0, self.on_disconnected)  # Исправлено
        finally:
            self.loop.close()
    
    async def _connect_and_monitor(self):
        """Асинхронное подключение и мониторинг"""
        try:
            async with BleakClient(self.address, timeout=20.0) as client:
                self.client = client
                self.connected = True
                self.start_time = datetime.now()
                
                # Уведомляем GUI о подключении
                if self.on_connected:
                    self.on_connected()
                
                # Настраиваем обработчик уведомлений
                def handle_notification(sender, data):
                    try:
                        parsed = parse_bmpcc_message(data)
                        self._process_camera_message(parsed, data)
                    except Exception as e:
                        print(f"[ERROR] Failed to parse: {e}")
                
                # Подписываемся на каналы
                try:
                    await client.start_notify(UUID_NOTIFICATIONS, handle_notification)
                    print("✅ Camera data channel subscribed")
                except Exception as e:
                    print(f"⚠️ Camera data channel error: {e}")
                
                try:
                    await client.start_notify(UUID_TELEMETRY, handle_notification)
                    print("✅ Telemetry channel subscribed")
                except Exception as e:
                    print(f"⚠️ Telemetry channel error: {e}")
                
                try:
                    await client.start_notify(UUID_TIMECODE, handle_notification)
                    print("✅ Timecode channel subscribed")
                except:
                    print("ℹ️ Timecode channel not available")
                
                # Отправляем запросы данных
                await self._send_data_requests(client)
                
                # Держим соединение открытым
                while self.connected:
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            print(f"❌ Connection error: {e}")
            self.connected = False
            if self.on_disconnected:
                self.on_disconnected()
    
    async def _send_data_requests(self, client):
        """Отправка запросов данных (как в main_monitor.py)"""
        try:
            # Ищем характеристику для записи
            write_char_uuid = None
            for service in client.services:
                if "291d567a" in service.uuid.lower():
                    for char in service.characteristics:
                        if "5dd3465f" in char.uuid.lower():
                            write_char_uuid = char.uuid
                            break
                    if write_char_uuid:
                        break
            
            if write_char_uuid:
                # Команды запроса из main_monitor.py
                commands = [
                    # FPS + Resolution (01:09)
                    bytes([0xFF, 0x01, 0x00, 0x00, 0x01, 0x09, 0x00, 0x00]),
                    # Transport Mode (0A:01) - статус записи
                    bytes([0xFF, 0x01, 0x00, 0x00, 0x0A, 0x01, 0x00, 0x00]),
                    # White Balance (01:02)
                    bytes([0xFF, 0x01, 0x00, 0x00, 0x01, 0x02, 0x00, 0x00]),
                    # ISO (01:0E)
                    bytes([0xFF, 0x01, 0x00, 0x00, 0x01, 0x0E, 0x00, 0x00]),
                    # Shutter (01:0B или 01:0C)
                    bytes([0xFF, 0x01, 0x00, 0x00, 0x01, 0x0B, 0x00, 0x00]),
                    # Lens Model (0C:09)
                    bytes([0xFF, 0x01, 0x00, 0x00, 0x0C, 0x09, 0x00, 0x00]),
                ]
                
                for cmd in commands:
                    try:
                        await client.write_gatt_char(write_char_uuid, cmd)
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        print(f"⚠️ Error sending command: {e}")
        except Exception as e:
            print(f"⚠️ Failed to send data requests: {e}")
    
    # ============ ОБРАБОТКА ДАННЫХ ИЗ MAIN_MONITOR ============
    
    def _process_camera_message(self, parsed: dict, raw_data: bytes):
        """Обрабатывает сообщение от камеры (скопировано из main_monitor.py)"""
        self.message_count += 1
        
        if parsed.get('type') != 'bmpcc_message':
            return
        
        category = parsed.get('category', 0)
        subcategory = parsed.get('subcategory', 0)
        
        # ============ FPS + РАЗРЕШЕНИЕ (01:09) ============
        if category == 0x01 and subcategory == 0x09:
            if 'fps_data' in parsed:
                fr_data = parsed['fps_data']
                self.timecode['fps'] = fr_data.get('fps', 25)
                self.resolution = fr_data.get('resolution', '1920x1080')
                
                # Парсим разрешение
                if 'x' in self.resolution:
                    w, h = self.resolution.split('x')[0], self.resolution.split('x')[1]
                    self.resolution_width = int(w) if w.isdigit() else 1920
                    self.resolution_height = int(h.split()[0]) if h.split()[0].isdigit() else 1080
        
        # ============ ОСТАВШЕЕСЯ ВРЕМЯ (09:02) ============
        elif category == 0x09 and subcategory == 0x02:
            value = parsed.get('value_human', '')
            if "Осталось:" in value:
                time_str = value.replace("Осталось:", "").strip()
                try:
                    if ':' in time_str:
                        parts = time_str.split(':')
                        if len(parts) == 3:
                            hours, minutes, seconds = map(int, parts)
                            total_seconds = hours * 3600 + minutes * 60 + seconds
                        elif len(parts) == 2:
                            minutes, seconds = map(int, parts)
                            total_seconds = minutes * 60 + seconds
                        else:
                            total_seconds = 0
                        
                        self.media['remaining_seconds'] = total_seconds
                        
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        frames = int((seconds % 1) * self.timecode['fps']) if self.timecode['fps'] > 0 else 0
                        
                        if hours > 0:
                            self.media['remaining_time'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
                        else:
                            self.media['remaining_time'] = f"{minutes:02d}:{seconds:02d}:{frames:02d}"
                except:
                    pass
        
        # ============ СТАТУС ЗАПИСИ (0A:01) ============
        elif category == 0x0A and subcategory == 0x01:
            value = parsed.get('value_human', '')
            old_recording = self.media['is_recording']
            
            if "🔴" in value or "Recording" in value:
                self.media['is_recording'] = True
                self.media['recording_status'] = "🔴"
                
                if not old_recording:
                    self.record_start_time = datetime.now()
                    self.timecode['clip_tc'] = "00:00:00:00"
                    self.last_frame_time = None
                    
                    # Уведомляем GUI
                    if self.on_recording_change:
                        self.on_recording_change(True)
            
            else:
                self.media['is_recording'] = False
                self.media['recording_status'] = "⚪"
                
                if old_recording and self.record_start_time:
                    elapsed = datetime.now() - self.record_start_time
                    hours = elapsed.seconds // 3600
                    minutes = (elapsed.seconds % 3600) // 60
                    seconds = elapsed.seconds % 60
                    frames = int((elapsed.microseconds / 1000000) * self.timecode['fps'])
                    
                    clip_duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
                    
                    self.clip_history.append({
                        "number": self.next_clip_number,
                        "duration": clip_duration,
                        "start_time": self.record_start_time.strftime('%H:%M:%S'),
                        "resolution": self.resolution,
                        "fps": self.timecode['fps'],
                        "codec": self.media['codec']
                    })
                    
                    self.next_clip_number += 1
                    if len(self.clip_history) > 10:
                        self.clip_history.pop(0)
                    
                    self.record_start_time = None
                    self.last_frame_time = None
                    
                    # Уведомляем GUI
                    if self.on_recording_change:
                        self.on_recording_change(False)
        
        # ============ КОДЕК (10:00) ============
        elif category == 0x10 and subcategory == 0x00:
            if 'codec_data' in parsed:
                codec_data = parsed['codec_data']
                self.media['codec_type'] = codec_data.get('codec', 'Unknown')
                self.media['codec_quality'] = codec_data.get('quality', '')
                self.media['codec'] = f"{self.media['codec_type']} {self.media['codec_quality']}".strip()
        
        # ============ РЕЖИМ ТРАНСПОРТА (10:01) ============
        elif category == 0x10 and subcategory == 0x01:
            if 'transport_data' in parsed:
                transport = parsed['transport_data']
                self.media['transport_mode'] = transport.get('mode', 'preview')
                self.media['transport_speed'] = transport.get('speed', 1)
                self.media['slot1_medium'] = transport.get('slot1', 'Unknown')
                self.media['slot2_medium'] = transport.get('slot2', 'Unknown')
        
        # ============ ISO (01:0E) ============
        elif category == 0x01 and subcategory == 0x0E:
            value = parsed.get('value_human', '')
            if "ISO " in value:
                self.video['iso'] = value
        
        # ============ ВЫДЕРЖКА (01:0B или 01:0C) ============
        elif category == 0x01 and subcategory in [0x0B, 0x0C]:
            value = parsed.get('value_human', '')
            if "Shutter:" in value:
                self.video['shutter'] = value.replace('Shutter: ', '')
                self.video['shutter_type'] = "angle" if subcategory == 0x0B else "speed"
        
        # ============ БАЛАНС БЕЛОГО (01:02) ============
        elif category == 0x01 and subcategory == 0x02:
            if 'wb_data' in parsed:
                wb_data = parsed['wb_data']
                self.video['white_balance'] = wb_data.get('wb', 5600)
                self.video['tint'] = wb_data.get('tint', 0)
        
        # ============ ДИНАМИЧЕСКИЙ ДИАПАЗОН (01:07) ============
        elif category == 0x01 and subcategory == 0x07:
            value = parsed.get('value_human', '')
            if "DR:" in value:
                self.video['dynamic_range'] = value.replace('DR: ', '')
        
        # ============ ДИАФРАГМА (0C:0A) ============
        elif category == 0x0C and subcategory == 0x0A:
            value = parsed.get('value_human', '')
            if "Aperture:" in value:
                self.video['aperture'] = value.replace('Aperture: ', '')
        
        # ============ ФОКУСНОЕ РАССТОЯНИЕ (0C:0B) ============
        elif category == 0x0C and subcategory == 0x0B:
            value = parsed.get('value_human', '')
            if "Zoom:" in value:
                self.lens['focal_length'] = value.replace('Zoom: ', '')
                self.lens['zoom'] = self.lens['focal_length']
        
        # ============ МОДЕЛЬ ОБЪЕКТИВА (0C:09) ============
        elif category == 0x0C and subcategory == 0x09:
            value = parsed.get('value_human', '')
            if "Lens:" in value:
                self.lens['model'] = value.replace('Lens: ', '')
        
        # ============ DISPLAY LUT (01:0F) ============
        elif category == 0x01 and subcategory == 0x0F:
            value = parsed.get('value_human', '')
            if "LUT:" in value:
                self.video['display_lut'] = value.replace('LUT: ', '')
        
        # ============ ND FILTER (01:10) ============
        elif category == 0x01 and subcategory == 0x10:
            value = parsed.get('value_human', '')
            if "ND:" in value:
                self.video['nd_filter'] = value.replace('ND: ', '')
        
        # ============ ТАЙМКОД (09:04) ============
        elif category == 0x09 and subcategory == 0x04:
            if 'timecode_data' in parsed:
                tc_data = parsed['timecode_data']
                tc_str = tc_data.get('hhmmssff', '00:00:00:00')
                
                self.timecode['last_tc_update'] = datetime.now()
                
                if self.media['is_recording']:
                    self.timecode['clip_tc'] = tc_str
                else:
                    self.timecode['free_tc'] = tc_str
                
                self.timecode['global_tc'] = tc_str
                self.timecode['tc_source'] = "external"
                
                # Уведомляем GUI
                if self.on_timecode_update:
                    self.on_timecode_update(tc_str)
        
        # ============ ОБНОВЛЯЕМ GUI ============
        self._update_gui()
    
    def _update_gui(self):
        """Обновляет GUI с текущими данными"""
        if self.on_data_update:
            # Собираем все данные в один словарь
            data = {
                'timecode': self.timecode['display_tc'],
                'fps': self.timecode['fps'],
                'resolution': self.resolution,
                'shutter': self.video['shutter'],
                'aperture': self.video['aperture'],
                'iso': self.video['iso'],
                'white_balance': self.video['white_balance'],
                'tint': self.video['tint'],
                'dynamic_range': self.video['dynamic_range'],
                'codec': self.media['codec'],
                'recording': self.media['is_recording'],
                'recording_status': self.media['recording_status'],
                'recording_duration': self.media['recording_duration'],
                'remaining_time': self.media['remaining_time'],
                'lens_model': self.lens['model'],
                'focal_length': self.lens['focal_length'],
                'transport_mode': self.media['transport_mode'],
                'clip_history': self.clip_history[-3:] if self.clip_history else [],
                'message_count': self.message_count,
                'connected': self.connected
            }
            self.on_data_update(data)
    
    # ============ ОТПРАВКА КОМАНД НА КАМЕРУ ============
    
    async def _send_command(self, command: bytes):
        """Отправляет команду на камеру"""
        if not self.client or not self.connected:
            return False
        
        try:
            # Ищем характеристику для записи
            write_char_uuid = None
            for service in self.client.services:
                if "291d567a" in service.uuid.lower():
                    for char in service.characteristics:
                        if "5dd3465f" in char.uuid.lower():
                            write_char_uuid = char.uuid
                            break
                    if write_char_uuid:
                        break
            
            if write_char_uuid:
                await self.client.write_gatt_char(write_char_uuid, command)
                return True
        except Exception as e:
            print(f"[ERROR] Failed to send command: {e}")
        
        return False
    
    def start_recording(self):
        """Начать запись"""
        if self.loop and self.connected:
            # Команда начала записи (нужно уточнить)
            cmd = bytes([0xFF, 0x01, 0x00, 0x00, 0x0A, 0x01, 0x02, 0x00])
            asyncio.run_coroutine_threadsafe(self._send_command(cmd), self.loop)
    
    def stop_recording(self):
        """Остановить запись"""
        if self.loop and self.connected:
            # Команда остановки записи
            cmd = bytes([0xFF, 0x01, 0x00, 0x00, 0x0A, 0x01, 0x00, 0x00])
            asyncio.run_coroutine_threadsafe(self._send_command(cmd), self.loop)
    
    def set_focus(self, value: float):
        """Установить фокус (0.5-2.0)"""
        if self.loop and self.connected:
            # Нормализуем значение (0-65535)
            norm_value = int((value - 0.5) / 1.5 * 65535)
            cmd = bytes([0xFF, 0x02, 0x00, 0x00, 0x00, 0x00, 0x80, 0x00]) + norm_value.to_bytes(4, 'little')
            asyncio.run_coroutine_threadsafe(self._send_command(cmd), self.loop)
    
    def set_zoom(self, value: int):
        """Установить зум (24-70)"""
        if self.loop and self.connected:
            # Нормализуем значение (0-65535)
            norm_value = int((value - 24) / 46 * 65535)
            cmd = bytes([0xFF, 0x02, 0x00, 0x00, 0x00, 0x07, 0x80, 0x00]) + norm_value.to_bytes(4, 'little')
            asyncio.run_coroutine_threadsafe(self._send_command(cmd), self.loop)
    
    def set_iso(self, value: int):
        """Установить ISO"""
        if self.loop and self.connected:
            cmd = bytes([0xFF, 0x02, 0x00, 0x00, 0x01, 0x0E, 0x03, 0x00]) + value.to_bytes(4, 'little')
            asyncio.run_coroutine_threadsafe(self._send_command(cmd), self.loop)
    
    def set_shutter_speed(self, value: int):
        """Установить выдержку (скорость)"""
        if self.loop and self.connected:
            cmd = bytes([0xFF, 0x02, 0x00, 0x00, 0x01, 0x0C, 0x03, 0x00]) + value.to_bytes(4, 'little')
            asyncio.run_coroutine_threadsafe(self._send_command(cmd), self.loop)
    
    def set_aperture(self, value: str):
        """Установить диафрагму (текст)"""
        if self.loop and self.connected:
            # Преобразуем f/2.8 в строку
            aperture_str = value.replace('f/', 'f')
            cmd = bytes([0xFF, 0x02, 0x00, 0x00, 0x0C, 0x0A, 0x05, 0x00]) + aperture_str.encode('ascii')
            asyncio.run_coroutine_threadsafe(self._send_command(cmd), self.loop)
    
    def set_white_balance(self, value: int):
        """Установить баланс белого"""
        if self.loop and self.connected:
            wb_low = value & 0xFF
            wb_high = (value >> 8) & 0xFF
            cmd = bytes([0xFF, 0x04, 0x00, 0x00, 0x01, 0x02, 0x02, 0x00, wb_low, wb_high, 0x00, 0x00])
            asyncio.run_coroutine_threadsafe(self._send_command(cmd), self.loop)
    
    # ============ УПРАВЛЕНИЕ ============
    
    def disconnect(self):
        """Отключение от камеры"""
        self.connected = False
        if self.client and self.loop:
            asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)