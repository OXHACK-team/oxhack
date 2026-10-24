from games.timed import TimedGame


class DodgeOrDie(TimedGame):
    game_id="dodge"
    goal=1

    def __init__(self,config,now,rng=None):
        super().__init__(config,now,rng,duration=config.dodge_seconds)
        self.lives=5
        self.obstacle_age=0.
        self.obstacle_number=0
        self.spawn()

    def spawn(self):
        self.required=self.rng.choice(["LEFT","RIGHT","DUCK"])
        self.obstacle_age=0.
        self.obstacle_number+=1
        self.travel_seconds=max(1.65,2.55-self.obstacle_number*.035)
        self.dodged_held=0.
        self._event("obstacle_spawn",required=self.required,number=self.obstacle_number)

    @property
    def approach(self):
        return min(1.,self.obstacle_age/self.travel_seconds)

    def advance(self,dt,actions):
        self.obstacle_age+=dt
        if self.approach>.72:
            self.dodged_held=self.dodged_held+dt if actions.matches(self.required,self.config.lean_threshold) else 0.
        if self.obstacle_age>=self.travel_seconds:
            if self.dodged_held>=.13:
                self.award(100+min(self.combo,10)*10,"CLEAN DODGE!")
            else:
                self.lives-=1
                self.miss("HIT!  FIND THE SAFE GAP")
            self.spawn()
        self.progress=self.elapsed/self.duration
        if self.lives<=0:
            self.finish(False)

    def success(self):
        return self.lives>0

    def on_pause(self):
        self.dodged_held=0.
