import tkinter as tk
from tkinter import ttk
import time
import threading
import os
import sys

# Импорт pygame для управления геймпадом
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Библиотека pygame не установлена. Управление геймпадом недоступно.")
    print("Установите её: pip install pygame")

class CameraControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Управление камерой")
        self.root.geometry("1400x850")
        self.root.configure(bg='#1e1e1e')
        
        # Переменные для хранения значений
        self.fps_value = tk.IntVar(value=30)
        self.shutter_value = tk.IntVar(value=60)
        self.aperture_value = tk.IntVar(value=22)
        self.iso_value = tk.IntVar(value=100)
        self.wb_value = tk.IntVar(value=3200)
        self.tint_value = tk.IntVar(value=0)
        self.focus_value = tk.DoubleVar(value=1.0)
        self.zoom_value = tk.DoubleVar(value=50)
        
        # Текущий активный параметр для слайдера
        self.current_param = None
        self.current_param_var = None
        self.current_min = 0
        self.current_max = 100
        self.current_step = 1
        
        # Переменная для состояния записи
        self.recording = False
        self.recording_time = 0
        self.recording_start_time = 0
        
        # Для управления геймпадом
        self.selected_index = 0
        self.in_slider_mode = False
        self.running = True
        self.menu_selected = 0
        
        # Маппинг кнопок для PS4
        self.BUTTON_MAPPING = {
            'A': 0,
            'B': 1,
            'X': 2,
            'Y': 3,
            'LB': 9,
            'RB': 10,
            'SHARE': 4,
            'OPTIONS': 6,
            'L3': 7,
            'R3': 8,
            'DPAD_UP': 11,
            'DPAD_DOWN': 12,
            'DPAD_LEFT': 13,
            'DPAD_RIGHT': 14,
        }
        
        # Настройки чувствительности
        self.focus_sensitivity = 1.0  # Базовая чувствительность фокуса
        self.zoom_sensitivity = 1.0   # Базовая чувствительность зума
        
        # Состояние геймпада
        self.joystick = None
        self.gamepad_connected = False
        
        # Тайминги для обработки кнопок
        self.last_dpad_left = 0
        self.last_dpad_right = 0
        self.last_dpad_up = 0
        self.last_dpad_down = 0
        self.last_button_A = 0
        self.last_button_B = 0
        self.last_button_X = 0
        self.last_button_Y = 0
        self.last_button_OPTIONS = 0

        # ДОБАВЬТЕ ЭТИ СТРОКИ - тайминги для триггеров и бамперов
        self.last_trigger_LT = 0
        self.last_trigger_RT = 0
        self.last_button_LB = 0
        self.last_button_RB = 0
        
        self.setup_ui()
        self.setup_gamepad()

        # Инициализируем отображение чувствительности
        self.update_sensitivity_display()  # Добавьте эту строку
        
        # Запускаем поток для обработки стиков
        if self.gamepad_connected:
            self.start_gamepad_thread()
        
        # Запускаем проверку кнопок геймпада
        self.root.after(100, self.check_gamepad_buttons)
        
        # Обновление времени записи
        self.update_recording_time()
        
        # Привязка клавиш для эмуляции геймпада
        self.root.bind('<Left>', lambda e: self.gamepad_navigation('left'))
        self.root.bind('<Right>', lambda e: self.gamepad_navigation('right'))
        self.root.bind('<Up>', lambda e: self.gamepad_navigation('up'))
        self.root.bind('<Down>', lambda e: self.gamepad_navigation('down'))
        self.root.bind('<Return>', lambda e: self.gamepad_navigation('enter'))
        self.root.bind('<space>', lambda e: self.gamepad_navigation('enter'))
        self.root.bind('<Escape>', lambda e: self.gamepad_navigation('back'))
        
        # Выделяем первый прямоугольник
        self.highlight_selected()
    
    def setup_ui(self):
        """Настройка интерфейса"""
        # Основной фрейм (горизонтальный)
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Левый фрейм для меню
        self.left_menu_frame = tk.Frame(main_frame, bg='#1a1a1a', width=250)
        self.left_menu_frame.pack(side=tk.LEFT, fill=tk.Y, padx=20, pady=20)
        self.left_menu_frame.pack_propagate(False)
        
        # Заголовок меню
        menu_header = tk.Label(self.left_menu_frame, text="Меню", font=("Arial", 20, "bold"),
                              bg='#1a1a1a', fg='white', pady=30)
        menu_header.pack(fill=tk.X)
        
        # Пункты меню
        self.menu_items = []
        menu_buttons = [
            ("Настройки подключения", lambda: self.menu_action("Настройки подключения")),
            ("Информация о девайсе", lambda: self.menu_action("Информация о девайсе")),
            ("Настройки управления", lambda: self.menu_action("Настройки управления")),
            ("Выход", self.exit_app)
        ]
        
        for text, command in menu_buttons:
            btn = tk.Button(self.left_menu_frame, text=text, font=("Arial", 14),
                          bg='#1a1a1a', fg='white', bd=0, activebackground='#2d2d2d',
                          command=command, anchor='w', padx=20, pady=15)
            btn.pack(fill=tk.X, pady=5)
            self.menu_items.append(btn)
        
        # Правый фрейм для основного контента
        self.right_frame = tk.Frame(main_frame, bg='#1e1e1e')
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Верхняя панель с прямоугольниками
        self.top_frame = tk.Frame(self.right_frame, bg='#1e1e1e', height=200)
        self.top_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 30))
        
        # Контейнер для прямоугольников с сеткой
        self.rect_container = tk.Frame(self.top_frame, bg='#1e1e1e')
        self.rect_container.pack(fill=tk.BOTH, expand=True)
        
        # Создаем 7 прямоугольников
        self.rectangles = []
        self.rect_frames = []
        
        # Названия и параметры прямоугольников
        rect_configs = [
            ("FPS", self.fps_value, 10, 100, 10),
            ("Shutter", self.shutter_value, 10, 100, 10),
            ("T", self.aperture_value, 10, 100, 10),
            ("Запись", None, None, None, None),
            ("ISO", self.iso_value, 10, 100, 10),
            ("WB", self.wb_value, 1000, 6000, 50),
            ("Tint", self.tint_value, -100, 100, 1)
        ]
        
        # Настраиваем столбцы сетки
        for i in range(len(rect_configs)):
            if i == 3:
                self.rect_container.grid_columnconfigure(i, weight=2)
            else:
                self.rect_container.grid_columnconfigure(i, weight=1)
        
        # Создаем фреймы для прямоугольников
        for i, (name, var, min_val, max_val, step) in enumerate(rect_configs):
            frame_container = tk.Frame(self.rect_container, bg='#1e1e1e')
            frame_container.grid(row=0, column=i, padx=5, pady=5, sticky='nsew')
            
            rect_frame = tk.Frame(frame_container, bg='#2d2d2d', relief=tk.RAISED, 
                                 bd=2, highlightbackground='#404040', highlightthickness=1)
            rect_frame.pack(fill=tk.BOTH, expand=True)
            
            if name == "Запись":
                self.setup_recording_rect(rect_frame)
            else:
                self.setup_param_rect(rect_frame, name, var, min_val, max_val, step, i)
            
            self.rectangles.append(rect_frame)
            self.rect_frames.append(frame_container)
        
        # Центральная область для вертикальных слайдеров
        self.center_frame = tk.Frame(self.right_frame, bg='#1e1e1e')
        self.center_frame.pack(fill=tk.BOTH, expand=True, pady=30)
        
        # Контейнер для центрирования слайдеров
        self.slider_container = tk.Frame(self.center_frame, bg='#1e1e1e')
        self.slider_container.place(relx=0.5, rely=0.5, anchor='center')
        
        # Фрейм для двух вертикальных слайдеров
        self.vertical_sliders_frame = tk.Frame(self.slider_container, bg='#1e1e1e')
        self.vertical_sliders_frame.pack()
        
        # Ползунок фокуса
        self.focus_frame = tk.Frame(self.vertical_sliders_frame, bg='#1e1e1e')
        self.focus_frame.pack(side=tk.LEFT, padx=80)
        
        tk.Label(self.focus_frame, text="0.5-2", font=("Arial", 16, "bold"), 
                bg='#1e1e1e', fg='white').pack(pady=(0, 15))
        
        self.focus_slider_frame = tk.Frame(self.focus_frame, bg='#1e1e1e')
        self.focus_slider_frame.pack()
        
        self.focus_vertical_frame = tk.Frame(self.focus_slider_frame, bg='#1e1e1e')
        self.focus_vertical_frame.pack(side=tk.LEFT, padx=15)
        
        self.focus_label = tk.Label(self.focus_vertical_frame, text="1.0", font=("Arial", 16, "bold"),
                                   bg='#1e1e1e', fg='white', width=6)
        self.focus_label.pack(pady=(0, 15))
        
        self.focus_slider = ttk.Scale(self.focus_vertical_frame, from_=2.0, to=0.5,
                                    variable=self.focus_value,
                                    command=lambda v: self.update_focus_value(),
                                    length=450, orient=tk.VERTICAL)
        self.focus_slider.pack()
        
        tk.Label(self.focus_slider_frame, text="F", font=("Arial", 24, "bold"), 
                bg='#1e1e1e', fg='white').pack(side=tk.LEFT, padx=20)
        
        # Ползунок зума
        self.zoom_frame = tk.Frame(self.vertical_sliders_frame, bg='#1e1e1e')
        self.zoom_frame.pack(side=tk.LEFT, padx=80)
        
        tk.Label(self.zoom_frame, text="24-70", font=("Arial", 16, "bold"), 
                bg='#1e1e1e', fg='white').pack(pady=(0, 15))
        
        self.zoom_slider_frame = tk.Frame(self.zoom_frame, bg='#1e1e1e')
        self.zoom_slider_frame.pack()
        
        self.zoom_vertical_frame = tk.Frame(self.zoom_slider_frame, bg='#1e1e1e')
        self.zoom_vertical_frame.pack(side=tk.LEFT, padx=15)
        
        self.zoom_label = tk.Label(self.zoom_vertical_frame, text="50", font=("Arial", 16, "bold"),
                                  bg='#1e1e1e', fg='white', width=6)
        self.zoom_label.pack(pady=(0, 15))
        
        self.zoom_slider = ttk.Scale(self.zoom_vertical_frame, from_=70, to=24,
                                   variable=self.zoom_value,
                                   command=lambda v: self.update_zoom_value(),
                                   length=450, orient=tk.VERTICAL)
        self.zoom_slider.pack()
        
        tk.Label(self.zoom_slider_frame, text="Z", font=("Arial", 24, "bold"), 
                bg='#1e1e1e', fg='white').pack(side=tk.LEFT, padx=20)
        
        # Нижний слайдер для параметров
        self.bottom_frame = tk.Frame(self.right_frame, bg='#1e1e1e', height=80)
        self.bottom_frame.pack_forget()
        
        # Слайдер параметров
        self.param_slider_frame = tk.Frame(self.bottom_frame, bg='#1e1e1e')
        self.param_slider_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.param_label = tk.Label(self.param_slider_frame, text="", 
                                   font=("Arial", 16, "bold"), bg='#1e1e1e', fg='white')
        self.param_label.pack(side=tk.LEFT, padx=(0, 30))
        
        self.param_slider = ttk.Scale(self.param_slider_frame, from_=0, to=100,
                                     command=self.update_param_value,
                                     length=700)
        self.param_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        self.param_value_label = tk.Label(self.param_slider_frame, text="", 
                                         font=("Arial", 16, "bold"), bg='#1e1e1e', fg='white',
                                         width=10)
        self.param_value_label.pack(side=tk.LEFT, padx=(30, 0))

        # Индикатор чувствительности
        self.sensitivity_label = tk.Label(self.right_frame, 
                                          text="Чувствительность: F=1.0x Z=1.0x",
                                          font=("Arial", 10),
                                          bg='#1e1e1e', fg='#aaaaaa')
        self.sensitivity_label.pack(side=tk.BOTTOM, pady=(0, 5))
        
        # Метка состояния геймпада
        self.gamepad_status_label = tk.Label(self.right_frame, text="Геймпад: не подключен", 
                                           font=("Arial", 12), bg='#1e1e1e', fg='#ff6666')
        self.gamepad_status_label.pack(side=tk.BOTTOM, pady=(0, 10))
    
    def setup_param_rect(self, frame, name, var, min_val, max_val, step, rect_id):
        """Настройка прямоугольника с параметром"""
        # Название параметра
        name_label = tk.Label(frame, text=name, font=("Arial", 16, "bold"), 
                            bg='#2d2d2d', fg='white')
        name_label.pack(pady=(20, 5))
        
        # Значение параметра
        value_label = tk.Label(frame, textvariable=var, font=("Arial", 20, "bold"), 
                             bg='#2d2d2d', fg='white')
        value_label.pack(pady=(5, 20))
        
        # Сохраняем ссылки для изменения цвета
        frame.rect_id = rect_id
        frame.name_label = name_label
        frame.value_label = value_label
        frame.original_bg = '#2d2d2d'
        frame.active_bg = '#0066cc'
        
        # Данные параметра
        frame.param_name = name
        frame.var = var
        frame.min_val = min_val
        frame.max_val = max_val
        frame.step = step
        
        # Привязываем клик
        frame.bind("<Button-1>", lambda e, f=frame: self.activate_param(f))
        name_label.bind("<Button-1>", lambda e, f=frame: self.activate_param(f))
        value_label.bind("<Button-1>", lambda e, f=frame: self.activate_param(f))
    
    def setup_recording_rect(self, frame):
        """Настройка прямоугольника записи"""
        self.recording_label = tk.Label(frame, text="00:00:00", font=("Arial", 20, "bold"), 
                                       bg='#2d2d2d', fg='white')
        self.recording_label.pack(expand=True)
        
        frame.original_bg = '#2d2d2d'
        frame.active_bg = '#0066cc'
        
        # Привязываем клик для переключения записи
        frame.bind("<Button-1>", self.toggle_recording)
        self.recording_label.bind("<Button-1>", self.toggle_recording)
    
    def activate_param(self, frame):
        """Активация параметра при нажатии на прямоугольник"""
        # Сбрасываем цвет всех прямоугольников
        for rect in self.rectangles:
            rect.config(bg=rect.original_bg)
            if hasattr(rect, 'name_label'):
                rect.name_label.config(bg=rect.original_bg)
            if hasattr(rect, 'value_label'):
                rect.value_label.config(bg=rect.original_bg)
        
        # Активируем выбранный прямоугольник
        frame.config(bg=frame.active_bg)
        if hasattr(frame, 'name_label'):
            frame.name_label.config(bg=frame.active_bg)
        if hasattr(frame, 'value_label'):
            frame.value_label.config(bg=frame.active_bg)
        
        # Настраиваем слайдер для этого параметра
        if hasattr(frame, 'param_name') and frame.param_name != "Запись":
            self.current_param = frame.param_name
            self.current_param_var = frame.var
            self.current_min = frame.min_val
            self.current_max = frame.max_val
            self.current_step = frame.step
            
            # Обновляем интерфейс слайдера
            self.param_label.config(text=frame.param_name)
            self.param_slider.config(from_=frame.min_val, to=frame.max_val)
            self.param_slider.set(frame.var.get())
            self.param_value_label.config(text=str(frame.var.get()))
            
            # Показываем слайдер
            self.bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(20, 0))
            
            # Входим в режим слайдера
            self.in_slider_mode = True
    
    def update_param_value(self, value):
        """Обновление значения параметра через слайдер"""
        if self.current_param_var is not None:
            # Применяем шаг
            if self.current_step == 1:
                stepped_value = round(float(value))
            elif self.current_step == 10:
                stepped_value = round(float(value) / 10) * 10
            elif self.current_step == 50:
                stepped_value = round(float(value) / 50) * 50
            else:
                stepped_value = round(float(value) / self.current_step) * self.current_step
            
            self.current_param_var.set(int(stepped_value))
            self.param_value_label.config(text=str(int(stepped_value)))
    
    def toggle_recording(self, event=None):
        """Переключение состояния записи"""
        self.recording = not self.recording
        
        if self.recording:
            self.recording_start_time = time.time() - self.recording_time
            self.recording_label.config(fg='red')
        else:
            self.recording_label.config(fg='white')
    
    def update_recording_time(self):
        """Обновление времени записи"""
        if self.recording:
            self.recording_time = time.time() - self.recording_start_time
            hours = int(self.recording_time // 3600)
            minutes = int((self.recording_time % 3600) // 60)
            seconds = int(self.recording_time % 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.recording_label.config(text=time_str)
        
        self.root.after(1000, self.update_recording_time)
    
    def update_focus_value(self):
        """Обновление значения фокуса"""
        self.focus_label.config(text=f"{self.focus_value.get():.1f}")
    
    def update_zoom_value(self):
        """Обновление значения зума"""
        self.zoom_label.config(text=f"{int(self.zoom_value.get())}")
    
    def setup_gamepad(self):
        """Настройка геймпада через pygame"""
        if not PYGAME_AVAILABLE:
            print("pygame не установлен")
            return
        
        print("\n" + "="*50)
        print("ИНИЦИАЛИЗАЦИЯ ГЕЙМПАДА")
        print("="*50)
        
        try:
            pygame.init()
            pygame.joystick.init()
            
            # Даём время на инициализацию
            time.sleep(0.1)
            
            joystick_count = pygame.joystick.get_count()
            print(f"Pygame видит джойстиков: {joystick_count}")
            
            if joystick_count > 0:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                self.gamepad_connected = True
                
                name = self.joystick.get_name()
                print(f"✓ Геймпад подключен: {name}")
                print(f"  Кнопок: {self.joystick.get_numbuttons()}")
                print(f"  Осей: {self.joystick.get_numaxes()}")
                
                self.gamepad_status_label.config(
                    text=f"Геймпад: {name}", 
                    fg='#66ff66'
                )
            else:
                print("✗ Джойстики не найдены")
                self.gamepad_status_label.config(
                    text="Геймпад не найден", 
                    fg='#ff6666'
                )
                
        except Exception as e:
            print(f"✗ Ошибка инициализации: {e}")
            import traceback
            traceback.print_exc()
            
        print("="*50 + "\n")
    
    def start_gamepad_thread(self):
        """Запуск отдельного потока для обработки стиков геймпада"""
        def gamepad_stick_worker():
            """Рабочий поток для обработки стиков (F и Z)"""
            while self.running:
                if self.gamepad_connected and self.joystick:
                    try:
                        # ТОЛЬКО читаем оси, без обработки событий
                        # Обработка событий будет в основном потоке
                        
                        # Левый стик (ось 1) - Фокус
                        left_stick_y = self.joystick.get_axis(1)
                        if abs(left_stick_y) > 0.1:
                            change_amount = -left_stick_y * 0.02 * self.focus_sensitivity
                            new_focus = self.focus_value.get() + change_amount
                            new_focus = max(0.5, min(2.0, new_focus))
                            self.root.after(0, lambda: self.update_focus_direct(new_focus))
                        
                        # Правый стик (ось 3) - Зум
                        right_stick_y = self.joystick.get_axis(3)
                        if abs(right_stick_y) > 0.1:
                            change_amount = -right_stick_y * 0.5 * self.zoom_sensitivity
                            new_zoom = self.zoom_value.get() + change_amount
                            new_zoom = max(24, min(70, new_zoom))
                            self.root.after(0, lambda: self.update_zoom_direct(new_zoom))
                            
                    except Exception as e:
                        print(f"Ошибка в потоке стиков: {e}")
                        self.gamepad_connected = False
                
                time.sleep(0.01)  # 100 раз в секунду
        
        # Запускаем поток
        self.stick_thread = threading.Thread(target=gamepad_stick_worker, daemon=True)
        self.stick_thread.start()
    
    def update_focus_direct(self, value):
        """Прямое обновление фокуса из потока"""
        self.focus_value.set(value)
        self.focus_label.config(text=f"{value:.1f}")
        
    def update_zoom_direct(self, value):
        """Прямое обновление зума из потока"""
        self.zoom_value.set(value)
        self.zoom_label.config(text=f"{int(value)}")

    def update_sensitivity_display(self, flash=False):
        if hasattr(self, 'sensitivity_label'):
            text = f"Чувствительность: F={self.focus_sensitivity:.1f}x Z={self.zoom_sensitivity:.1f}x"
            self.sensitivity_label.config(text=text)
            
            # Мигание при изменении
            if flash:
                self.sensitivity_label.config(fg='#ffcc00')  # Желтый
                self.root.after(200, lambda: self.sensitivity_label.config(fg='#aaaaaa'))  # Возврат через 200мс
             
    def check_gamepad_buttons(self):
        """Проверка кнопок геймпада в основном потоке"""
        try:
            if self.gamepad_connected and self.joystick:
                # Обновляем состояние геймпада
                pygame.event.pump()
                
                # Обрабатываем DPAD
                self.process_dpad()
                
                # Обрабатываем кнопки
                self.process_buttons()
                
                # Обрабатываем триггеры и бамперы - ДОБАВЬТЕ ЭТУ СТРОКУ
                self.process_triggers_and_bumpers()
                
        except Exception as e:
            print(f"Ошибка при проверке кнопок: {e}")
        
        # Проверяем каждые 50ms (20 раз в секунду)
        self.root.after(50, self.check_gamepad_buttons)
    
    def process_dpad(self):
        """Обработка крестовины (дискретно, по 0.2 секунды)"""
        current_time = time.time()
        
        # ВЛЕВО
        if self.joystick.get_button(self.BUTTON_MAPPING['DPAD_LEFT']):
            if current_time - self.last_dpad_left > 0.2:
                self.gamepad_navigation('left')
                self.last_dpad_left = current_time
        
        # ВПРАВО
        elif self.joystick.get_button(self.BUTTON_MAPPING['DPAD_RIGHT']):
            if current_time - self.last_dpad_right > 0.2:
                self.gamepad_navigation('right')
                self.last_dpad_right = current_time
        
        # ВВЕРХ
        if self.joystick.get_button(self.BUTTON_MAPPING['DPAD_UP']):
            if current_time - self.last_dpad_up > 0.2:
                self.gamepad_navigation('up')
                self.last_dpad_up = current_time
        
        # ВНИЗ
        elif self.joystick.get_button(self.BUTTON_MAPPING['DPAD_DOWN']):
            if current_time - self.last_dpad_down > 0.2:
                self.gamepad_navigation('down')
                self.last_dpad_down = current_time
    
    def process_buttons(self):
        """Обработка основных кнопок"""
        current_time = time.time()
        
        # Кнопка A (X) - ВЫБОР
        if self.joystick.get_button(self.BUTTON_MAPPING['A']):
            if current_time - self.last_button_A > 0.3:
                self.gamepad_navigation('enter')
                self.last_button_A = current_time
        
        # Кнопка B (Circle) - НАЗАД
        elif self.joystick.get_button(self.BUTTON_MAPPING['B']):
            if current_time - self.last_button_B > 0.3:
                self.gamepad_navigation('back')
                self.last_button_B = current_time
        
        # Кнопка X (Square) - ЗАПИСЬ
        elif self.joystick.get_button(self.BUTTON_MAPPING['X']):
            if current_time - self.last_button_X > 0.3:
                self.toggle_recording()
                self.last_button_X = current_time
        
        # Кнопка Y (Triangle) - ПЕРЕКЛЮЧЕНИЕ МЕНЮ
        elif self.joystick.get_button(self.BUTTON_MAPPING['Y']):
            if current_time - self.last_button_Y > 0.3:
                if self.selected_index == -1:
                    self.selected_index = 0
                else:
                    self.selected_index = -1
                    self.menu_selected = 0
                self.highlight_selected()
                self.last_button_Y = current_time
        
        # Кнопка OPTIONS - ПЕРЕКЛЮЧЕНИЕ МЕНЮ/ИНТЕРФЕЙС
        elif self.joystick.get_button(self.BUTTON_MAPPING['OPTIONS']):
            if current_time - self.last_button_OPTIONS > 0.5:
                if self.selected_index == -1:
                    self.selected_index = 0
                else:
                    self.selected_index = -1
                    self.menu_selected = 0
                self.highlight_selected()
                self.last_button_OPTIONS = current_time

    def process_triggers_and_bumpers(self):
        """Обработка триггеров и бамперов для регулировки чувствительности"""
        current_time = time.time()
        
        if not self.gamepad_connected or not self.joystick:
            return
        
        # Флаг, чтобы знать, изменилась ли чувствительность
        sensitivity_changed = False
        
        # Триггеры (LT и RT) - уменьшение чувствительности
        try:
            # Проверяем оси 2 и 5 (триггеры на PS4)
            if self.joystick.get_numaxes() > 2:
                lt_value = self.joystick.get_axis(4)
                # Для PS4: -1.0 (отпущено) до 1.0 (нажато)
                # Триггер нажат, если значение > 0.0
                if lt_value > 0.0:  # Нажат хотя бы немного
                    if current_time - self.last_trigger_LT > 0.5:  # Задержка 0.5 сек
                        old_focus_sens = self.focus_sensitivity
                        self.focus_sensitivity = max(0.2, self.focus_sensitivity - 0.1)
                        if old_focus_sens != self.focus_sensitivity:
                            print(f"Скорость F уменьшена: x{self.focus_sensitivity:.1f}")
                            sensitivity_changed = True
                        self.last_trigger_LT = current_time
            
            if self.joystick.get_numaxes() > 5:
                rt_value = self.joystick.get_axis(5)
                if rt_value > 0.0:  # Нажат хотя бы немного
                    if current_time - self.last_trigger_RT > 0.5:
                        old_zoom_sens = self.zoom_sensitivity
                        self.zoom_sensitivity = max(0.2, self.zoom_sensitivity - 0.1)
                        if old_zoom_sens != self.zoom_sensitivity:
                            print(f"Скорость Z уменьшена: x{self.zoom_sensitivity:.1f}")
                            sensitivity_changed = True
                        self.last_trigger_RT = current_time
                        
        except Exception as e:
            print(f"Ошибка при чтении триггеров: {e}")
            
        
        # Бамперы (LB/RB) - увеличение чувствительности
        try:
            # LB - увеличение чувствительности фокуса
            if self.joystick.get_button(self.BUTTON_MAPPING['LB']):
                if current_time - self.last_button_LB > 0.5:
                    old_focus_sens = self.focus_sensitivity
                    self.focus_sensitivity = min(3.0, self.focus_sensitivity + 0.1)
                    if old_focus_sens != self.focus_sensitivity:
                        print(f"Скорость F увеличена: x{self.focus_sensitivity:.1f}")
                        sensitivity_changed = True
                    self.last_button_LB = current_time
            
            # RB - увеличение чувствительности зума
            if self.joystick.get_button(self.BUTTON_MAPPING['RB']):
                if current_time - self.last_button_RB > 0.5:
                    old_zoom_sens = self.zoom_sensitivity
                    self.zoom_sensitivity = min(3.0, self.zoom_sensitivity + 0.1)
                    if old_zoom_sens != self.zoom_sensitivity:
                        print(f"Скорость Z увеличена: x{self.zoom_sensitivity:.1f}")
                        sensitivity_changed = True
                    self.last_button_RB = current_time
                    
        except Exception as e:
            print(f"Ошибка при чтении бамперов: {e}")
        
        # Если чувствительность изменилась - обновляем интерфейс
        if sensitivity_changed:
            self.update_sensitivity_display()
    
    def gamepad_navigation(self, action):
        """Обработка навигации с геймпада (дискретно)"""
        if action == 'left':
            if self.in_slider_mode and self.current_param_var:
                current = self.current_param_var.get()
                # Изменяем ровно на один шаг (без ускорения)
                new_value = max(self.current_min, current - self.current_step)
                self.current_param_var.set(int(new_value))
                self.param_slider.set(new_value)
                self.param_value_label.config(text=str(int(new_value)))
                print(f"[PARAM] {self.current_param}: {current} -> {new_value} (-{self.current_step})")
                
            elif self.selected_index >= 0:
                self.selected_index = max(0, self.selected_index - 1)
                self.highlight_selected()
        
        elif action == 'right':
            if self.in_slider_mode and self.current_param_var:
                current = self.current_param_var.get()
                # Изменяем ровно на один шаг (без ускорения)
                new_value = min(self.current_max, current + self.current_step)
                self.current_param_var.set(int(new_value))
                self.param_slider.set(new_value)
                self.param_value_label.config(text=str(int(new_value)))
                print(f"[PARAM] {self.current_param}: {current} -> {new_value} (+{self.current_step})")
                
            elif self.selected_index >= 0:
                self.selected_index = min(len(self.rectangles) - 1, self.selected_index + 1)
                self.highlight_selected()
        
        elif action == 'up':
            if self.selected_index == -1:
                # Перемещаемся ВВЕРХ по меню
                self.menu_selected = max(0, self.menu_selected - 1)
                self.highlight_selected()
            elif not self.in_slider_mode:
                # Переключаемся на меню
                self.selected_index = -1
                self.menu_selected = 0
                self.highlight_selected()
        
        elif action == 'down':
            if self.selected_index == -1:
                # Перемещаемся ВНИЗ по меню
                self.menu_selected = min(len(self.menu_items) - 1, self.menu_selected + 1)
                self.highlight_selected()
            elif self.in_slider_mode:
                # Выходим из режима слайдера
                self.in_slider_mode = False
                self.bottom_frame.pack_forget()
        
        elif action == 'enter':
            if self.selected_index == -1:
                # Нажатие на пункт меню
                if 0 <= self.menu_selected < len(self.menu_items):
                    self.menu_items[self.menu_selected].invoke()
            elif 0 <= self.selected_index < len(self.rectangles):
                # Нажатие на прямоугольник
                rect = self.rectangles[self.selected_index]
                if self.selected_index == 3:  # Прямоугольник записи
                    self.toggle_recording()
                else:
                    self.activate_param(rect)
                    self.in_slider_mode = True
        
        elif action == 'back':
            if self.in_slider_mode:
                self.in_slider_mode = False
                self.bottom_frame.pack_forget()
            elif self.selected_index == -1:
                # Возвращаемся к прямоугольникам
                self.selected_index = 0
                self.highlight_selected()
    
    def highlight_selected(self):
        """Выделение выбранного элемента"""
        # Сбрасываем выделение всех прямоугольников
        for rect in self.rectangles:
            rect.config(bg=rect.original_bg)
            if hasattr(rect, 'name_label'):
                rect.name_label.config(bg=rect.original_bg)
            if hasattr(rect, 'value_label'):
                rect.value_label.config(bg=rect.original_bg)
        
        # Сбрасываем выделение меню
        for btn in self.menu_items:
            btn.config(bg='#1a1a1a')
        
        if self.selected_index == -1:
            # Выделение в меню
            if 0 <= self.menu_selected < len(self.menu_items):
                self.menu_items[self.menu_selected].config(bg='#0066cc')
        elif 0 <= self.selected_index < len(self.rectangles):
            # Выделение прямоугольника
            rect = self.rectangles[self.selected_index]
            rect.config(bg=rect.active_bg)
            if hasattr(rect, 'name_label'):
                rect.name_label.config(bg=rect.active_bg)
            if hasattr(rect, 'value_label'):
                rect.value_label.config(bg=rect.active_bg)

    def update_sensitivity_display(self):
        """Обновление отображения чувствительности в интерфейсе"""
        if hasattr(self, 'sensitivity_label'):
            self.sensitivity_label.config(
                text=f"Чувствительность: F={self.focus_sensitivity:.1f}x Z={self.zoom_sensitivity:.1f}x"
            )
    
    def menu_action(self, item):
        """Действие при выборе пункта меню"""
        print(f"Выбран пункт меню: {item}")
    
    def exit_app(self):
        """Выход из приложения"""
        self.running = False
        if self.joystick:
            try:
                self.joystick.quit()
            except:
                pass
        try:
            pygame.quit()
        except:
            pass
        self.root.quit()

def main():
    root = tk.Tk()
    app = CameraControlApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
