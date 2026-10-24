"""Identical seeded challenges for solo, two live players, and a local AI rival."""
import random
from games import GAMES
from ai_opponent import AIController
from motion_input import MotionInput


def update_game(game,now,actions,valid):
    if game.game_id=="red_green":
        return game.update(now,actions.run,actions.motion,valid)
    return game.update(now,actions,valid)


def ranking_key(game):
    if getattr(game,"endless",False):
        return (game.score,round(game.elapsed,3),-game.violations)
    if game.metric=="time":
        return (int(game.won),-game.elapsed if game.won else game.progress)
    return (int(game.won),game.score,-game.violations)


class Match:
    def __init__(self,config,game_id,mode,now,names=None,seed=1,difficulty="normal"):
        self.game_id,self.mode=game_id,mode
        self.human_count=2 if mode=="duo" else 1
        self.names=names or ([config.player_name,"Player 2"] if mode=="duo" else [config.player_name])
        if mode=="ai":
            self.names=list(self.names)+["NOVA / AI"]
        self.games=[GAMES[game_id]["factory"](config,now,rng=random.Random(seed)) for _ in self.names]
        self.brain=AIController(difficulty,seed+404) if mode=="ai" else None
        self.manual_pause=False
        self.seed=seed
        self.last_inputs=[MotionInput() for _ in self.games]
        self.last_update=now
        self.recovery_countdown=0.
        self.recovering=False

    @property
    def finished(self):
        return all(g.finished for g in self.games)

    @property
    def paused(self):
        return self.manual_pause or self.recovery_countdown>0 or any(g.paused for g in self.games if not g.finished)

    @property
    def winner_indices(self):
        best=max(ranking_key(g) for g in self.games)
        return [i for i,g in enumerate(self.games) if ranking_key(g)==best]

    def update(self,now,inputs,validity):
        dt=max(0.,now-self.last_update)
        self.last_update=now
        reliable=not self.manual_pause and all(validity[i] or self.games[i].finished for i in range(self.human_count))
        if not reliable:
            self.recovering=True
            self.recovery_countdown=0.
        elif self.recovering:
            self.recovering=False
            self.recovery_countdown=2. if any(g.elapsed>0 and not g.finished for g in self.games) else 0.
        elif self.recovery_countdown>0:
            self.recovery_countdown=max(0.,self.recovery_countdown-dt)
        reliable=reliable and self.recovery_countdown==0
        events=[]
        for i,game in enumerate(self.games):
            actions=inputs[i] if i<self.human_count else self.brain.act(game)
            self.last_inputs[i]=actions
            events.extend((i,event) for event in update_game(game,now,actions,reliable))
        if self.brain and self.games[0].endless and self.games[0].finished and not self.games[1].finished:
            self.games[1].finish(False)
        return events
