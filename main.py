#!/usr/bin/env python3
"""
🏠 ГЛАВНОЕ МЕНЮ - Управление камерами Blackmagic
"""

import asyncio
import sys
import os
import platform
import subprocess
from enum import Enum

# Добавляем путь к нашим модулям
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from protocols.ble.scanner import BLECameraScanner
from protocols.ble.connector import BLECameraConnector

class MenuChoice(Enum):
    DEBUG_MONITOR = 1
    CAMERA_MONITOR = 2
    SIMPLE_MONITOR = 3
    SCAN_CAMERAS = 4
    SYSTEM_INFO = 5
    EXIT = 6

def clear_screen():
    """Очистка экрана"""
    os.system('clear' if os.name == 'posix' else 'cls')

def print_header():
    """Заголовок программы"""
    print("=" * 60)
    print("     🎬 BLACKMAGIC CAMERA CONTROL v1.0")
    print("=" * 60)
    print()

async def get_camera_address(force_scan=False):
    """Получение адреса камеры"""
    # Если не нужно сканировать и есть сохраненный адрес
    if not force_scan and os.path.exists("selected_camera.txt"):
        with open("selected_camera.txt", "r") as f:
            address = f.read().strip()
            if address:
                return address
    
    # Сканируем
    print("🔍 Сканирую камеры...")
    scanner = BLECameraScanner()
    cameras = await scanner.progressive_scan()
    
    if not cameras:
        print("❌ Камеры не найдены")
        return None
    
    selected = scanner.select_camera(cameras)
    if not selected:
        return None
    
    name, address = selected
    scanner.save_selected_camera(selected)
    print(f"✅ Выбрана камера: {name}")
    return address

def run_monitor_script(script_name, address=None):
    """Запуск монитора как отдельного процесса"""
    try:
        if address:
            # Создаем временный файл с адресом для монитора
            temp_file = "temp_camera_address.txt"
            with open(temp_file, "w") as f:
                f.write(address)
            
            # Запускаем монитор с передачей адреса
            env = os.environ.copy()
            env["CAMERA_ADDRESS"] = address
            
            # Для Unix-систем
            if platform.system() != "Windows":
                # Используем терминал для корректного отображения
                subprocess.run([
                    "python3", 
                    f"monitors/{script_name}",
                    address
                ], env=env)
            else:
                # Для Windows
                subprocess.run([
                    "python", 
                    f"monitors/{script_name}",
                    address
                ], env=env, shell=True)
            
            # Удаляем временный файл
            if os.path.exists(temp_file):
                os.remove(temp_file)
        else:
            # Просто запускаем монитор
            subprocess.run(["python3", f"monitors/{script_name}"])
            
    except FileNotFoundError:
        print(f"❌ Файл monitors/{script_name} не найден")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")

async def option_debug_monitor():
    """Опция 1: Отладочный монитор"""
    clear_screen()
    print_header()
    
    print("🔍 ЗАПУСК ОТЛАДОЧНОГО МОНИТОРА")
    print("-" * 40)
    
    address = await get_camera_address()
    if not address:
        input("\nНажмите Enter для возврата...")
        return
    
    print(f"\n📡 Запускаю монитор для камеры: {address[:17]}...")
    print("Управление в мониторе:")
    print("  [p] - Пауза/продолжить вывод")
    print("  [s] - Показать состояние")
    print("  [q] - Выйти")
    print("\nЗапуск через 3 секунды...")
    
    await asyncio.sleep(3)
    run_monitor_script("unified_monitor.py", address)

async def option_camera_monitor():
    """Опция 2: Основной монитор"""
    clear_screen()
    print_header()
    
    print("🎬 ЗАПУСК ОСНОВНОГО МОНИТОРА")
    print("-" * 40)
    
    address = await get_camera_address()
    if not address:
        input("\nНажмите Enter для возврата...")
        return
    
    print(f"\n📡 Запускаю профессиональный монитор...")
    print("Управление в мониторе:")
    print("  [Q] - Выйти")
    print("  [R] - Показать сырые данные")
    print("  [P] - Пауза")
    print("  [C] - Очистить экран")
    print("\nЗапуск через 3 секунды...")
    
    await asyncio.sleep(3)
    run_monitor_script("main_monitor.py", address)

async def option_simple_monitor():
    """Опция 3: Простой монитор"""
    clear_screen()
    print_header()
    
    print("📊 ПРОСТОЙ МОНИТОР СТАТУСА")
    print("-" * 40)
    
    address = await get_camera_address()
    if not address:
        input("\nНажмите Enter для возврата...")
        return
    
    print(f"📡 Подключаюсь к камере: {address[:17]}...")
    
    connector = BLECameraConnector(address)
    connected = await connector.connect()
    
    if not connected:
        print("❌ Не удалось подключиться")
        input("\nНажмите Enter для возврата...")
        return
    
    print("✅ Подключено!")
    print("\nОбновление каждые 2 секунды...")
    print("Нажмите Ctrl+C для выхода")
    
    try:
        while True:
            clear_screen()
            print_header()
            print("📊 СТАТУС КАМЕРЫ (обновление: каждые 2 сек)")
            print("-" * 40)
            print(f"Адрес: {address}")
            
            # Получаем информацию
            info = await connector.get_camera_info()
            if info:
                print("\n📸 Информация:")
                for key, value in info.items():
                    print(f"  {key}: {value}")
            
            # Получаем статус
            status = await connector.get_status()
            if status:
                print(f"\n📡 Статус: {status.hex()[:20]}...")
            
            print("\n" + "-" * 40)
            print("Ожидание обновления...")
            
            # Ждем 2 секунды или прерывание
            try:
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
                
    except KeyboardInterrupt:
        print("\n\n⏹️ Возвращаюсь в меню...")
    
    finally:
        await connector.disconnect()
        await asyncio.sleep(1)

async def option_scan_cameras():
    """Опция 4: Сканирование камер"""
    clear_screen()
    print_header()
    
    print("🔍 СКАНИРОВАНИЕ КАМЕР")
    print("-" * 40)
    
    scanner = BLECameraScanner()
    cameras = await scanner.progressive_scan()
    
    if cameras:
        print(f"\n✅ Найдено камер: {len(cameras)}")
        
        selected = scanner.select_camera(cameras)
        if selected:
            name, address = selected
            scanner.save_selected_camera(selected)
            print(f"\n🎯 Выбрана камера: {name}")
            print(f"📁 Адрес сохранен")
    
    else:
        print("\n❌ Камеры не найдены")
    
    input("\nНажмите Enter для возврата...")

def option_system_info():
    """Опция 5: Информация о системе"""
    clear_screen()
    print_header()
    
    print("💻 ИНФОРМАЦИЯ О СИСТЕМЕ")
    print("-" * 40)
    
    print(f"ОС: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    
    # Проверяем модули
    print("\n📦 ПРОВЕРКА МОДУЛЕЙ:")
    modules = ["bleak", "asyncio"]
    for module in modules:
        try:
            __import__(module)
            version = "OK"
            if module == "bleak":
                import bleak
                version = bleak.__version__
            print(f"  {module}: ✅ {version}")
        except ImportError:
            print(f"  {module}: ❌ НЕ УСТАНОВЛЕН")
    
    # Проверяем структуру проекта
    print("\n📁 СТРУКТУРА ПРОЕКТА:")
    project_structure = [
        ("main.py", "✅" if os.path.exists("main.py") else "❌"),
        ("protocols/ble/scanner.py", "✅" if os.path.exists("protocols/ble/scanner.py") else "❌"),
        ("protocols/ble/connector.py", "✅" if os.path.exists("protocols/ble/connector.py") else "❌"),
        ("protocols/bm/parser.py", "✅" if os.path.exists("protocols/bm/parser.py") else "❌"),
        ("monitors/unified_monitor.py", "✅" if os.path.exists("monitors/unified_monitor.py") else "❌"),
        ("monitors/main_monitor.py", "✅" if os.path.exists("monitors/main_monitor.py") else "❌"),
    ]
    
    for file, status in project_structure:
        print(f"  {file:30} {status}")
    
    input("\nНажмите Enter для возврата...")

def display_menu():
    """Отображение меню"""
    clear_screen()
    print_header()
    
    print("🏠 ГЛАВНОЕ МЕНЮ")
    print("-" * 40)
    
    menu_items = [
        ("1", "🔍 Отладочный монитор", "Сырые HEX данные, логирование"),
        ("2", "🎬 Основной монитор", "Профессиональный интерфейс"),
        ("3", "📊 Простой монитор", "Базовая информация о камере"),
        ("4", "🔎 Сканирование камер", "Поиск и выбор камеры"),
        ("5", "💻 Информация о системе", "Проверка установленных модулей"),
        ("6", "🚪 Выход", "Завершить программу"),
    ]
    
    for num, title, desc in menu_items:
        print(f"{num}. {title}")
        print(f"   {desc}")
    
    print("-" * 40)
    return input("\nВыберите действие (1-6): ").strip()

async def main():
    """Основная функция программы"""
    while True:
        try:
            choice = display_menu()
            
            if choice == "1":
                await option_debug_monitor()
            elif choice == "2":
                await option_camera_monitor()
            elif choice == "3":
                await option_simple_monitor()
            elif choice == "4":
                await option_scan_cameras()
            elif choice == "5":
                option_system_info()
            elif choice == "6":
                print("\n👋 До свидания!")
                break
            else:
                print(f"❌ Неверный выбор: {choice}")
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n👋 До свидания!")
            break
        except Exception as e:
            print(f"\n⚠️ Ошибка: {e}")
            input("\nНажмите Enter для продолжения...")

if __name__ == "__main__":
    # Для корректной работы asyncio на Windows
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Программа завершена")