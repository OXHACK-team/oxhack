"""Configuration shared by tracking, input and the deterministic game engine."""
from dataclasses import asdict, dataclass, field
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent


@dataclass
class Config:
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480
    fullscreen: bool = True
    target_fps: int = 60
    player_name: str = "Player 1"
    sensitivity: float = 1.0
    sound: bool = True
    show_preview: bool = True
    tracking_confidence: float = .6
    tracking_stale_seconds: float = .55
    rejoin_after_seconds: float = 3.0
    join_hold_seconds: float = 1.2
    calibration_seconds: float = 1.0
    dwell_seconds: float = 1.0
    cursor_smoothing_seconds: float = .085
    pose_smoothing_seconds: float = .055
    time_limit_seconds: float = 60.0
    green_seconds: list = field(default_factory=lambda: [2., 5.])
    red_seconds: list = field(default_factory=lambda: [2., 4.])
    red_grace_seconds: float = .5
    red_motion_enter: float = .65
    red_motion_exit: float = .4
    red_motion_hold_seconds: float = .16
    penalty_cooldown_seconds: float = 1.5
    penalty_progress: float = .07
    run_knee_amplitude: float = .075
    run_energy_enter: float = .55
    run_energy_exit: float = .3
    forward_speed: float = .11
    arcade_seconds: float = 36.
    dodge_seconds: float = 36.
    sprint_seconds: float = 40.
    echo_seconds: float = 45.
    target_radius: float = .135
    target_hold_seconds: float = .10
    beat_period_seconds: float = 2.6
    beat_window_seconds: float = .32
    pose_hold_seconds: float = .45
    ai_difficulty: str = "normal"
    lean_threshold: float = .22
    crouch_threshold: float = .28

    @classmethod
    def load(cls, path=ROOT / "config.json"):
        raw = json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {}
        unknown = set(raw) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"Unknown configuration keys: {', '.join(sorted(unknown))}")
        cfg = cls(**raw)
        cfg.validate()
        return cfg

    def validate(self):
        if not .4 <= self.sensitivity <= 2.:
            raise ValueError("sensitivity must be between 0.4 and 2.0")
        for key in ("green_seconds", "red_seconds"):
            value = getattr(self, key)
            if len(value) != 2 or not 0 < value[0] <= value[1]:
                raise ValueError(f"{key} must be [positive minimum, maximum]")
        for key in ("time_limit_seconds", "forward_speed", "join_hold_seconds", "calibration_seconds",
                    "dwell_seconds", "target_fps", "camera_width", "camera_height", "tracking_stale_seconds",
                    "rejoin_after_seconds", "cursor_smoothing_seconds", "pose_smoothing_seconds",
                    "red_motion_hold_seconds", "penalty_cooldown_seconds", "run_knee_amplitude"):
            if getattr(self, key) <= 0:
                raise ValueError(f"{key} must be positive")
        if not 0 < self.tracking_confidence <= 1 or not 0 <= self.penalty_progress <= 1:
            raise ValueError("Invalid confidence or penalty")
        if not 0 <= self.red_motion_exit < self.red_motion_enter or not 0 <= self.run_energy_exit < self.run_energy_enter:
            raise ValueError("Motion hysteresis exit thresholds must be below enter thresholds")
        if self.red_grace_seconds < 0 or self.red_grace_seconds >= self.red_seconds[0]:
            raise ValueError("Red grace must be nonnegative and shorter than the shortest red phase")
        for key in ("arcade_seconds","dodge_seconds","sprint_seconds","echo_seconds","target_radius",
                    "target_hold_seconds","beat_period_seconds","beat_window_seconds","pose_hold_seconds"):
            if getattr(self,key)<=0:
                raise ValueError(f"{key} must be positive")
        if self.ai_difficulty not in ("easy","normal","hard"):
            raise ValueError("ai_difficulty must be easy, normal or hard")
        if self.beat_window_seconds>=self.beat_period_seconds/2 or self.target_radius>.3:
            raise ValueError("Beat window or target radius is too large")
        if not 0<self.lean_threshold<=.6 or not 0<self.crouch_threshold<=1:
            raise ValueError("Lean and crouch thresholds are outside the supported range")

    def save(self, path=ROOT / "config.json"):
        target = Path(path)
        temp = target.with_suffix(".tmp")
        temp.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        temp.replace(target)
