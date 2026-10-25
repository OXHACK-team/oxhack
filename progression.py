"""Local, earned progression. Demo and webcam profiles use separate records."""
import math


def xp_for(game):
    if not game.finished or game.elapsed<8 or (game.score<=0 and not game.won):
        return 0
    survival=int(min(600.,game.elapsed)/4.)
    performance=min(180,int(math.sqrt(max(0,game.score))*.55))
    precision=max(0,35-game.violations*5)
    return 20+survival+performance+precision+(40 if game.won else 0)


def profile_for(xp,runs=0):
    xp=max(0,int(xp))
    remaining=xp
    level=1
    required=100
    while remaining>=required and level<100:
        remaining-=required
        level+=1
        required=100+(level-1)*60
    title="TIME ROOKIE" if level<3 else "TIME RUNNER" if level<6 else "CHRONO ACE" if level<10 else "TIME MASTER" if level<20 else "ARENA LEGEND"
    return {"level":level,"title":title,"xp":xp,"level_xp":remaining,
            "next_level_xp":required,"progress":min(1.,remaining/required),"runs":int(runs)}
