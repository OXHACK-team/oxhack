"""Common monotonic clock, pause semantics, scoring and events for arena games."""
import random
from motion_input import MotionInput


class TimedGame:
    game_id = "base"
    metric = "score"

    def __init__(self, config, now, rng=None, duration=None):
        self.config = config
        self.endless = config.endless
        if self.endless:
            self.metric = "score"
        self.rng = rng or random.Random()
        self._duration = duration or config.arcade_seconds
        self.started_at = self.last_update = now
        self.elapsed = 0.
        self.countdown = 3.
        self.score = 0
        self.progress = 0.
        self.violations = 0
        self.combo = 0
        self.best_combo = 0
        self.finished = self.won = self.paused = False
        self.feedback = "GET READY"
        self.feedback_until = 0.
        self.feedback_kind = "success"
        self.events = []
        self.level = 1
        self.max_lives = 5 if self.game_id == "dodge" else 3
        self.lives = self.max_lives
        self.laps = 0
        self.energy = 100.
        self.distance_score = 0.
        self.level_until = 0.
        self._event("round_created", now)

    @property
    def difficulty(self):
        # Continuous and bounded: no sudden speed jumps and no impossible tempos.
        import math
        return 1. - math.exp(-self.elapsed / 100.)

    def pace(self, start, floor):
        return start + (floor-start)*self.difficulty

    @property
    def duration(self):
        return self._duration

    @property
    def remaining(self):
        return 0. if self.endless else max(0., self.duration-self.elapsed)

    def _event(self, kind, now=None, **data):
        timestamp = self.last_update if now is None else now
        self.events.append({"event":kind,"monotonic_offset_s":round(timestamp-self.started_at,6),
                            "game_elapsed_s":round(self.elapsed,6),**data})

    def award(self, points, message="NICE!"):
        self.combo += 1
        self.best_combo = max(self.best_combo,self.combo)
        points = round(points * (min(3., 1.+.12*(self.level-1)) if self.endless else 1.))
        self.score += int(points)
        self.feedback, self.feedback_until = message, self.elapsed+.8
        self.feedback_kind="success"
        self._event("score",points=int(points),score=self.score,combo=self.combo)
        if self.endless and self.combo % 12 == 0 and self.lives < self.max_lives:
            self.lives += 1
            self.feedback = "12 HIT CHAIN / SHIELD RESTORED!"
            self._event("shield_restored",lives=self.lives)

    def miss(self, message="TRY THE NEXT ONE"):
        self.combo = 0
        self.violations += 1
        self.feedback, self.feedback_until = message, self.elapsed+.8
        self.feedback_kind="error"
        self._event("miss",count=self.violations)
        if self.endless:
            self.lives=max(0,self.lives-1)
            if self.lives==0:
                self.finish(False)

    def running_energy(self, dt, actions, drain):
        self.energy = min(100., max(0., self.energy + (actions.run*13.-drain)*dt))
        self.distance_score += max(0.,actions.run)*dt*65*(1.+self.difficulty)
        amount=int(self.distance_score)
        self.score+=amount
        self.distance_score-=amount
        if self.energy<=0:
            self.miss("TIME ENERGY EMPTY / KEEP JOGGING")
            self.energy=70.

    def finish(self, won):
        if self.finished:
            return
        self.finished,self.won=True,bool(won)
        self._event("win" if self.won else "lose",score=self.score,violations=self.violations)

    def update(self, now, actions=None, tracking_ok=True):
        dt=max(0.,now-self.last_update)
        self.last_update=now
        before=len(self.events)
        if self.finished:
            return []
        if not tracking_ok:
            if not self.paused:
                self._event("tracking_paused")
            self.paused=True
            self.on_pause()
            return self.events[before:]
        if self.paused:
            self.paused=False
            self._event("tracking_resumed")
            return self.events[before:]
        if self.countdown:
            used=min(dt,self.countdown)
            self.countdown=max(0.,self.countdown-used)
            dt-=used
            if self.countdown==0:
                self._event("round_started",now-dt)
                self.on_start(actions or MotionInput())
        if self.endless:
            # A stalled render frame is not extra reaction time for the engine:
            # discard excess wall time rather than resolving unseen obstacles.
            dt=min(dt,.1)
        # Fixed maximum integration step prevents skipped impacts or beat deadlines.
        while dt>1e-8 and not self.finished:
            step=min(dt,1/60) if self.endless else min(dt,1/60,self.remaining)
            self.elapsed+=step
            if self.endless:
                level=1+int(self.elapsed/25.)
                if level>self.level:
                    self.level=level
                    self.level_until=self.elapsed+2.
                    self._event("level_up",level=self.level)
            self.advance(step,actions or MotionInput())
            dt-=step
            if not self.endless and self.remaining<=1e-8 and not self.finished:
                self.finish(self.success())
        return self.events[before:]

    def on_pause(self):
        pass

    def on_start(self, actions):
        pass

    def advance(self, dt, actions):
        raise NotImplementedError

    def success(self):
        return self.score>=self.goal
