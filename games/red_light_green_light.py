"""Pure game state. All clocks are supplied by the caller for reproducible tests."""
import random
from games.timed import TimedGame
from motion_input import MotionInput


class RedLightGreenLight(TimedGame):
    game_id="red_green"
    metric="time"
    goal=1
    def __init__(self, config, now, rng=None):
        self.endless=config.endless
        if self.endless:
            super().__init__(config,now,rng)
        self.config = config
        self.rng = rng or random.Random()
        self.started_at = self.last_update = now
        self.elapsed = 0.
        self.countdown = 3.
        self.phase = "GREEN"
        self.phase_elapsed = 0.
        self.phase_duration = self.rng.uniform(*config.green_seconds)
        self.progress = 0.
        self.violations = 0
        self.finished = self.won = False
        self.paused = False
        self.motion_high = False
        self.motion_held = 0.
        self.last_penalty = -99.
        self.warning_until = -1.
        self.phase_number=1
        self.phase_penalized=False
        self.events = []
        self._event("round_created", now)

    @property
    def score(self):
        return self._score if self.endless else int(self.progress*10000)

    @score.setter
    def score(self,value):
        self._score=value

    @property
    def duration(self):
        return self.config.time_limit_seconds

    @property
    def remaining(self):
        return 0. if self.endless else max(0., self.config.time_limit_seconds - self.elapsed)

    @property
    def in_grace(self):
        return self.phase == "RED" and self.phase_elapsed < self.config.red_grace_seconds

    def _event(self, kind, now=None, **extra):
        now=self.last_update if now is None else now
        self.events.append({"event": kind, "monotonic_offset_s": round(now - self.started_at, 6),
                            "game_elapsed_s": round(self.elapsed, 6), **extra})

    def update(self, now, run_score, motion_score, tracking_ok=True, time_power=False):
        if self.endless:
            return super().update(now,MotionInput(run=run_score,motion=motion_score,time_power=time_power),tracking_ok)
        dt = max(0., now - self.last_update)
        self.last_update = now
        if self.finished:
            return []
        before = len(self.events)
        if not tracking_ok:
            if not self.paused:
                self._event("tracking_paused", now)
            self.paused = True
            self.motion_held = 0.
            self.motion_high = False
            return self.events[before:]
        if self.paused:
            self.paused = False
            # Discard the interval ending at reacquisition; no catch-up or false penalty.
            self._event("tracking_resumed", now)
            return self.events[before:]
        if self.countdown > 0:
            consumed=min(self.countdown,dt)
            self.countdown = max(0., self.countdown - consumed)
            dt-=consumed
            if self.countdown == 0:
                self._event("phase_green", now-dt)
            if dt<=1e-9:
                return self.events[before:]
        dt = min(dt, self.remaining)
        # Split elapsed intervals at phase boundaries, rather than awarding old-phase
        # progress to a new light after a long render frame.
        cursor = now - dt
        while dt > 1e-9 and not self.finished:
            segment = min(dt, self.phase_duration - self.phase_elapsed)
            was_in_grace=self.in_grace
            if was_in_grace:
                segment=min(segment,self.config.red_grace_seconds-self.phase_elapsed)
            speed=max(0.,min(1.,run_score))*self.config.forward_speed
            if self.phase=="GREEN" and speed>0:
                segment=min(segment,(1.-self.progress)/speed)
            self.elapsed += segment
            self.phase_elapsed += segment
            cursor += segment
            if self.phase == "GREEN":
                self.progress = min(1., self.progress + speed * segment)
                if self.progress>=1.-1e-9:
                    self.progress=1.
                self.motion_held = 0.
                self.motion_high = False
            else:
                if not was_in_grace:
                    self.motion_high = motion_score > (self.config.red_motion_exit if self.motion_high else self.config.red_motion_enter)
                    self.motion_held = self.motion_held + segment if self.motion_high else 0.
                    if self.motion_held >= self.config.red_motion_hold_seconds and self.elapsed - self.last_penalty >= self.config.penalty_cooldown_seconds:
                        self.violations += 1
                        self.progress = max(0., self.progress - self.config.penalty_progress)
                        self.last_penalty = self.elapsed
                        self.warning_until = self.elapsed + 1.15
                        self.motion_held = 0.
                        self._event("red_violation", cursor, motion_score=round(float(motion_score), 4), progress=round(self.progress, 4))
            dt -= segment
            if self.progress >= 1. or self.remaining <= 1e-8:
                self.finished = True
                self.won = self.progress >= 1.
                self._event("win" if self.won else "lose", cursor, violations=self.violations)
            elif self.phase_elapsed >= self.phase_duration - 1e-8:
                self.phase = "RED" if self.phase == "GREEN" else "GREEN"
                self.phase_number+=1
                self.phase_elapsed = 0.
                self.phase_duration = self.rng.uniform(*(self.config.red_seconds if self.phase == "RED" else self.config.green_seconds))
                self.motion_held = 0.
                self.motion_high = False
                self._event("phase_red" if self.phase == "RED" else "phase_green", cursor)
        return self.events[before:]

    def advance(self,dt,actions):
        self.phase_elapsed+=dt
        if self.phase=="GREEN":
            self.running_energy(dt,actions,self.pace(3.2,6.8))
            self.progress=min(1.,self.progress+max(0.,min(1.,actions.run))*self.config.forward_speed*dt)
            if self.progress>=1.-1e-8:
                self.laps+=1
                self.progress=0.
                self.energy=min(100.,self.energy+15.)
                self.award(1000,"PORTAL CLEARED / KEEP GOING!")
                self._event("checkpoint",lap=self.laps)
        elif not self.in_grace and not self.phase_penalized:
            self.motion_high=actions.motion>(self.config.red_motion_exit if self.motion_high else self.config.red_motion_enter)
            self.motion_held=self.motion_held+dt if self.motion_high else 0.
            if self.motion_held>=self.config.red_motion_hold_seconds:
                self.phase_penalized=True
                if self.miss("YOU MOVED / ONE SHIELD LOST"):
                    self.progress=max(0.,self.progress-self.config.penalty_progress)
                    self.warning_until=self.elapsed+1.15
                    self._event("red_violation",motion_score=round(actions.motion,4))
        if self.phase_elapsed>=self.phase_duration:
            self.phase="RED" if self.phase=="GREEN" else "GREEN"
            self.phase_number+=1
            self.phase_elapsed=0.
            lo,hi=self.config.red_seconds if self.phase=="RED" else self.config.green_seconds
            self.phase_duration=max(1.4,self.rng.uniform(lo,hi)*self.pace(1.,.6))
            self.motion_held=0.
            self.motion_high=False
            self.phase_penalized=False
            self._event("phase_red" if self.phase=="RED" else "phase_green")

    def on_pause(self):
        self.motion_held=0.
        self.motion_high=False

    def on_start(self,actions):
        self._event("phase_green")
