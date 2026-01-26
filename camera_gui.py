# ==============================
# ФАЙЛ 2: camera_gui.py
# Простой графический интерфейс
# ==============================

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# Добавляем текущую папку в путь, чтобы найти наш модуль
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from camera_core import BlackmagicCamera
except ImportError:
    print("Ошибка: Не найден файл camera_core.py")
    print("Убедитесь что оба файла в одной папке!")
    sys.exit(1)

class CameraControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Управление Blackmagic камерой")
        self.root.geometry("500x600")
        
        # Устанавливаем иконку (если есть)
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # Создаем объект камеры
        self.camera = None
        
        # Создаем интерфейс
        self.setup_ui()
        
        # Центрируем окно
        self.center_window()
    
    def center_window(self):
        """Центрирование окна на экране"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        """Создание всех элементов интерфейса"""
        
        # ========== РАМКА ПОДКЛЮЧЕНИЯ ==========
        conn_frame = ttk.LabelFrame(self.root, text="Подключение к камере", padding="15")
        conn_frame.pack(fill="x", padx=10, pady=10)
        
        # Метка и поле для имени камеры
        ttk.Label(conn_frame, text="Имя камеры в сети:").grid(row=0, column=0, sticky="w", pady=5)
        
        self.hostname_var = tk.StringVar(value="Pocket-Cinema-Camera-6K-Pro.local")
        self.hostname_entry = ttk.Entry(conn_frame, textvariable=self.hostname_var, width=40)
        self.hostname_entry.grid(row=1, column=0, sticky="we", pady=5)
        
        # Кнопка подключения
        self.connect_btn = ttk.Button(
            conn_frame, 
            text="ПОДКЛЮЧИТЬСЯ", 
            command=self.connect_to_camera,
            width=20
        )
        self.connect_btn.grid(row=1, column=1, padx=10)
        
        # Статус подключения
        self.status_label = ttk.Label(conn_frame, text="❌ Не подключено", foreground="red")
        self.status_label.grid(row=2, column=0, sticky="w", pady=10)
        
        # ========== РАМКА УПРАВЛЕНИЯ ЗАПИСЬЮ ==========
        record_frame = ttk.LabelFrame(self.root, text="Управление записью", padding="15")
        record_frame.pack(fill="x", padx=10, pady=10)
        
        # Кнопки записи
        self.record_start_btn = ttk.Button(
            record_frame,
            text="▶ НАЧАТЬ ЗАПИСЬ",
            command=self.start_recording,
            width=25,
            state="disabled"
        )
        self.record_start_btn.pack(side=tk.LEFT, padx=5)
        
        self.record_stop_btn = ttk.Button(
            record_frame,
            text="⏹ ОСТАНОВИТЬ ЗАПИСЬ",
            command=self.stop_recording,
            width=25,
            state="disabled"
        )
        self.record_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Индикатор записи
        self.record_indicator = tk.Label(record_frame, text="●", font=("Arial", 24), fg="gray")
        self.record_indicator.pack(side=tk.LEFT, padx=20)
        
        # ========== РАМКА НАСТРОЕК КАМЕРЫ ==========
        settings_frame = ttk.LabelFrame(self.root, text="Настройки камеры", padding="15")
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        # ISO
        ttk.Label(settings_frame, text="ISO (чувствительность):").grid(row=0, column=0, sticky="w", pady=5)
        
        self.iso_var = tk.IntVar(value=800)
        self.iso_combobox = ttk.Combobox(
            settings_frame,
            textvariable=self.iso_var,
            values=[100, 200, 400, 800, 1600, 3200, 6400],
            state="readonly",
            width=15
        )
        self.iso_combobox.grid(row=0, column=1, padx=10, pady=5)
        
        self.iso_btn = ttk.Button(
            settings_frame,
            text="Установить ISO",
            command=self.set_iso,
            state="disabled"
        )
        self.iso_btn.grid(row=0, column=2, padx=5)
        
        # Баланс белого
        ttk.Label(settings_frame, text="Баланс белого (K):").grid(row=1, column=0, sticky="w", pady=5)
        
        self.wb_var = tk.IntVar(value=5600)
        self.wb_combobox = ttk.Combobox(
            settings_frame,
            textvariable=self.wb_var,
            values=[3200, 4000, 4500, 5000, 5600, 6500, 7500],
            state="readonly",
            width=15
        )
        self.wb_combobox.grid(row=1, column=1, padx=10, pady=5)
        
        self.wb_btn = ttk.Button(
            settings_frame,
            text="Установить баланс",
            command=self.set_white_balance,
            state="disabled"
        )
        self.wb_btn.grid(row=1, column=2, padx=5)
        
        # ========== ИНФОРМАЦИОННАЯ РАМКА ==========
        info_frame = ttk.LabelFrame(self.root, text="Информация", padding="15")
        info_frame.pack(fill="x", padx=10, pady=10)
        
        self.info_text = tk.Text(info_frame, height=6, width=50)
        self.info_text.pack(fill="x")
        
        # Добавляем начальный текст
        self.log_message("Добро пожаловать в Blackmagic Camera Controller!")
        self.log_message("1. Введите имя вашей камеры")
        self.log_message("2. Нажмите 'ПОДКЛЮЧИТЬСЯ'")
        self.log_message("3. Управляйте камерой с помощью кнопок")
        
        # ========== КНОПКА ВЫХОДА ==========
        ttk.Button(
            self.root,
            text="ВЫЙТИ",
            command=self.root.quit,
            width=20
        ).pack(pady=20)
    
    def log_message(self, message):
        """Добавление сообщения в информационное окно"""
        self.info_text.insert(tk.END, f"> {message}\n")
        self.info_text.see(tk.END)
    
    def enable_controls(self, enabled):
        """Включение или отключение элементов управления"""
        state = "normal" if enabled else "disabled"
        self.record_start_btn.config(state=state)
        self.record_stop_btn.config(state=state)
        self.iso_btn.config(state=state)
        self.wb_btn.config(state=state)
    
    def connect_to_camera(self):
        """Подключение к камере"""
        hostname = self.hostname_var.get().strip()
        
        if not hostname:
            messagebox.showerror("Ошибка", "Введите имя камеры!")
            return
        
        self.connect_btn.config(state="disabled", text="Подключаемся...")
        self.log_message(f"Пробуем подключиться к {hostname}...")
        
        # Создаем объект камеры
        self.camera = BlackmagicCamera(hostname)
        
        # Пробуем подключиться
        if self.camera.test_connection():
            self.status_label.config(text="✓ Подключено", foreground="green")
            self.enable_controls(True)
            self.log_message("✓ Успешное подключение!")
            self.log_message("Камера готова к управлению!")
            
            # Обновляем значения из камеры
            self.update_camera_values()
        else:
            self.status_label.config(text="❌ Ошибка подключения", foreground="red")
            self.log_message("✗ Не удалось подключиться к камере")
            self.log_message("Проверьте:")
            self.log_message("1. Имя камеры")
            self.log_message("2. Подключение к сети")
            self.log_message("3. Включена ли камера")
        
        self.connect_btn.config(state="normal", text="ПОДКЛЮЧИТЬСЯ")
    
    def update_camera_values(self):
        """Обновление значений интерфейса из камеры"""
        if self.camera and self.camera.connected:
            # Здесь можно добавить получение реальных значений
            pass
    
    def start_recording(self):
        """Начать запись"""
        if not self.camera:
            return
            
        self.log_message("Отправляем команду: Начать запись...")
        
        result = self.camera.start_recording()
        if result:
            self.record_indicator.config(fg="red")
            self.log_message("✓ Запись начата!")
        else:
            self.log_message("✗ Ошибка при старте записи")
    
    def stop_recording(self):
        """Остановить запись"""
        if not self.camera:
            return
            
        self.log_message("Отправляем команду: Остановить запись...")
        
        result = self.camera.stop_recording()
        if result:
            self.record_indicator.config(fg="gray")
            self.log_message("✓ Запись остановлена")
        else:
            self.log_message("✗ Ошибка при остановке записи")
    
    def set_iso(self):
        """Установить ISO"""
        if not self.camera:
            return
            
        iso_value = self.iso_var.get()
        self.log_message(f"Устанавливаем ISO = {iso_value}...")
        
        result = self.camera.set_iso(iso_value)
        if result:
            self.log_message(f"✓ ISO установлен на {iso_value}")
        else:
            self.log_message("✗ Ошибка установки ISO")
    
    def set_white_balance(self):
        """Установить баланс белого"""
        if not self.camera:
            return
            
        wb_value = self.wb_var.get()
        self.log_message(f"Устанавливаем баланс белого = {wb_value}K...")
        
        result = self.camera.set_white_balance(wb_value)
        if result:
            self.log_message(f"✓ Баланс белого установлен на {wb_value}K")
        else:
            self.log_message("✗ Ошибка установки баланса белого")

# ================= ЗАПУСК ПРОГРАММЫ =================
if __name__ == "__main__":
    # Создаем главное окно
    root = tk.Tk()
    
    # Создаем приложение
    app = CameraControlApp(root)
    
    # Запускаем главный цикл
    root.mainloop()