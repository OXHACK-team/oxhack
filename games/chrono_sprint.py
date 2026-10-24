from games.timed import TimedGame


class ChronoSprint(TimedGame):
    game_id="sprint"
    metric="time"
    goal=1

    def __init__(self,config,now,rng=None):
        super().__init__(config,now,rng,duration=config.sprint_seconds)
        self.boost=False

    def advance(self,dt,actions):
        self.boost=int(self.elapsed)%8>=5 and actions.run>.65
        speed=.07*(1.6 if self.boost else 1.)
        self.progress=min(1.,self.progress+actions.run*speed*dt)
        self.score=int(self.progress*10000)
        if self.progress>=1.-1e-8:
            self.progress=1.
            self.finish(True)
