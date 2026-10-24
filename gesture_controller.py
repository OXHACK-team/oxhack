"""Hand cursor, exponential smoothing and release-to-rearm dwell selection."""
import math
import numpy as np
from tracking_types import LS, RS, LW, RW, LH, RH
from motion_input import HAND_REACH_WIDTH


class GestureController:
    def __init__(self, config):
        self.config = config
        self.position = None
        self.target = None
        self.started = None
        self.progress = 0.
        self.blocked_target = None
        self.blocked_until = 0.
        self.active_wrist = None
        self.release_position = None

    def reset(self, now=0.):
        self.target = None
        self.started = None
        self.progress = 0.
        self.blocked_target = None
        self.blocked_until = now + .65
        self.release_position = self.position.copy() if self.position is not None else None

    def reset_owner(self, now=0.):
        self.position = None
        self.active_wrist = None
        self.reset(now)

    def hand_position(self, frame, pose, dt, width=1440, height=900):
        if pose is None:
            return None
        shoulder = np.mean(pose[[LS, RS], :2], axis=0)
        hip = np.mean(pose[[LH, RH], :2], axis=0)
        torso = max(.1, hip[1] - shoulder[1])
        # Choose the higher hand; switch only when the other is clearly higher.
        candidate = LW if pose[LW, 1] < pose[RW, 1] else RW
        if self.active_wrist is None or pose[candidate, 1] + torso*.15 < pose[self.active_wrist, 1]:
            self.active_wrist = candidate
        wrist = pose[self.active_wrist, :2]
        hand = wrist
        if frame.hands:
            nearest = min(frame.hands, key=lambda h: float(np.linalg.norm(h - wrist)))
            if np.linalg.norm(nearest - wrist) < .14:
                hand = nearest
        # Comfortable reach above the waist spans the complete UI, distance-normalized.
        x = .5 + (hand[0] - shoulder[0]) * (frame.aspect/(4/3)) / (torso * HAND_REACH_WIDTH)
        y = (hand[1] - (shoulder[1] - torso * .65)) / (torso * 1.6)
        desired = np.clip([x, y], .015, .985) * [width, height]
        alpha = 1 - math.exp(-max(.001, dt) / self.config.cursor_smoothing_seconds)
        self.position = desired if self.position is None else self.position + alpha * (desired - self.position)
        return self.position

    def update(self, position, buttons, now, enabled=True):
        if self.release_position is not None and position is not None:
            if np.linalg.norm(np.array(position)-self.release_position) < 32:
                self.target,self.started,self.progress=None,None,0.
                return None
            self.release_position=None
        target = next((b.key for b in buttons if b.enabled and position is not None and b.rect.collidepoint(position)), None) if enabled else None
        if target != self.blocked_target:
            self.blocked_target = None
        if target is None or now < self.blocked_until or target == self.blocked_target:
            self.target, self.started, self.progress = None, None, 0.
            return None
        if target != self.target:
            self.target, self.started = target, now
        self.progress = min(1., (now - self.started) / self.config.dwell_seconds)
        if self.progress >= 1:
            self.blocked_target = target
            self.blocked_until = now + .65
            self.target, self.started, self.progress = None, None, 0.
            return target
        return None
