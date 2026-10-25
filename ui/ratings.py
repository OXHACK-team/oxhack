"""Visible run medals based on actual survival and completed challenge results."""
from dataclasses import dataclass


MEDALS=(
    ("D","WARM UP",(170,187,201)),
    ("C","BRONZE",(226,159,105)),
    ("B","SILVER",(202,222,236)),
    ("A","GOLD",(255,210,111)),
    ("S","CHRONO MASTER",(162,135,255)),
)
MILESTONES=(20.,45.,90.,180.)


@dataclass(frozen=True)
class RunRating:
    grade: str
    title: str
    color: tuple
    progress: float
    next_target: str
    highlight: str


def rate_run(game):
    """No inferred reaction times or fabricated accuracy from the webcam."""
    score=max(0,getattr(game,"score",0))
    elapsed=max(0.,game.elapsed)
    misses=max(0,game.violations)
    hits=sum(e.get("event")=="score" for e in game.events)
    if game.game_id in ("red_green","sprint"):
        portals=max(0,getattr(game,"laps",int(game.won)))
        highlight=f"{portals} PORTALS CLEARED  /  {misses} MISSES"
    else:
        noun={"lightning":"ORBS CHARGED","dodge":"CLEAN DODGES","timekeeper":"BEATS CAUGHT","echo":"POSES MATCHED"}.get(game.game_id,"HITS")
        highlight=f"{hits} {noun}  /  BEST CHAIN {getattr(game,'best_combo',0)}"
    if getattr(game,"endless",False):
        qualifying=elapsed if score>0 else 0.
        index=sum(qualifying>=target for target in MILESTONES)
        if index==len(MILESTONES):
            progress=1.
            target="CHRONO MASTER / 180s SURVIVED"
        else:
            previous=0. if index==0 else MILESTONES[index-1]
            progress=max(0.,min(1.,(qualifying-previous)/(MILESTONES[index]-previous)))
            target=f"NEXT MEDAL: {MEDALS[index+1][1]} / {MILESTONES[index]:.0f}s"
    elif not game.won:
        index=0
        progress=max(0.,min(1.,getattr(game,"progress",0.)))
        target="FINISH THE CHALLENGE TO EARN A MEDAL"
    else:
        if game.metric=="time":
            fraction=elapsed/max(.001,game.duration)
            index=4 if fraction<=.35 else 3 if fraction<=.65 else 2 if fraction<=.85 else 1
        elif game.game_id=="dodge":
            index=4 if misses==0 else 3 if misses<=1 else 2 if misses<=3 else 1
        else:
            ratio=score/max(1,game.goal)
            index=4 if ratio>=2.5 else 3 if ratio>=1.75 else 2 if ratio>=1.25 else 1
        progress=1.
        target="CHALLENGE CLEARED / KEEP CHASING YOUR BEST"
    grade,title,color=MEDALS[index]
    return RunRating(grade,title,color,progress,target,highlight)
