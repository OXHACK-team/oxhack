from games.timed import TimedGame

POSES=["LEFT","RIGHT","DUCK","HANDS UP"]


class EchoShift(TimedGame):
    game_id="echo"
    metric="time"
    goal=900

    def __init__(self,config,now,rng=None):
        super().__init__(config,now,rng,duration=config.echo_seconds)
        self.round=0
        self.stage="WATCH"
        self.stage_age=0.
        self.pose_held=0.
        self.step_index=0
        self.sequence=[]
        self.new_sequence()

    def new_sequence(self):
        self.round+=1
        self.sequence=[]
        length=min(6,2+(self.round-1)//2) if self.endless else self.round+1
        self.show_seconds=self.pace(1.05,.80) if self.endless else 1.05
        self.repeat_seconds=max(5.,length*self.pace(3.,2.)) if self.endless else 12.
        for _ in range(length):
            self.sequence.append(self.rng.choice([p for p in POSES if not self.sequence or p!=self.sequence[-1]]))
        self.stage="WATCH"
        self.stage_age=self.pose_held=0.
        self.step_index=0
        self._event("echo_sequence",sequence=list(self.sequence),round=self.round)

    @property
    def shown_index(self):
        return min(len(self.sequence)-1,int(self.stage_age/self.show_seconds))

    @property
    def expected(self):
        return self.sequence[self.step_index]

    def advance(self,dt,actions):
        self.stage_age+=dt
        if self.stage=="WATCH":
            if self.stage_age>=len(self.sequence)*self.show_seconds+.45:
                self.stage="REPEAT"
                self.stage_age=0.
                self._event("echo_repeat",round=self.round)
        elif self.stage=="REPEAT":
            self.pose_held=self.pose_held+dt if actions.matches(self.expected,self.config.lean_threshold) else 0.
            if self.pose_held>=self.config.pose_hold_seconds:
                self.award(100,"ECHO MATCHED!")
                self.step_index+=1
                self.pose_held=0.
                if self.step_index==len(self.sequence):
                    if self.round>=3 and not self.endless:
                        self.stage="COMPLETE"
                        self.finish(True)
                    else:
                        self.stage="REST"
                        self.stage_age=0.
            elif self.stage_age>self.repeat_seconds:
                self.miss("TIME ECHO LOST. WATCH AGAIN.")
                self.stage="WATCH"
                self.stage_age=0.
                self.step_index=0
        elif self.stage=="REST" and self.stage_age>=1.:
            self.new_sequence()
        self.progress=min(1.,self.score/self.goal)

    def on_pause(self):
        pass  # earned pose holds freeze with the recall clock

    def success(self):
        return False
