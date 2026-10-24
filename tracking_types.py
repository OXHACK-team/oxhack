"""Landmarks always use mirrored image coordinates; timestamps use perf_counter."""
from dataclasses import dataclass, field
import numpy as np

NOSE, LS, RS, LE, RE, LW, RW, LH, RH, LK, RK, LA, RA = 0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28
CORE = [NOSE, LS, RS, LE, RE, LW, RW, LH, RH, LK, RK, LA, RA]


@dataclass
class TrackingFrame:
    timestamp: float
    landmarks: np.ndarray | None = None  # 33 rows: x, y, z, visibility
    frame: np.ndarray | None = None     # mirrored RGB, immutable once published
    hands: list = field(default_factory=list)  # hand centers in normalized coordinates
    people: int = 0
    status: str = "Looking for a player"
    inference_ms: float = 0.
    aspect: float = 4 / 3
    poses: list = field(default_factory=list)  # all detected bodies, before lane assignment
    x_bounds: tuple = (.015, .985)  # actual camera edges in this frame's coordinates

    @property
    def confidence(self):
        return float(np.min(self.landmarks[CORE, 3])) if self.landmarks is not None else 0.


def neutral_pose():
    p = np.zeros((33, 4), dtype=np.float64)
    p[:, :2] = [.5, .4]
    p[:, 3] = .99
    for i, xy in {NOSE:(.5,.16), LS:(.42,.29), RS:(.58,.29), LE:(.37,.43), RE:(.63,.43),
                  LW:(.35,.56), RW:(.65,.56), LH:(.45,.55), RH:(.55,.55),
                  LK:(.44,.73), RK:(.56,.73), LA:(.43,.92), RA:(.57,.92)}.items():
        p[i, :2] = xy
    return p
