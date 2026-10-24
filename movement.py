"""Body-normalized motion; jogging requires repeated alternating leg activity."""
from collections import deque
import math
import numpy as np
from tracking_types import *


class MovementDetector:
    def __init__(self, config):
        self.config = config
        self.reset()

    def reset(self):
        self.previous = None
        self.last_time = None
        self.side = 0
        self.steps = deque()
        self.run_score = self.motion_score = 0.
        self.running = False

    def update(self, pose, timestamp, scale, aspect=4/3):
        if self.last_time is not None and timestamp <= self.last_time:
            return self.run_score, self.motion_score
        if self.previous is None or timestamp - self.last_time > .6:
            self.previous, self.last_time = pose.copy(), timestamp
            self.steps.clear()
            self.side = 0
            self.running = False
            self.run_score = self.motion_score = 0.
            return 0., 0.
        dt = max(.005, timestamp - self.last_time)
        points = pose[:, :2] * [aspect, 1]
        prior = self.previous[:, :2] * [aspect, 1]
        velocity = np.linalg.norm(points - prior, axis=1) / (max(.08, scale) * dt)
        velocity = np.maximum(0., velocity - .035)
        alpha = 1 - math.exp(-dt / .12)
        raw_motion = (float(np.quantile(velocity[CORE], .7)) + float(np.max(velocity[CORE])) * .2) * self.config.sensitivity
        self.motion_score += alpha * (raw_motion - self.motion_score)
        knee_diff = ((pose[LK, 1] - pose[LH, 1]) - (pose[RK, 1] - pose[RH, 1])) / max(.08, scale)
        threshold = self.config.run_knee_amplitude / self.config.sensitivity
        side = 1 if knee_diff > threshold else -1 if knee_diff < -threshold else 0
        if side and side != self.side:
            self.steps.append(timestamp)
            self.side = side
        while self.steps and timestamp - self.steps[0] > 1.5:
            self.steps.popleft()
        hip = np.mean(points[[LH, RH]], axis=0)
        old_hip = np.mean(prior[[LH, RH]], axis=0)
        relative_leg_speed = float(np.mean(np.linalg.norm((points[[LK, RK, LA, RA]] - hip) - (prior[[LK, RK, LA, RA]] - old_hip), axis=1))) / (max(.08, scale) * dt)
        energy = relative_leg_speed * self.config.sensitivity
        alternating = len(self.steps) >= 3 and timestamp - self.steps[-1] < .65
        self.running = alternating and energy > (self.config.run_energy_exit if self.running else self.config.run_energy_enter)
        target = min(1., energy / 2.) if self.running else 0.
        self.run_score += (1 - math.exp(-dt / .16)) * (target - self.run_score)
        self.previous, self.last_time = pose.copy(), timestamp
        return self.run_score, self.motion_score
