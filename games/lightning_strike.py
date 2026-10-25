import math
from games.timed import TimedGame


class LightningStrike(TimedGame):
    game_id="lightning"
    goal=1200

    def __init__(self,config,now,rng=None):
        super().__init__(config,now,rng)
        self.target=None
        self.target_age=0.
        self.touch_held=0.
        self.target_number=0
        self.spawn()

    def spawn(self):
        choices=[(.24,.28),(.5,.25),(.76,.28),(.24,.55),(.76,.55),(.35,.72),(.65,.72)]
        available=[p for p in choices if p!=self.target]
        self.target=self.rng.choice(available)
        self.target_age=self.touch_held=0.
        self.target_number+=1
        self.target_lifetime=self.pace(2.5,1.4) if self.endless else max(1.35,2.2-self.combo*.04)
        self._event("target_spawn",target=list(self.target),number=self.target_number)

    def advance(self,dt,actions):
        self.target_age+=dt
        near=min(math.dist(hand,self.target) for hand in (actions.left_hand,actions.right_hand)) < self.config.target_radius
        self.touch_held=self.touch_held+dt if near else 0.
        if self.touch_held>=self.config.target_hold_seconds:
            self.award(100+min(100,self.combo*10),"TIME CHAIN!" if self.combo>2 else "CHARGED!",target=list(self.target))
            self.spawn()
        elif self.target_age>=self.target_lifetime:
            self.miss("TARGET EXPIRED")
            self.spawn()
        self.progress=min(1.,self.score/self.goal)

    def on_pause(self):
        pass  # preserve a charge already earned before the target clock froze
