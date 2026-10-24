from games.timed import TimedGame


class Timekeeper(TimedGame):
    game_id="timekeeper"
    goal=650

    def __init__(self,config,now,rng=None):
        super().__init__(config,now,rng)
        self.period=config.beat_period_seconds
        self.beat_age=0.
        self.beat_number=1
        self.was_raised=False
        self.attempted=False
        self.hit=False
        self.last_error=None
        self.window=config.beat_window_seconds

    @property
    def target_time(self):
        return self.period*.76

    def advance(self,dt,actions):
        previous=self.beat_age
        self.beat_age+=dt
        if previous<self.target_time<=self.beat_age:
            self._event("beat_cue",beat=self.beat_number)
        rising=actions.raised and not self.was_raised
        self.was_raised=actions.raised
        if rising and not self.attempted:
            self.attempted=True
            error=abs(self.beat_age-self.target_time)
            self.last_error=error
            if error<=self.window:
                self.hit=True
                perfect=error<=self.window*.42
                self.award(150 if perfect else 100,"PERFECT SYNC!" if perfect else "IN SYNC!")
                self._event("beat_hit",absolute_game_timing_error_s=round(error,4))
            else:
                self.miss("TOO EARLY" if self.beat_age<self.target_time else "TOO LATE")
        if self.beat_age>=self.period:
            if not self.attempted:
                self.miss("RAISE A HAND WHEN THE RINGS MEET")
            self.beat_age-=self.period
            self.beat_number+=1
            if self.endless:
                self.period=self.pace(self.config.beat_period_seconds,1.8)
                self.window=self.pace(self.config.beat_window_seconds,.20)
            self.attempted=self.hit=False
            self._event("beat_started",beat=self.beat_number)
        self.progress=min(1.,self.score/self.goal)

    def on_pause(self):
        # Reacquisition cannot manufacture a fresh raising edge.
        self.was_raised=True

    def on_start(self,actions):
        self.was_raised=actions.raised
