"""Registration, neutral-stance calibration, continuity checks and smoothing."""
import math
import numpy as np
from tracking_types import *


class PlayerManager:
    def __init__(self, config, label="Player 1"):
        self.config = config
        self.label = label
        self.reset()

    def reset(self):
        self.registered = False
        self.neutral = None
        self.smoothed = None
        self.body_scale = .26
        self.last_timestamp = None
        self.last_good = None
        self.last_center = None
        self.last_scale = None
        self.join_started = None
        self.samples = []
        self.calibration_started = None
        self.join_progress = 0.
        self.calibration_progress = 0.
        self.needs_rejoin = False
        self.valid = False
        self.message = "Step back until your body is visible."

    def request_rejoin(self):
        """Rearm body registration without requiring a mouse or ending the match."""
        if self.needs_rejoin:
            return
        self.registered = self.valid = False
        self.needs_rejoin = True
        self.neutral = self.smoothed = None
        self.last_timestamp = None
        self.last_scale = None
        self.join_started = self.calibration_started = None
        self.join_progress = self.calibration_progress = 0.
        self.samples.clear()
        self.message = "Stand still with arms down, then raise a hand to reconnect."

    def update(self, frame, now):
        self.valid = False
        p = frame.landmarks
        fresh = now - frame.timestamp <= self.config.tracking_stale_seconds
        enough = p is not None and frame.people == 1 and frame.confidence >= self.config.tracking_confidence
        if enough:
            enough = bool(np.all((p[CORE, 0] > frame.x_bounds[0]) & (p[CORE, 0] < frame.x_bounds[1])) and
                          np.all((p[CORE, 1] > .015) & (p[CORE, 1] < .985)))
        if not fresh or not enough:
            self._lost(now, frame.status if p is None or frame.people > 1 else "Move farther back: head, hands and feet must be visible")
            return False
        center = np.mean(p[[LH, RH], :2], axis=0)
        scale = float(np.linalg.norm((np.mean(p[[LS, RS], :2], axis=0) - center) * [frame.aspect, 1]))
        if self.registered and self.last_center is not None:
            if np.linalg.norm((center - self.last_center) * [frame.aspect, 1]) > self.body_scale * 1.25 or not .55 < scale / self.last_scale < 1.8:
                self._lost(now, "Player position changed. Return to your spot or recalibrate.")
                return False
        self.last_good = now
        self.last_center, self.last_scale = center, max(.08, scale)
        self.valid = True
        if frame.timestamp != self.last_timestamp:
            dt = .033 if self.last_timestamp is None else max(.001, frame.timestamp - self.last_timestamp)
            alpha = 1 - math.exp(-dt / self.config.pose_smoothing_seconds)
            self.smoothed = p.copy() if self.smoothed is None else self.smoothed + alpha * (p - self.smoothed)
            self.last_timestamp = frame.timestamp
        if self.registered:
            self.message = f"{self.label} connected"
            return True
        raised = min(p[LW, 1], p[RW, 1]) < p[NOSE, 1] - .035
        if self.neutral is None:
            self.message = "Stand naturally, arms down. Calibrating..."
            if raised:
                self.samples.clear()
                self.calibration_started = None
                self.calibration_progress = 0.
                self.message = "Lower your hands briefly to calibrate your neutral stance"
            else:
                if self.calibration_started is None:
                    self.calibration_started = now
                # One sample per camera frame, never inflate sample count at render FPS.
                if not self.samples or frame.timestamp != self.samples[-1][0]:
                    self.samples.append((frame.timestamp, p.copy()))
                self.calibration_progress = min(1., (now - self.calibration_started) / self.config.calibration_seconds)
                if self.calibration_progress >= 1 and len(self.samples) >= 8:
                    data = np.array([sample[1] for sample in self.samples])
                    if float(np.max(np.std(data[:, [LS, RS, LH, RH], :2], axis=0))) > .025:
                        self.samples.clear()
                        self.calibration_started = now
                        self.message = "Hold your neutral stance still for a moment"
                    else:
                        self.neutral = np.median(data, axis=0)
                        self.body_scale = max(.08, scale)
            return False
        self.message = "RAISE YOUR HAND TO JOIN"
        if raised:
            if self.join_started is None:
                self.join_started = now
            self.join_progress = min(1., (now - self.join_started) / self.config.join_hold_seconds)
            if self.join_progress >= 1:
                self.registered = True
                self.needs_rejoin = False
                self.message = f"{self.label.upper()} CONNECTED"
                return True
        else:
            self.join_started = None
            self.join_progress = 0.
        return False

    def _lost(self, now, message):
        self.message = message
        self.join_started = None
        self.join_progress = 0.
        if not self.registered:
            self.samples.clear()
            self.calibration_started = None
            self.calibration_progress = 0.
            if self.last_good is not None and now-self.last_good>self.config.rejoin_after_seconds:
                self.neutral=self.smoothed=None
                self.last_timestamp=None
        if self.registered and self.last_good is not None and now - self.last_good > self.config.rejoin_after_seconds:
            self.request_rejoin()
