"""A shared, body-relative vocabulary for every human, simulated and AI player."""
from dataclasses import dataclass
import numpy as np
from tracking_types import LS, RS, LW, RW, LH, RH

HAND_REACH_WIDTH = 2.5  # torso lengths; includes UI corners inside the camera


@dataclass(frozen=True)
class MotionInput:
    run: float = 0.
    motion: float = 0.
    lean: float = 0.
    crouch: bool = False
    left_up: bool = False
    right_up: bool = False
    left_hand: tuple = (.25, .9)
    right_hand: tuple = (.75, .9)

    @property
    def raised(self):
        return self.left_up or self.right_up

    def matches(self, pose,lean_threshold=.22):
        return {"LEFT": self.lean < -lean_threshold, "RIGHT": self.lean > lean_threshold,
                "DUCK": self.crouch, "HANDS UP": self.left_up and self.right_up,
                "LEFT HAND": self.left_up and not self.right_up,
                "RIGHT HAND": self.right_up and not self.left_up}.get(pose, False)


def from_player(player, movement, aspect=4/3):
    if not player.valid or player.smoothed is None or player.neutral is None:
        return MotionInput()
    p, neutral = player.smoothed, player.neutral
    shoulder = np.mean(p[[LS, RS], :2], axis=0)
    neutral_shoulder = np.mean(neutral[[LS, RS], :2], axis=0)
    hip = np.mean(p[[LH, RH], :2], axis=0)
    old_hip = np.mean(neutral[[LH, RH], :2], axis=0)
    scale = max(.08, player.body_scale)
    torso = max(.1, old_hip[1]-neutral_shoulder[1])
    def hand(i):
        return (float(np.clip(.5+(p[i,0]-shoulder[0])*(aspect/(4/3))/(torso*HAND_REACH_WIDTH),0,1)),
                float(np.clip((p[i,1]-(shoulder[1]-torso*.65))/(torso*1.6),0,1)))
    return MotionInput(float(movement.run_score), float(movement.motion_score),
        float((shoulder[0]-neutral_shoulder[0])*aspect/scale*player.config.sensitivity),
        bool((hip[1]-old_hip[1])/scale*player.config.sensitivity > player.config.crouch_threshold),
        bool(p[LW,1]<shoulder[1]-.1*torso), bool(p[RW,1]<shoulder[1]-.1*torso), hand(LW), hand(RW))
