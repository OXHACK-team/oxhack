"""Common monotonic clock, pause semantics, scoring and events for arena games."""
import random
from motion_input import MotionInput


class TimedGame:
    game_id = "base"
    metric = "score"

    def __init__(self, config, now, rng=None, duration=None):
        self.config = config
        self.rng = rng or random.Random()
        self.duration = duration or config.arcade_seconds
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
        self._event("round_created", now)

    @property
    def remaining(self):
        return max(0., self.duration-self.elapsed)

    def _event(self, kind, now=None, **data):
        timestamp = self.last_update if now is None else now
        self.events.append({"event":kind,"monotonic_offset_s":round(timestamp-self.started_at,6),
                            "game_elapsed_s":round(self.elapsed,6),**data})

    def award(self, points, message="NICE!"):
        self.combo += 1
        self.best_combo = max(self.best_combo,self.combo)
        self.score += int(points)
        self.feedback, self.feedback_until = message, self.elapsed+.8
        self.feedback_kind="success"
        self._event("score",points=int(points),score=self.score,combo=self.combo)

    def miss(self, message="TRY THE NEXT ONE"):
        self.combo = 0
        self.violations += 1
        self.feedback, self.feedback_until = message, self.elapsed+.8
        self.feedback_kind="error"
        self._event("miss",count=self.violations)

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
        # Fixed maximum integration step prevents skipped impacts or beat deadlines.
        while dt>1e-8 and not self.finished:
            step=min(dt,1/60,self.remaining)
            self.elapsed+=step
            self.advance(step,actions or MotionInput())
            dt-=step
            if self.remaining<=1e-8 and not self.finished:
                self.finish(self.success())
        return self.events[before:]

    def on_pause(self):
        pass

    def advance(self, dt, actions):
        raise NotImplementedError

    def success(self):
        return self.score>=self.goal
