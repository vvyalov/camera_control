#!/usr/bin/env python3
"""
АВТОМАТИЧЕСКИЙ ЗАПУСК ВСЕХ СКРИПТОВ
"""

import subprocess
import sys
import os
import time

def run_scanner():
    """Запускает сканер с интерактивным вводом"""
    print(f"\n{'='*50}")
    print(f"🚀 ЗАПУСК СКАНЕРА")
    print(f"{'='*50}")
    
    try:
        # Запускаем сканер напрямую, без передачи stdin
        print("Открываю сканер в новом процессе...")
        result = subprocess.run([sys.executable, "scanner.py"])
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def run_connect():
    """Запускает подключение"""
    print(f"\n{'='*50}")
    print(f"🚀 ПОДКЛЮЧЕНИЕ К КАМЕРЕ")
    print(f"{'='*50}")
    
    try:
        result = subprocess.run(
            [sys.executable, "connect.py"],
            text=True,
            capture_output=True
        )
        print(result.stdout)
        if result.stderr:
            print(f"Ошибки: {result.stderr}")
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def run_controller():
    """Запускает управление"""
    print(f"\n{'='*50}")
    print(f"🚀 УПРАВЛЕНИЕ КАМЕРОЙ")
    print(f"{'='*50}")
    
    try:
        print("Открываю контроллер...")
        result = subprocess.run([sys.executable, "controller.py"])
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def check_camera_selected():
    """Проверяет, что камера выбрана"""
    if not os.path.exists("selected_camera.txt"):
        return False
    
    with open("selected_camera.txt", "r") as f:
        content = f.read().strip()
    
    return len(content) > 0

def auto_launch():
    """Автоматический запуск"""
    print("="*60)
    print("🤖 BLACKMAGIC CAMERA CONTROL")
    print("="*60)
    
    # Проверяем файлы
    if not os.path.exists("scanner.py"):
        print("❌ scanner.py не найден")
        return False
    
    # ШАГ 1: Сканирование
    print("\n[1/3] 🔍 Поиск камер...")
    if not run_scanner():
        print("❌ Сканирование не удалось")
        return False
    
    # Проверяем выбор камеры
    time.sleep(1)
    if not check_camera_selected():
        print("❌ Камера не была выбрана")
        return False
    
    with open("selected_camera.txt", "r") as f:
        camera_address = f.read().strip()
    
    print(f"\n✅ Камера выбрана: {camera_address}")
    
    # ШАГ 2: Подключение
    print("\n[2/3] 🔗 Подключение...")
    time.sleep(1)
    
    if not run_connect():
        print("⚠️ Возможны ошибки подключения")
    
    # ШАГ 3: Управление
    print("\n[3/3] 🎮 Управление...")
    time.sleep(1)
    
    run_controller()
    
    print("\n" + "="*60)
    print("✅ ЗАВЕРШЕНО")
    print("="*60)
    
    return True

def main():
    """Главная функция"""
    try:
        auto_launch()
    except KeyboardInterrupt:
        print("\n\n⏹️ Остановлено")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

if __name__ == "__main__":
    main()