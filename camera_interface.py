# camera_interface.py
import tkinter as tk
from tkinter import ttk
import time
import os
import sys

# Импорт модуля управления геймпадом
try:
    from gamepad_controller import GamepadController
    GAMEPAD_AVAILABLE = True
except ImportError:
    GAMEPAD_AVAILABLE = False
    print("Модуль управления геймпадом не найден")

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
        
        # Настройки чувствительности
        self.focus_sensitivity = 1.0  # Базовая чувствительность фокуса
        self.zoom_sensitivity = 1.0   # Базовая чувствительность зума
        
        # Инициализация контроллера геймпада
        self.gamepad_controller = None
        if GAMEPAD_AVAILABLE:
            self.gamepad_controller = GamepadController(self)
            if self.gamepad_controller.gamepad_connected:
                self.gamepad_controller.start()
        
        self.setup_ui()
        
        # Запускаем проверку кнопок геймпада
        if self.gamepad_controller and self.gamepad_controller.gamepad_connected:
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
        
        # Обновляем статус геймпада
        self.update_gamepad_status()
    
    def update_gamepad_status(self):
        """Обновление статуса геймпада в интерфейсе"""
        if self.gamepad_controller:
            gamepad_info = self.gamepad_controller.get_gamepad_info()
            if gamepad_info['connected']:
                self.gamepad_status_label.config(
                    text=f"Геймпад: {gamepad_info['name']}", 
                    fg='#66ff66'
                )
            else:
                self.gamepad_status_label.config(
                    text="Геймпад не найден", 
                    fg='#ff6666'
                )
        else:
            self.gamepad_status_label.config(
                text="Модуль управления геймпадом не загружен", 
                fg='#ff6666'
            )
    
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
    
    def update_focus_direct(self, value):
        """Прямое обновление фокуса из потока"""
        self.focus_value.set(value)
        self.focus_label.config(text=f"{value:.1f}")
        
    def update_zoom_direct(self, value):
        """Прямое обновление зума из потока"""
        self.zoom_value.set(value)
        self.zoom_label.config(text=f"{int(value)}")

    def update_sensitivity_display(self):
        """Обновление отображения чувствительности в интерфейсе"""
        if hasattr(self, 'sensitivity_label'):
            self.sensitivity_label.config(
                text=f"Чувствительность: F={self.focus_sensitivity:.1f}x Z={self.zoom_sensitivity:.1f}x"
            )
             
    def check_gamepad_buttons(self):
        """Проверка кнопок геймпада в основном потоке"""
        if self.gamepad_controller:
            self.gamepad_controller.check_gamepad_buttons()
        
        # Проверяем каждые 50ms (20 раз в секунду)
        self.root.after(50, self.check_gamepad_buttons)
    
    def gamepad_navigation(self, action):
        """Обработка навигации с геймпада (дискретно)"""
        # Получаем состояние из контроллера
        if self.gamepad_controller:
            in_slider_mode = self.gamepad_controller.in_slider_mode
            selected_index = self.gamepad_controller.selected_index
            menu_selected = self.gamepad_controller.menu_selected
        else:
            in_slider_mode = self.in_slider_mode
            selected_index = self.selected_index
            menu_selected = self.menu_selected
        
        if action == 'left':
            if in_slider_mode and self.current_param_var:
                current = self.current_param_var.get()
                # Изменяем ровно на один шаг (без ускорения)
                new_value = max(self.current_min, current - self.current_step)
                self.current_param_var.set(int(new_value))
                self.param_slider.set(new_value)
                self.param_value_label.config(text=str(int(new_value)))
                print(f"[PARAM] {self.current_param}: {current} -> {new_value} (-{self.current_step})")
                
            elif selected_index >= 0:
                selected_index = max(0, selected_index - 1)
                self.selected_index = selected_index
                if self.gamepad_controller:
                    self.gamepad_controller.selected_index = selected_index
                self.highlight_selected()
        
        elif action == 'right':
            if in_slider_mode and self.current_param_var:
                current = self.current_param_var.get()
                # Изменяем ровно на один шаг (без ускорения)
                new_value = min(self.current_max, current + self.current_step)
                self.current_param_var.set(int(new_value))
                self.param_slider.set(new_value)
                self.param_value_label.config(text=str(int(new_value)))
                print(f"[PARAM] {self.current_param}: {current} -> {new_value} (+{self.current_step})")
                
            elif selected_index >= 0:
                selected_index = min(len(self.rectangles) - 1, selected_index + 1)
                self.selected_index = selected_index
                if self.gamepad_controller:
                    self.gamepad_controller.selected_index = selected_index
                self.highlight_selected()
        
        elif action == 'up':
            if selected_index == -1:
                # Перемещаемся ВВЕРХ по меню
                menu_selected = max(0, menu_selected - 1)
                self.menu_selected = menu_selected
                if self.gamepad_controller:
                    self.gamepad_controller.menu_selected = menu_selected
                self.highlight_selected()
            elif not in_slider_mode:
                # Переключаемся на меню
                self.selected_index = -1
                self.menu_selected = 0
                if self.gamepad_controller:
                    self.gamepad_controller.selected_index = -1
                    self.gamepad_controller.menu_selected = 0
                self.highlight_selected()
        
        elif action == 'down':
            if selected_index == -1:
                # Перемещаемся ВНИЗ по меню
                menu_selected = min(len(self.menu_items) - 1, menu_selected + 1)
                self.menu_selected = menu_selected
                if self.gamepad_controller:
                    self.gamepad_controller.menu_selected = menu_selected
                self.highlight_selected()
            elif in_slider_mode:
                # Выходим из режима слайдера
                self.in_slider_mode = False
                if self.gamepad_controller:
                    self.gamepad_controller.in_slider_mode = False
                self.bottom_frame.pack_forget()
        
        elif action == 'enter':
            if selected_index == -1:
                # Нажатие на пункт меню
                if 0 <= menu_selected < len(self.menu_items):
                    self.menu_items[menu_selected].invoke()
            elif 0 <= selected_index < len(self.rectangles):
                # Нажатие на прямоугольник
                rect = self.rectangles[selected_index]
                if selected_index == 3:  # Прямоугольник записи
                    self.toggle_recording()
                else:
                    self.activate_param(rect)
                    self.in_slider_mode = True
                    if self.gamepad_controller:
                        self.gamepad_controller.in_slider_mode = True
        
        elif action == 'back':
            if in_slider_mode:
                self.in_slider_mode = False
                if self.gamepad_controller:
                    self.gamepad_controller.in_slider_mode = False
                self.bottom_frame.pack_forget()
            elif selected_index == -1:
                # Возвращаемся к прямоугольникам
                self.selected_index = 0
                if self.gamepad_controller:
                    self.gamepad_controller.selected_index = 0
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
        
        # Получаем текущее состояние выбора
        if self.gamepad_controller:
            selected_index = self.gamepad_controller.selected_index
            menu_selected = self.gamepad_controller.menu_selected
        else:
            selected_index = self.selected_index
            menu_selected = self.menu_selected
            
        if selected_index == -1:
            # Выделение в меню
            if 0 <= menu_selected < len(self.menu_items):
                self.menu_items[menu_selected].config(bg='#0066cc')
        elif 0 <= selected_index < len(self.rectangles):
            # Выделение прямоугольника
            rect = self.rectangles[selected_index]
            rect.config(bg=rect.active_bg)
            if hasattr(rect, 'name_label'):
                rect.name_label.config(bg=rect.active_bg)
            if hasattr(rect, 'value_label'):
                rect.value_label.config(bg=rect.active_bg)
    
    def menu_action(self, item):
        """Действие при выборе пункта меню"""
        print(f"Выбран пункт меню: {item}")
    
    def exit_app(self):
        """Выход из приложения"""
        self.running = False
        if self.gamepad_controller:
            self.gamepad_controller.stop()
        self.root.quit()

def main():
    root = tk.Tk()
    app = CameraControlApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
