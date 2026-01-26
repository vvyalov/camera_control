# blackmagic_api.py
import requests
import json
import websocket
import threading
from datetime import datetime

class BlackmagicCamera:
    def __init__(self, hostname="camera.local", use_https=False):
        self.hostname = hostname
        self.protocol = "https" if use_https else "http"
        self.ws_protocol = "wss" if use_https else "ws"
        self.base_url = f"{self.protocol}://{hostname}"
        self.ws_url = f"{self.ws_protocol}://{hostname}/ws"
        
        # Хранилище данных с камеры (аналог propertyData в JS)
        self.property_data = {}
        self.ws = None
        self.ws_thread = None
        self.connected = False
        
    def connect(self):
        """Подключение к камере и инициализация WebSocket"""
        try:
            # Тестовый запрос для проверки доступности
            test = requests.get(f"{self.base_url}/device", timeout=3)
            if test.status_code == 200:
                self.connected = True
                self.start_websocket()
                return True
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return False
    
    def start_websocket(self):
        """Запуск WebSocket для получения обновлений"""
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_ws_message,
            on_error=self.on_ws_error,
            on_close=self.on_ws_close
        )
        
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
    
    def on_ws_message(self, ws, message):
        """Обработка сообщений от камеры"""
        try:
            data = json.loads(message)
            endpoint = data.get("path", "")
            if endpoint:
                self.property_data[endpoint] = data.get("value", {})
                # Здесь будет вызываться обновление UI
                if hasattr(self, 'update_ui_callback'):
                    self.update_ui_callback(endpoint, data['value'])
        except Exception as e:
            print(f"Ошибка обработки WS: {e}")
    
    def send_command(self, endpoint, data):
        """Основной метод отправки команд (аналог PUTdata из JS)"""
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.put(
                url, 
                json=data, 
                timeout=3,
                verify=False  # Для самоподписанных сертификатов
            )
            return response.json()
        except Exception as e:
            print(f"Ошибка отправки команды {endpoint}: {e}")
            return None
    
    # --- КОМАНДЫ КАМЕРЫ (из BMDevice.js) ---
    
    def record_start(self):
        return self.send_command("/transports/0/record", {"recording": True})
    
    def record_stop(self):
        return self.send_command("/transports/0/record", {"recording": False})
    
    def set_white_balance(self, kelvin):
        return self.send_command("/video/whiteBalance", {"whiteBalance": kelvin})
    
    def set_iso(self, iso):
        return self.send_command("/video/iso", {"iso": iso})
    
    def set_iris(self, f_stop):
        return self.send_command("/video/iris", {"iris": f_stop})
    
    def set_shutter_angle(self, angle):
        return self.send_command("/video/shutterAngle", {"shutterAngle": angle})
    
    # Добавьте остальные команды по аналогии...
    
    def set_update_callback(self, callback):
        """Установка функции для обновления UI"""
        self.update_ui_callback = callback