"""Six complete games, one vocabulary, one navigation and match system."""
from games.red_light_green_light import RedLightGreenLight
from games.lightning_strike import LightningStrike
from games.dodge_or_die import DodgeOrDie
from games.chrono_sprint import ChronoSprint
from games.timekeeper import Timekeeper
from games.echo_shift import EchoShift

GAME_CARDS=[
    dict(id="red_green",title="RED LIGHT, GREEN LIGHT",short="RED / GREEN",tag="MASTER STILLNESS",color=(164,239,121),
         description="Race on green. Become a statue on red.",control="JOG + FREEZE",theme="Timing your movement",art=0,factory=RedLightGreenLight,
         rules=["Jog in place on GREEN. Alternate your knees.","Freeze on RED. Moving costs race progress.","Reach the portal before the clock reaches zero."],metric="time"),
    dict(id="lightning",title="LIGHTNING STRIKE",short="LIGHTNING STRIKE",tag="CHASE THE MOMENT",color=(255,195,96),
         description="Reach for energy before its time runs out.",control="REACH WITH EITHER HAND",theme="Act before the moment expires",art=1,factory=LightningStrike,
         rules=["Move either hand onto the glowing energy orb.","Hold briefly to charge it before it disappears.","Chain hits for bonus points. Aim for 1,200."],metric="score"),
    dict(id="dodge",title="DODGE OR DIE",short="DODGE OR DIE",tag="SEE THE FUTURE",color=(93,218,233),
         description="Read the incoming wall. Find your escape.",control="LEAN LEFT / RIGHT + DUCK",theme="Anticipate the next second",art=2,factory=DodgeOrDie,
         rules=["Watch the wall and the large movement prompt.","Lean LEFT, lean RIGHT or DUCK before impact.","Survive the clock. You have five shields."],metric="score"),
    dict(id="sprint",title="CHRONO SPRINT",short="CHRONO SPRINT",tag="OUTRUN YOUR PAST",color=(255,143,100),
         description="An all-out sprint through a clockwork world.",control="JOG IN PLACE",theme="Beat your previous completion time",art=3,factory=ChronoSprint,
         rules=["Jog in place and alternate your knees.","Build speed during the glowing TIME WARP windows.","Reach the finish as fast as you can."],metric="time"),
    dict(id="timekeeper",title="TIMEKEEPER",short="TIMEKEEPER",tag="FIND YOUR RHYTHM",color=(241,200,112),
         description="Feel the rhythm. Catch the perfect instant.",control="RAISE + LOWER A HAND",theme="Synchronize with a repeating beat",art=4,factory=Timekeeper,
         rules=["Watch the shrinking ring approach the fixed ring.","RAISE a hand when the two rings meet.","LOWER between beats. Aim for 650 points."],metric="score"),
    dict(id="echo",title="ECHO SHIFT",short="ECHO SHIFT",tag="REMEMBER THE PAST",color=(186,155,255),
         description="Watch your time echo. Recreate its moves.",control="LEAN + DUCK + HANDS UP",theme="Turn short-term memory into movement",art=5,factory=EchoShift,
         rules=["WATCH the robot demonstrate a short pose sequence.","REPEAT those poses in the same order. Hold each briefly.","Complete sequences of 2, 3 and 4 poses as fast as you can."],metric="time"),
]
for card in GAME_CARDS:
    card["enabled"]=True
GAMES={card["id"]:card for card in GAME_CARDS}

MODES={
    "solo":("SOLO","One player. Your next personal best."),
    "ai":("AI RIVAL","Race NOVA, an offline computer opponent."),
    "duo":("2 PLAYERS","Two people, one camera, play side by side."),
    "party":("PARTY / 2-4","Take turns. Same challenge. One winner."),
}
