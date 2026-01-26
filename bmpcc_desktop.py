#!/usr/bin/env python3
"""
BLACKMAGIC CAMERA DESKTOP CONTROLLER
Объединяем веб-интерфейс с Bluetooth подключением
"""

import asyncio
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
from bleak import BleakClient, BleakScanner

class BMPCCDesktopController:
    def __init__(self, root):
        self.root = root
        self.root.title("Blackmagic Camera Desktop Control")
        self.root.geometry("1000x700")
        
        # Настройки Bluetooth
        self.camera_address = "E7D0FD32-5393-2B54-61EE-F21174E0D7B0"
        self.COMMAND_UUID = "5dd3465f-1aee-4299-8493-d2eca2f8e1bb"
        
        # Команды из веб-приложения (переведем в HEX позже)
        self.COMMANDS = {
            # Транспорт
            'record_start': "/transports/0/record",
            'record_stop': "/transports/0/record",
            
            # Видео настройки
            'iso': "/video/iso",
            'white_balance': "/video/whiteBalance",
            'shutter': "/video/shutterAngle",
            'iris': "/video/iris",
            
            # Объектив
            'focus': "/lens/focus",
            'aperture': "/lens/aperture",
            
            # Таймлапс
            'timelapse': "/mode"  # предположительно
        }
        
        # HEX команды из вашего старого кода
        self.HEX_COMMANDS = {
            'stop': "ff0a00000a010102000040000103",
            'timelapse_hex': "ff0a00000a010102000080000103",
            'video_mode': "ff0a00000a010102000002000103",
            'record_start_hex': "ff0a00000a010102000010000103",
        }
        
        # Для управления
        self.client = None
        self.is_connected = False
        self.event_loop = None
        self.loop_thread = None
        
        # Данные камеры (как в веб-приложении)
        self.camera_data = {
            'recording': False,
            'battery': 0,
            'temperature': 0,
            'iso': 800,
            'white_balance': 5600,
            'shutter_angle': 180,
            'iris': 2.8,
            'focus': 50,
            'model': "Unknown"
        }
        
        # Запускаем event loop
        self.start_event_loop()
        
        # Создаем интерфейс как в веб-приложении
        self.create_widgets()
        
        # Лог
        self.log("=" * 60)
        self.log("Blackmagic Camera Desktop Controller")
        self.log("Bluetooth версия")
        self.log("=" * 60)
    
    def log(self, message):
        """Логирование"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        if hasattr(self, 'log_text'):
            self.log_text.insert(tk.END, log_entry + "\n")
            self.log_text.see(tk.END)
    
    def start_event_loop(self):
        """Запуск event loop для асинхронности"""
        self.event_loop = asyncio.new_event_loop()
        
        def run_loop():
            asyncio.set_event_loop(self.event_loop)
            self.event_loop.run_forever()
        
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
    
    def run_async(self, coro):
        """Запуск асинхронной функции"""
        return asyncio.run_coroutine_threadsafe(coro, self.event_loop)
    
    def create_widgets(self):
        """Создаем интерфейс как в веб-приложении"""
        # Главный контейнер
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # === ЛЕВАЯ ПАНЕЛЬ: Управление ===
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 1. Панель подключения
        connection_frame = ttk.LabelFrame(left_panel, text="Подключение", padding="10")
        connection_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Статус
        self.status_label = ttk.Label(
            connection_frame,
            text="❌ Не подключено",
            font=("Arial", 11),
            foreground="red"
        )
        self.status_label.pack(anchor=tk.W, pady=5)
        
        # Инфо о камере
        self.camera_info = ttk.Label(
            connection_frame,
            text="Камера не найдена",
            font=("Arial", 9)
        )
        self.camera_info.pack(anchor=tk.W, pady=2)
        
        # Кнопки подключения
        btn_frame = ttk.Frame(connection_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            btn_frame,
            text="🔍 Найти камеру",
            command=self.scan_cameras,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame,
            text="🔌 Подключиться",
            command=self.connect_to_camera,
            width=15,
            state="disabled"
        ).pack(side=tk.LEFT, padx=5)
        self.connect_btn = btn_frame.winfo_children()[-1]
        
        ttk.Button(
            btn_frame,
            text="🔓 Отключиться",
            command=self.disconnect_camera,
            width=15,
            state="disabled"
        ).pack(side=tk.LEFT, padx=5)
        self.disconnect_btn = btn_frame.winfo_children()[-1]
        
        # 2. Транспорт (Запись) - как в веб-интерфейсе
        transport_frame = ttk.LabelFrame(left_panel, text="Транспорт", padding="10")
        transport_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Большие кнопки записи
        record_btn_frame = ttk.Frame(transport_frame)
        record_btn_frame.pack(pady=10)
        
        self.record_start_btn = ttk.Button(
            record_btn_frame,
            text="▶ НАЧАТЬ ЗАПИСЬ",
            command=self.start_recording,
            width=20,
            state="disabled"
        )
        self.record_start_btn.pack(side=tk.LEFT, padx=10)
        
        self.record_stop_btn = ttk.Button(
            record_btn_frame,
            text="⏹ ОСТАНОВИТЬ",
            command=self.stop_recording,
            width=20,
            state="disabled"
        )
        self.record_stop_btn.pack(side=tk.LEFT, padx=10)
        
        # Индикатор записи
        self.record_indicator = tk.Label(
            transport_frame,
            text="●",
            font=("Arial", 24),
            fg="gray"
        )
        self.record_indicator.pack(pady=5)
        
        # 3. Видео настройки - как в веб-интерфейсе
        video_frame = ttk.LabelFrame(left_panel, text="Видео", padding="10")
        video_frame.pack(fill=tk.X, pady=(0, 10))
        
        # ISO
        iso_frame = ttk.Frame(video_frame)
        iso_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(iso_frame, text="ISO:", width=10).pack(side=tk.LEFT)
        
        self.iso_var = tk.StringVar(value="800")
        iso_values = ["100", "200", "400", "800", "1600", "3200", "6400"]
        self.iso_combo = ttk.Combobox(
            iso_frame,
            textvariable=self.iso_var,
            values=iso_values,
            state="readonly",
            width=15
        )
        self.iso_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            iso_frame,
            text="Установить",
            command=self.set_iso,
            state="disabled",
            width=10
        ).pack(side=tk.LEFT)
        self.iso_btn = iso_frame.winfo_children()[-1]
        
        # Баланс белого
        wb_frame = ttk.Frame(video_frame)
        wb_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(wb_frame, text="Баланс белого:", width=10).pack(side=tk.LEFT)
        
        self.wb_var = tk.StringVar(value="5600")
        wb_values = ["3200", "4500", "5600", "6500", "7500"]
        self.wb_combo = ttk.Combobox(
            wb_frame,
            textvariable=self.wb_var,
            values=wb_values,
            state="readonly",
            width=15
        )
        self.wb_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            wb_frame,
            text="Установить",
            command=self.set_white_balance,
            state="disabled",
            width=10
        ).pack(side=tk.LEFT)
        self.wb_btn = wb_frame.winfo_children()[-1]
        
        # 4. Таймлапс
        timelapse_frame = ttk.LabelFrame(left_panel, text="Таймлапс", padding="10")
        timelapse_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(
            timelapse_frame,
            text="⏱️ Включить таймлапс",
            command=self.enable_timelapse,
            state="disabled",
            width=20
        ).pack(pady=5)
        self.timelapse_btn = timelapse_frame.winfo_children()[-1]
        
        ttk.Button(
            timelapse_frame,
            text="⏱️→STOP (5 секунд)",
            command=self.quick_timelapse,
            state="disabled",
            width=20
        ).pack(pady=5)
        self.quick_timelapse_btn = timelapse_frame.winfo_children()[-1]
        
        # === ПРАВАЯ ПАНЕЛЬ: Информация и лог ===
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # 5. Информация о камере
        info_frame = ttk.LabelFrame(right_panel, text="Информация о камере", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.info_text = tk.Text(
            info_frame,
            height=8,
            width=40,
            font=("Monaco", 9),
            bg="#f0f0f0"
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
        # Начальная информация
        self.update_camera_info()
        
        # 6. Лог
        log_frame = ttk.LabelFrame(right_panel, text="Лог", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            font=("Monaco", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Кнопки управления логом
        log_buttons = ttk.Frame(log_frame)
        log_buttons.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(
            log_buttons,
            text="📋 Копировать лог",
            command=self.copy_log,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            log_buttons,
            text="🧹 Очистить",
            command=self.clear_log,
            width=15
        ).pack(side=tk.LEFT, padx=5)
    
    def update_ui_state(self, connected):
        """Обновить состояние интерфейса"""
        self.is_connected = connected
        
        if connected:
            self.status_label.config(text="✅ Подключено", foreground="green")
            self.camera_info.config(text=f"Камера: {self.camera_data['model']}")
            
            # Включаем кнопки
            self.connect_btn.config(state="disabled")
            self.disconnect_btn.config(state="normal")
            self.record_start_btn.config(state="normal")
            self.record_stop_btn.config(state="normal")
            self.iso_btn.config(state="normal")
            self.wb_btn.config(state="normal")
            self.timelapse_btn.config(state="normal")
            self.quick_timelapse_btn.config(state="normal")
            
        else:
            self.status_label.config(text="❌ Не подключено", foreground="red")
            self.camera_info.config(text="Камера не найдена")
            
            # Отключаем кнопки
            self.connect_btn.config(state="disabled")
            self.disconnect_btn.config(state="disabled")
            self.record_start_btn.config(state="disabled")
            self.record_stop_btn.config(state="disabled")
            self.iso_btn.config(state="disabled")
            self.wb_btn.config(state="disabled")
            self.timelapse_btn.config(state="disabled")
            self.quick_timelapse_btn.config(state="disabled")
    
    def update_camera_info(self):
        """Обновить информацию о камере"""
        info = f"""Модель: {self.camera_data['model']}
Состояние: {'Запись' if self.camera_data['recording'] else 'Ожидание'}
Батарея: {self.camera_data['battery']}%
Температура: {self.camera_data['temperature']}°C
ISO: {self.camera_data['iso']}
Баланс белого: {self.camera_data['white_balance']}K
Диафрагма: f/{self.camera_data['iris']}
Выдержка: 1/{self.camera_data['shutter_angle']}"""
        
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info)
    
    # === BLUETOOTH МЕТОДЫ ===
    
    async def scan_async(self):
        """Поиск камер"""
        self.log("🔍 Поиск Bluetooth устройств...")
        devices = await BleakScanner.discover()
        
        cameras = []
        for device in devices:
            if "Blackmagic" in str(device.name) or "BMPCC" in str(device.name):
                cameras.append(device)
                self.log(f"  Найдена: {device.name} - {device.address}")
        
        return cameras
    
    async def connect_async(self):
        """Подключение к камере"""
        try:
            self.log(f"Подключаюсь к {self.camera_address}...")
            self.client = BleakClient(self.camera_address)
            await self.client.connect(timeout=10.0)
            
            if self.client.is_connected:
                # Пробуем получить информацию о камере
                try:
                    # Читаем характеристики
                    services = await self.client.get_services()
                    self.log(f"Услуги: {len(services.services)} найдено")
                    
                    # Предполагаем что это BMPCC 6K G2
                    self.camera_data['model'] = "BMPCC 6K G2"
                    
                except Exception as e:
                    self.log(f"⚠️ Не удалось получить данные: {e}")
                    self.camera_data['model'] = "Blackmagic Camera"
                
                self.log("✅ Подключение успешно!")
                return True
                
        except Exception as e:
            self.log(f"❌ Ошибка подключения: {str(e)[:100]}")
        
        return False
    
    async def send_hex_command_async(self, hex_command, description=""):
        """Отправить HEX команду"""
        if not self.client or not self.client.is_connected:
            self.log("❌ Не подключено к камере")
            return False
        
        try:
            self.log(f"📤 Отправка: {description}")
            
            cmd_bytes = bytes.fromhex(hex_command)
            await self.client.write_gatt_char(self.COMMAND_UUID, cmd_bytes, response=True)
            
            self.log("✅ Команда отправлена")
            return True
            
        except Exception as e:
            self.log(f"❌ Ошибка отправки: {str(e)[:100]}")
            return False
    
    async def disconnect_async(self):
        """Отключиться"""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            return True
        return False
    
    # === UI ОБЕРТКИ ===
    
    def scan_cameras(self):
        """Поиск камер"""
        def scan():
            future = self.run_async(self.scan_async())
            try:
                cameras = future.result(timeout=30)
                if cameras:
                    self.log(f"Найдено {len(cameras)} камер")
                    # Разрешаем подключение
                    self.root.after(0, self.connect_btn.config, {"state": "normal"})
                else:
                    self.log("Камеры не найдены")
                    messagebox.showwarning("Не найдено", 
                        "Blackmagic камеры не найдены.\n"
                        "Убедитесь что:\n"
                        "1. Камера включена\n"
                        "2. Bluetooth включен\n"
                        "3. Камера рядом с компьютером")
                    
            except Exception as e:
                self.log(f"❌ Ошибка поиска: {str(e)[:100]}")
        
        threading.Thread(target=scan, daemon=True).start()
    
    def connect_to_camera(self):
        """Подключиться к камере"""
        def connect():
            future = self.run_async(self.connect_async())
            try:
                success = future.result(timeout=15)
                if success:
                    self.root.after(0, self.update_ui_state, True)
                    self.root.after(0, self.update_camera_info)
            except Exception as e:
                self.log(f"❌ Ошибка: {str(e)[:100]}")
        
        threading.Thread(target=connect, daemon=True).start()
    
    def disconnect_camera(self):
        """Отключиться от камеры"""
        def disconnect():
            future = self.run_async(self.disconnect_async())
            try:
                success = future.result(timeout=5)
                if success:
                    self.root.after(0, self.update_ui_state, False)
                    self.log("🔌 Отключено от камеры")
            except Exception as e:
                self.log(f"❌ Ошибка отключения: {str(e)[:100]}")
        
        threading.Thread(target=disconnect, daemon=True).start()
    
    # === КОМАНДЫ КАМЕРЫ ===
    
    def start_recording(self):
        """Начать запись (команда 10)"""
        def execute():
            self.log("--- НАЧАТЬ ЗАПИСЬ ---")
            
            # Сначала STOP для безопасности
            future_stop = self.run_async(
                self.send_hex_command_async(
                    self.HEX_COMMANDS['stop'],
                    "Предварительный STOP"
                )
            )
            
            try:
                future_stop.result(timeout=5)
                time.sleep(1)
                
                # Запуск записи (команда 10)
                future_record = self.run_async(
                    self.send_hex_command_async(
                        self.HEX_COMMANDS['record_start_hex'],
                        "Запуск записи"
                    )
                )
                future_record.result(timeout=10)
                
                self.camera_data['recording'] = True
                self.root.after(0, self.record_indicator.config, {"fg": "red"})
                self.root.after(0, self.update_camera_info)
                self.log("✅ Запись начата")
                
            except Exception as e:
                self.log(f"❌ Ошибка: {str(e)[:100]}")
        
        threading.Thread(target=execute, daemon=True).start()
    
    def stop_recording(self):
        """Остановить запись (команда STOP)"""
        def execute():
            self.log("--- ОСТАНОВИТЬ ЗАПИСЬ ---")
            
            future = self.run_async(
                self.send_hex_command_async(
                    self.HEX_COMMANDS['stop'],
                    "Остановка записи"
                )
            )
            
            try:
                future.result(timeout=10)
                self.camera_data['recording'] = False
                self.root.after(0, self.record_indicator.config, {"fg": "gray"})
                self.root.after(0, self.update_camera_info)
                self.log("✅ Запись остановлена")
                
            except Exception as e:
                self.log(f"❌ Ошибка: {str(e)[:100]}")
        
        threading.Thread(target=execute, daemon=True).start()
    
    def set_iso(self):
        """Установить ISO"""
        # TODO: Нужно найти HEX команду для ISO
        iso_value = self.iso_var.get()
        self.log(f"ISO установлен на {iso_value} (заглушка)")
        self.camera_data['iso'] = int(iso_value)
        self.update_camera_info()
    
    def set_white_balance(self):
        """Установить баланс белого"""
        # TODO: Нужно найти HEX команду для баланса белого
        wb_value = self.wb_var.get()
        self.log(f"Баланс белого установлен на {wb_value}K (заглушка)")
        self.camera_data['white_balance'] = int(wb_value)
        self.update_camera_info()
    
    def enable_timelapse(self):
        """Включить таймлапс"""
        def execute():
            self.log("--- ВКЛЮЧИТЬ ТАЙМЛАПС ---")
            
            # STOP
            future_stop = self.run_async(
                self.send_hex_command_async(
                    self.HEX_COMMANDS['stop'],
                    "Остановка перед таймлапсом"
                )
            )
            
            try:
                future_stop.result(timeout=5)
                time.sleep(2)
                
                # Таймлапс
                future_tl = self.run_async(
                    self.send_hex_command_async(
                        self.HEX_COMMANDS['timelapse_hex'],
                        "Запуск таймлапса"
                    )
                )
                future_tl.result(timeout=10)
                
                self.log("✅ Таймлапс включен")
                
            except Exception as e:
                self.log(f"❌ Ошибка: {str(e)[:100]}")
        
        threading.Thread(target=execute, daemon=True).start()
    
    def quick_timelapse(self):
        """Быстрый таймлапс на 5 секунд"""
        def execute():
            self.log("--- БЫСТРЫЙ ТАЙМЛАПС (5 сек) ---")
            
            # STOP
            future_stop = self.run_async(
                self.send_hex_command_async(
                    self.HEX_COMMANDS['stop'],
                    "Остановка"
                )
            )
            
            try:
                future_stop.result(timeout=5)
                time.sleep(1)
                
                # Таймлапс
                future_tl = self.run_async(
                    self.send_hex_command_async(
                        self.HEX_COMMANDS['timelapse_hex'],
                        "Таймлапс"
                    )
                )
                future_tl.result(timeout=10)
                
                self.log("Таймлапс работает... (5 секунд)")
                time.sleep(5)
                
                # STOP
                future_stop2 = self.run_async(
                    self.send_hex_command_async(
                        self.HEX_COMMANDS['stop'],
                        "Остановка таймлапса"
                    )
                )
                future_stop2.result(timeout=5)
                
                self.log("✅ Таймлапс завершен")
                
            except Exception as e:
                self.log(f"❌ Ошибка: {str(e)[:100]}")
        
        threading.Thread(target=execute, daemon=True).start()
    
    def copy_log(self):
        """Копировать лог"""
        try:
            log_content = self.log_text.get(1.0, tk.END)
            if log_content.strip():
                self.root.clipboard_clear()
                self.root.clipboard_append(log_content)
                self.log("📋 Лог скопирован в буфер")
            else:
                self.log("📋 Лог пуст")
        except Exception as e:
            self.log(f"❌ Ошибка копирования: {e}")
    
    def clear_log(self):
        """Очистить лог"""
        self.log_text.delete(1.0, tk.END)
        self.log("🧹 Лог очищен")
    
    def on_closing(self):
        """Закрытие программы"""
        try:
            if self.client and self.client.is_connected:
                future = self.run_async(self.disconnect_async())
                future.result(timeout=3)
        except:
            pass
        
        if self.event_loop and self.event_loop.is_running():
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        
        self.root.destroy()

def main():
    root = tk.Tk()
    
    # Центрирование окна
    root.update_idletasks()
    width = 1000
    height = 700
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    app = BMPCCDesktopController(root)
    
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    print("=" * 60)
    print("Blackmagic Camera Desktop Controller")
    print("Bluetooth версия")
    print("=" * 60)
    print("Установите зависимости: pip install bleak")
    print("=" * 60)
    
    # Проверяем bleak
    try:
        import bleak
    except ImportError:
        print("❌ Библиотека 'bleak' не установлена!")
        print("Установите: pip install bleak")
        print("Или запустите: python3 -m pip install bleak")
        exit(1)
    
    main()