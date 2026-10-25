"""Optional body-input warmups. No game clocks, scores, records or AI decisions."""
from dataclasses import dataclass
import math
from motion_input import MotionInput


@dataclass(frozen=True)
class CoachStep:
    kind: str
    label: str
    instruction: str
    demo_pose: str
    seconds: float
    target: tuple = (.5,.35)


LESSONS={
    "red_green":(
        CoachStep("RUN","JOG IN PLACE","Alternate your knees. Let your avatar build speed.","RUN",1.2),
        CoachStep("FREEZE","NOW FREEZE","Stop your whole body. Hold still until the ring fills.","IDLE",.9)),
    "sprint":(
        CoachStep("RUN","FIND YOUR RUNNING RHYTHM","Jog in place. Alternate knees; hand shaking will not count.","RUN",1.8),),
    "dodge":(
        CoachStep("LEFT","LEAN LEFT","Shift your shoulders left while keeping your feet planted.","LEFT",.6),
        CoachStep("RIGHT","LEAN RIGHT","Now shift your shoulders to the right.","RIGHT",.6),
        CoachStep("DUCK","DUCK DOWN","Bend your knees and lower your hips.","DUCK",.6)),
    "lightning":(
        CoachStep("REACH","REACH THE PRACTICE ORB","Move either hand cursor onto the orb and hold briefly.","RIGHT HAND",.25),),
    "timekeeper":(
        CoachStep("LOWER","LOWER YOUR HANDS","Start below shoulder height. The next move is a fresh raise.","IDLE",.35),
        CoachStep("RAISE","RAISE EITHER HAND","Raise a hand. In the game, do this when the rings meet.","LEFT HAND",.5),
        CoachStep("LOWER","LOWER AGAIN","Lower between beats so your next raise can count.","IDLE",.5)),
    "echo":(
        CoachStep("LEFT","MATCH THE ECHO / LEAN LEFT","Copy the purple model and hold each pose briefly.","LEFT",.55),
        CoachStep("HANDS UP","MATCH THE ECHO / HANDS UP","Raise both hands above your shoulders.","HANDS UP",.55),
        CoachStep("DUCK","MATCH THE ECHO / DUCK","Lower your hips. The game will ask you to remember poses.","DUCK",.55)),
}


class CoachPlayer:
    def __init__(self,steps):
        self.steps=steps
        self.step_index=0
        self.held=0.
        self.tracking_ok=False
        self.matching=False
        self.last_action=MotionInput()

    @property
    def complete(self):
        return self.step_index>=len(self.steps)

    @property
    def current_step(self):
        return self.steps[min(self.step_index,len(self.steps)-1)]

    @property
    def hold_progress(self):
        return 1. if self.complete else min(1.,self.held/self.current_step.seconds)


class PracticeCoach:
    def __init__(self,game_id,config,player_count=1):
        if game_id not in LESSONS:
            raise ValueError(f"Unknown practice game: {game_id}")
        if player_count not in (1,2):
            raise ValueError("Practice supports one or two simultaneous humans")
        self.game_id=game_id
        self.config=config
        self.players=[CoachPlayer(LESSONS[game_id]) for _ in range(player_count)]

    @property
    def complete(self):
        return all(player.complete for player in self.players)

    def _matches(self,step,action):
        if step.kind=="RUN":
            return action.run>=.3
        if step.kind=="FREEZE":
            return action.motion<self.config.red_motion_exit
        if step.kind=="LOWER":
            return not action.raised
        if step.kind=="RAISE":
            return action.raised
        if step.kind=="REACH":
            return min(math.dist(hand,step.target) for hand in (action.left_hand,action.right_hand))<=self.config.target_radius
        return action.matches(step.kind,self.config.lean_threshold)

    def update(self,dt,actions,validity):
        # A stalled render or lost body cannot manufacture a completed hold.
        dt=max(0.,min(.1,float(dt)))
        for i,player in enumerate(self.players):
            player.tracking_ok=i<len(validity) and bool(validity[i])
            player.last_action=actions[i] if i<len(actions) and player.tracking_ok else MotionInput()
            if player.complete:
                continue
            if not player.tracking_ok:
                player.held=0.
                player.matching=False
                continue
            player.matching=self._matches(player.current_step,player.last_action)
            player.held=player.held+dt if player.matching else 0.
            if player.held+1e-8>=player.current_step.seconds:
                player.step_index+=1
                player.held=0.
                player.matching=False
