"""NOVA is a local rule-based opponent with reaction delays and difficulty errors."""
import random
from motion_input import MotionInput


def pose_input(pose):
    return MotionInput(lean=-.5 if pose=="LEFT" else .5 if pose=="RIGHT" else 0.,
                       crouch=pose=="DUCK",left_up=pose in ("HANDS UP","LEFT HAND"),
                       right_up=pose in ("HANDS UP","RIGHT HAND"))


class AIController:
    def __init__(self,difficulty="normal",seed=1):
        self.rng=random.Random(seed)
        self.speed={"easy":.53,"normal":.76,"hard":.93}[difficulty]
        self.delay={"easy":.65,"normal":.36,"hard":.18}[difficulty]
        self.error_rate={"easy":.25,"normal":.12,"hard":.035}[difficulty]
        self.difficulty=difficulty
        self.token=None
        self.noticed=0.
        self.mistake=False
        self.jitter=0.

    def notice(self,game,token):
        if token!=self.token:
            self.token=token
            self.noticed=game.elapsed
            self.mistake=self.rng.random()<self.error_rate
            self.jitter=self.rng.uniform(-1,1)*{"easy":.55,"normal":.27,"hard":.10}[self.difficulty]
        return game.elapsed-self.noticed

    def act(self,game):
        key=game.game_id
        if key=="red_green":
            self.notice(game,(game.phase,sum(e["event"].startswith("phase_") for e in game.events)))
            if game.phase=="GREEN":
                return MotionInput(run=self.speed,motion=2.)
            moving=game.phase_elapsed<self.delay or (self.mistake and game.phase_elapsed<1.)
            return MotionInput(motion=2. if moving else .04)
        if key=="sprint":
            return MotionInput(run=self.speed,motion=2.)
        if key=="lightning":
            age=self.notice(game,game.target_number)
            if age>self.delay and not self.mistake:
                return MotionInput(right_hand=game.target)
        elif key=="dodge":
            self.notice(game,game.obstacle_number)
            if game.approach>.45 and not self.mistake:
                return pose_input(game.required)
        elif key=="timekeeper":
            self.notice(game,game.beat_number)
            moment=game.target_time+self.jitter
            return MotionInput(left_up=not self.mistake and moment<=game.beat_age<moment+.25)
        elif key=="echo" and game.stage=="REPEAT":
            age=self.notice(game,(game.round,game.step_index))
            if age>self.delay:
                return pose_input(game.expected if not self.mistake or age>self.delay+1.5 else "LEFT")
        return MotionInput()
