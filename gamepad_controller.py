# gamepad_controller.py
import time
import threading
import pygame

class GamepadController:
    def __init__(self, app_reference):
        """
        Инициализация контроллера геймпада
        :param app_reference: ссылка на главное приложение для callback'ов
        """
        self.app = app_reference
        self.joystick = None
        self.gamepad_connected = False
        self.running = True
        
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
        self.last_trigger_LT = 0
        self.last_trigger_RT = 0
        self.last_button_LB = 0
        self.last_button_RB = 0
        
        # Состояние управления
        self.in_slider_mode = False
        self.selected_index = 0
        self.menu_selected = 0
        
        # Инициализация pygame
        self.setup_gamepad()
        
    def setup_gamepad(self):
        """Настройка геймпада через pygame"""
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
                
            else:
                print("✗ Джойстики не найдены")
                
        except Exception as e:
            print(f"✗ Ошибка инициализации: {e}")
            import traceback
            traceback.print_exc()
            
        print("="*50 + "\n")
        
    def start(self):
        """Запуск обработки геймпада"""
        if self.gamepad_connected:
            # Запускаем поток для обработки стиков
            self.start_gamepad_thread()
            
    def stop(self):
        """Остановка обработки геймпада"""
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
            
    def start_gamepad_thread(self):
        """Запуск отдельного потока для обработки стиков геймпада"""
        def gamepad_stick_worker():
            """Рабочий поток для обработки стиков (F и Z)"""
            while self.running:
                if self.gamepad_connected and self.joystick:
                    try:
                        # Левый стик (ось 1) - Фокус
                        left_stick_y = self.joystick.get_axis(1)
                        if abs(left_stick_y) > 0.1:
                            change_amount = -left_stick_y * 0.02 * self.app.focus_sensitivity
                            new_focus = self.app.focus_value.get() + change_amount
                            new_focus = max(0.5, min(2.0, new_focus))
                            self.app.root.after(0, lambda: self.app.update_focus_direct(new_focus))
                        
                        # Правый стик (ось 3) - Зум
                        right_stick_y = self.joystick.get_axis(3)
                        if abs(right_stick_y) > 0.1:
                            change_amount = -right_stick_y * 0.5 * self.app.zoom_sensitivity
                            new_zoom = self.app.zoom_value.get() + change_amount
                            new_zoom = max(24, min(70, new_zoom))
                            self.app.root.after(0, lambda: self.app.update_zoom_direct(new_zoom))
                            
                    except Exception as e:
                        print(f"Ошибка в потоке стиков: {e}")
                        self.gamepad_connected = False
                
                time.sleep(0.01)  # 100 раз в секунду
        
        # Запускаем поток
        self.stick_thread = threading.Thread(target=gamepad_stick_worker, daemon=True)
        self.stick_thread.start()
        
    def check_gamepad_buttons(self):
        """Проверка кнопок геймпада (вызывается из основного потока)"""
        try:
            if self.gamepad_connected and self.joystick:
                # Обновляем состояние геймпада
                pygame.event.pump()
                
                # Обрабатываем DPAD
                self.process_dpad()
                
                # Обрабатываем кнопки
                self.process_buttons()
                
                # Обрабатываем триггеры и бамперы
                self.process_triggers_and_bumpers()
                
        except Exception as e:
            print(f"Ошибка при проверке кнопок: {e}")
            
    def process_dpad(self):
        """Обработка крестовины (дискретно, по 0.2 секунды)"""
        current_time = time.time()
        
        # ВЛЕВО
        if self.joystick.get_button(self.BUTTON_MAPPING['DPAD_LEFT']):
            if current_time - self.last_dpad_left > 0.2:
                self.app.gamepad_navigation('left')
                self.last_dpad_left = current_time
        
        # ВПРАВО
        elif self.joystick.get_button(self.BUTTON_MAPPING['DPAD_RIGHT']):
            if current_time - self.last_dpad_right > 0.2:
                self.app.gamepad_navigation('right')
                self.last_dpad_right = current_time
        
        # ВВЕРХ
        if self.joystick.get_button(self.BUTTON_MAPPING['DPAD_UP']):
            if current_time - self.last_dpad_up > 0.2:
                self.app.gamepad_navigation('up')
                self.last_dpad_up = current_time
        
        # ВНИЗ
        elif self.joystick.get_button(self.BUTTON_MAPPING['DPAD_DOWN']):
            if current_time - self.last_dpad_down > 0.2:
                self.app.gamepad_navigation('down')
                self.last_dpad_down = current_time
    
    def process_buttons(self):
        """Обработка основных кнопок"""
        current_time = time.time()
        
        # Кнопка A (X) - ВЫБОР
        if self.joystick.get_button(self.BUTTON_MAPPING['A']):
            if current_time - self.last_button_A > 0.3:
                self.app.gamepad_navigation('enter')
                self.last_button_A = current_time
        
        # Кнопка B (Circle) - НАЗАД
        elif self.joystick.get_button(self.BUTTON_MAPPING['B']):
            if current_time - self.last_button_B > 0.3:
                self.app.gamepad_navigation('back')
                self.last_button_B = current_time
        
        # Кнопка X (Square) - ЗАПИСЬ
        elif self.joystick.get_button(self.BUTTON_MAPPING['X']):
            if current_time - self.last_button_X > 0.3:
                self.app.toggle_recording()
                self.last_button_X = current_time
        
        # Кнопка Y (Triangle) - ПЕРЕКЛЮЧЕНИЕ МЕНЮ
        elif self.joystick.get_button(self.BUTTON_MAPPING['Y']):
            if current_time - self.last_button_Y > 0.3:
                if self.selected_index == -1:
                    self.selected_index = 0
                else:
                    self.selected_index = -1
                    self.menu_selected = 0
                self.app.highlight_selected()
                self.last_button_Y = current_time
        
        # Кнопка OPTIONS - ПЕРЕКЛЮЧЕНИЕ МЕНЮ/ИНТЕРФЕЙС
        elif self.joystick.get_button(self.BUTTON_MAPPING['OPTIONS']):
            if current_time - self.last_button_OPTIONS > 0.5:
                if self.selected_index == -1:
                    self.selected_index = 0
                else:
                    self.selected_index = -1
                    self.menu_selected = 0
                self.app.highlight_selected()
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
                if lt_value > 0.0:  # Нажат хотя бы немного
                    if current_time - self.last_trigger_LT > 0.5:  # Задержка 0.5 сек
                        old_focus_sens = self.app.focus_sensitivity
                        self.app.focus_sensitivity = max(0.2, self.app.focus_sensitivity - 0.1)
                        if old_focus_sens != self.app.focus_sensitivity:
                            print(f"Скорость F уменьшена: x{self.app.focus_sensitivity:.1f}")
                            sensitivity_changed = True
                        self.last_trigger_LT = current_time
            
            if self.joystick.get_numaxes() > 5:
                rt_value = self.joystick.get_axis(5)
                if rt_value > 0.0:  # Нажат хотя бы немного
                    if current_time - self.last_trigger_RT > 0.5:
                        old_zoom_sens = self.app.zoom_sensitivity
                        self.app.zoom_sensitivity = max(0.2, self.app.zoom_sensitivity - 0.1)
                        if old_zoom_sens != self.app.zoom_sensitivity:
                            print(f"Скорость Z уменьшена: x{self.app.zoom_sensitivity:.1f}")
                            sensitivity_changed = True
                        self.last_trigger_RT = current_time
                        
        except Exception as e:
            print(f"Ошибка при чтении триггеров: {e}")
            
        # Бамперы (LB/RB) - увеличение чувствительности
        try:
            # LB - увеличение чувствительности фокуса
            if self.joystick.get_button(self.BUTTON_MAPPING['LB']):
                if current_time - self.last_button_LB > 0.5:
                    old_focus_sens = self.app.focus_sensitivity
                    self.app.focus_sensitivity = min(3.0, self.app.focus_sensitivity + 0.1)
                    if old_focus_sens != self.app.focus_sensitivity:
                        print(f"Скорость F увеличена: x{self.app.focus_sensitivity:.1f}")
                        sensitivity_changed = True
                    self.last_button_LB = current_time
            
            # RB - увеличение чувствительности зума
            if self.joystick.get_button(self.BUTTON_MAPPING['RB']):
                if current_time - self.last_button_RB > 0.5:
                    old_zoom_sens = self.app.zoom_sensitivity
                    self.app.zoom_sensitivity = min(3.0, self.app.zoom_sensitivity + 0.1)
                    if old_zoom_sens != self.app.zoom_sensitivity:
                        print(f"Скорость Z увеличена: x{self.app.zoom_sensitivity:.1f}")
                        sensitivity_changed = True
                    self.last_button_RB = current_time
                    
        except Exception as e:
            print(f"Ошибка при чтении бамперов: {e}")
        
        # Если чувствительность изменилась - обновляем интерфейс
        if sensitivity_changed:
            self.app.update_sensitivity_display()
            
    def get_gamepad_info(self):
        """Получение информации о подключенном геймпаде"""
        if self.gamepad_connected and self.joystick:
            return {
                'name': self.joystick.get_name(),
                'connected': True,
                'buttons': self.joystick.get_numbuttons(),
                'axes': self.joystick.get_numaxes()
            }
        return {
            'name': None,
            'connected': False,
            'buttons': 0,
            'axes': 0
        }
