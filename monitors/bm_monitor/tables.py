"""
Blackmagic Camera Monitoring - Таблицы состояния
Хранит текущие значения всех параметров камеры
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from monitors.bm_monitor.constants import TransportMode, CodecType, DynamicRangeMode


@dataclass
class CameraStatusState:
    """Состояние статуса камеры"""
    power_on: bool = False
    connected: bool = False
    paired: bool = False
    versions_verified: bool = False
    initial_payload: bool = False
    ready: bool = False
    raw: int = 0
    updated_at: Optional[datetime] = None
    
    def update(self, flags: Dict):
        for key, value in flags.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()
    
    @property
    def is_recording(self) -> bool:
        """Алиас для удобства"""
        return self.ready and self.connected  # TODO: уточнить


@dataclass
class TimecodeState:
    """Состояние таймкода"""
    timecode: str = "00:00:00:00"
    hours: int = 0
    minutes: int = 0
    seconds: int = 0
    frames: int = 0
    raw: int = 0
    updated_at: Optional[datetime] = None
    
    def update(self, data: Dict):
        self.timecode = data.get('timecode', self.timecode)
        self.hours = data.get('hours', self.hours)
        self.minutes = data.get('minutes', self.minutes)
        self.seconds = data.get('seconds', self.seconds)
        self.frames = data.get('frames', self.frames)
        self.raw = data.get('timecode_bcd', self.raw)
        self.updated_at = datetime.now()


@dataclass
class LensState:
    """Состояние объектива"""
    focus: float = 0.0          # 0-1 norm
    aperture: float = 0.0       # normalized
    aperture_fstop: float = 0.0  # AV value
    zoom: float = 0.0          # normalized
    zoom_mm: int = 0
    ois: bool = False
    updated_at: Optional[datetime] = None
    
    def update(self, param: str, value: Any):
        if hasattr(self, param):
            setattr(self, param, value)
            self.updated_at = datetime.now()


@dataclass
class VideoState:
    """Состояние видеонастроек"""
    # Exposure
    iso: int = 400
    shutter_angle: int = 18000  # 180.00°
    shutter_speed: int = 50     # 1/50
    exposure_us: int = 10000    # 10ms
    gain_db: int = 0
    
    # White Balance
    white_balance: int = 5600   # K
    tint: int = 0
    
    # Format
    frame_rate: int = 24
    sensor_frame_rate: int = 24
    width: int = 1920
    height: int = 1080
    format_flags: int = 0
    format_flags_parsed: Dict = field(default_factory=dict)
    
    # Picture
    dynamic_range: int = DynamicRangeMode.FILM
    sharpening: int = 1
    nd_filter: float = 0.0
    
    updated_at: Optional[datetime] = None
    
    def update(self, param: str, value: Any):
        if hasattr(self, param):
            setattr(self, param, value)
            self.updated_at = datetime.now()
    
    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"
    
    @property
    def shutter_angle_deg(self) -> float:
        return self.shutter_angle / 100.0
    
    @property
    def shutter_speed_fraction(self) -> str:
        return f"1/{self.shutter_speed}"


@dataclass
class AudioState:
    """Состояние аудио"""
    mic_level: float = 0.5
    headphone_level: float = 0.5
    input_type: int = 0  # Internal mic
    input_level_ch0: float = 0.5
    input_level_ch1: float = 0.5
    phantom_power: bool = False
    updated_at: Optional[datetime] = None


@dataclass
class DisplayState:
    """Состояние дисплея и ассистентов"""
    brightness: float = 0.5
    zebra_level: float = 0.7
    peaking_level: float = 0.5
    updated_at: Optional[datetime] = None


@dataclass
class MediaState:
    """Состояние медиа"""
    transport_mode: int = TransportMode.PREVIEW
    transport_mode_name: str = "PREVIEW"
    codec_type: int = CodecType.BRAW
    codec_variant: int = 0
    slot1_type: int = 0
    slot2_type: int = 0
    time_lapse: bool = False
    updated_at: Optional[datetime] = None


@dataclass
class MetadataState:
    """Метаданные проекта"""
    reel: int = 0
    scene: str = ""
    take: int = 1
    camera_id: str = ""
    operator: str = ""
    project: str = ""
    updated_at: Optional[datetime] = None


class CameraState:
    """
    Полное состояние камеры
    """
    
    def __init__(self):
        self.status = CameraStatusState()
        self.timecode = TimecodeState()
        self.lens = LensState()
        self.video = VideoState()
        self.audio = AudioState()
        self.display = DisplayState()
        self.media = MediaState()
        self.metadata = MetadataState()
        
        self.device_info = {
            'manufacturer': '',
            'model': '',
            'protocol_version': ''
        }
        
        self.updated_at = datetime.now()
        self.callbacks = []
    
    def register_callback(self, callback):
        """Подписка на изменения"""
        self.callbacks.append(callback)
    
    def _notify(self, section: str, param: str, value: Any):
        """Уведомление подписчиков"""
        for cb in self.callbacks:
            try:
                cb(section, param, value)
            except:
                pass
    
    def update_from_parser(self, parsed_data: Dict):
        """
        Обновление состояния из данных парсера
        """
        char_type = parsed_data.get('type')
        
        if char_type == 'camera_status':
            flags = parsed_data.get('flags', {})
            self.status.update(flags)
            self._notify('status', 'all', flags)
            
        elif char_type == 'timecode':
            self.timecode.update(parsed_data)
            self._notify('timecode', 'timecode', self.timecode.timecode)
            
        elif char_type == 'camera_control':
            for packet in parsed_data.get('packets', []):
                decoded = packet.get('decoded', {})
                if decoded.get('valid'):
                    self._update_parameter(decoded)
    
    def _update_parameter(self, decoded: Dict):
        """
        Обновление отдельного параметра
        """
        category = decoded.get('category')
        name = decoded.get('name')
        value = decoded.get('value')
        
        if category == 0:  # Lens
            if name == 'Focus':
                self.lens.focus = value
            elif name == 'Aperture_Normalised':
                self.lens.aperture = value
            elif name == 'Zoom_Normalised':
                self.lens.zoom = value
            elif name == 'OIS':
                self.lens.ois = value
                
        elif category == 1:  # Video
            if name == 'ISO':
                self.video.iso = value
            elif name == 'ShutterAngle':
                self.video.shutter_angle = value
            elif name == 'ShutterSpeed':
                self.video.shutter_speed = value
            elif name == 'WhiteBalance':
                self.video.white_balance = value
            elif name == 'Tint':
                self.video.tint = value
                
            elif name == 'RecordingFormat':
                vals = decoded.get('values', {})
                self.video.frame_rate = vals.get('frame_rate', self.video.frame_rate)
                self.video.sensor_frame_rate = vals.get('sensor_frame_rate', self.video.sensor_frame_rate)
                self.video.width = vals.get('width', self.video.width)
                self.video.height = vals.get('height', self.video.height)
                self.video.format_flags = vals.get('flags', self.video.format_flags)
                self.video.format_flags_parsed = vals.get('flags_parsed', {})
                
        elif category == 2:  # Audio
            if name == 'MicLevel':
                self.audio.mic_level = value
            elif name == 'HeadphoneLevel':
                self.audio.headphone_level = value
                
        elif category == 4:  # Display
            if name == 'Brightness':
                self.display.brightness = value
            elif name == 'ZebraLevel':
                self.display.zebra_level = value
            elif name == 'PeakingLevel':
                self.display.peaking_level = value
                
        elif category == 10:  # Media
            if name == 'TransportMode':
                vals = decoded.get('values', {})
                self.media.transport_mode = vals.get('mode', self.media.transport_mode)
                self.media.transport_mode_name = vals.get('mode_name', 'UNKNOWN')
                self.media.slot1_type = vals.get('slot1_type', self.media.slot1_type)
                self.media.slot2_type = vals.get('slot2_type', self.media.slot2_type)
                self.media.time_lapse = vals.get('time_lapse', self.media.time_lapse)
                
        self.updated_at = datetime.now()
        self._notify('parameter', name, value)
    
    def get_summary(self) -> Dict:
        """Краткое состояние для UI"""
        return {
            'status': 'RECORDING' if self.media.transport_mode == TransportMode.RECORD else self.media.transport_mode_name,
            'timecode': self.timecode.timecode,
            'lens': f"{self.lens.focus:.2f} / F{self.lens.aperture:.1f}",
            'exposure': f"ISO{self.video.iso} {self.video.shutter_speed_fraction}",
            'wb': f"{self.video.white_balance}K",
            'resolution': self.video.resolution,
            'fps': self.video.frame_rate
        }