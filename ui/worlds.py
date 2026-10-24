"""Six animated arena presentations, with perspective geometry and live mascots."""
import math
import pygame
from avatar import demonstration_pose
from motion_input import MotionInput
from tracking_types import neutral_pose
from ui.art import gradient
from ui.theme import *


def playfields(count):
    return [pygame.Rect(40,190,1360,574)] if count==1 else [pygame.Rect(40,190,668,574),pygame.Rect(732,190,668,574)]


def hand_area(rect):
    return pygame.Rect(rect.x+rect.width*.09,rect.y+150,rect.width*.82,350)


def glow(surface,center,radius,color):
    x,y=map(round,center)
    for i in range(4,0,-1):
        r=round(radius*(1+i*.18))
        pygame.draw.circle(surface,tuple(round(c*(.08+.045*(4-i))) for c in color),(x,y),r)
    pygame.draw.circle(surface,color,(x,y),round(radius))
    pygame.draw.circle(surface,tuple(min(255,c+45) for c in color),(x-round(radius*.2),y-round(radius*.22)),max(2,round(radius*.55)))


class Worlds:
    def __init__(self,app):
        self.a=app
        self.surfaces={}
        self.backgrounds={}

    def draw(self,destination,rect,game,slot,now):
        a=self.a
        w,h=rect.size
        if rect.size not in self.surfaces:
            self.surfaces[rect.size]=pygame.Surface(rect.size)
            bg=a.art.image("stadium",w,h,80).copy()
            bg.blit(gradient(w,h,110,140),(0,0))
            self.backgrounds[rect.size]=bg
        s=self.surfaces[rect.size]
        s.blit(self.backgrounds[rect.size],(0,0))
        color=CYAN if slot==0 else ORANGE
        actions=a.match.last_inputs[slot]
        pose=None
        neutral=None
        aspect=4/3
        if slot<a.match.human_count:
            player=a.bank.players[slot]
            pose=player.smoothed
            neutral=player.neutral
            aspect=a.bank.frames[slot].aspect if len(a.bank.frames)>slot else aspect
        else:
            name="RUN" if actions.run>.1 else "DUCK" if actions.crouch else "LEFT" if actions.lean<-.2 else "RIGHT" if actions.lean>.2 else "HANDS UP" if actions.left_up and actions.right_up else "LEFT HAND" if actions.left_up else "IDLE"
            pose=demonstration_pose(name,now)
            neutral=neutral_pose()
        self.floor(s,w,h,color,game.elapsed)
        key=game.game_id
        if key in ("red_green","sprint"):
            self.race(s,game,w,h,now,color)
            a.avatar.draw(s,pose,w*.5,250,244,aspect,now,slot>0,neutral,color)
        elif key=="lightning":
            a.avatar.draw(s,pose,w*.5,250,244,aspect,now,slot>0,neutral,color)
            self.lightning(s,game,w,h,actions,now,color)
        elif key=="dodge":
            self.dodge(s,game,w,h,now)
            x=w*.5+max(-.7,min(.7,actions.lean))*w*.23
            a.avatar.draw(s,pose,x,250,244,aspect,now,slot>0,neutral,color)
        elif key=="timekeeper":
            a.avatar.draw(s,pose,w*.25,252,240,aspect,now,slot>0,neutral,color)
            self.timekeeper(s,game,w,h,now)
        elif key=="echo":
            a.avatar.draw(s,pose,w*.27,248,245,aspect,now,slot>0,neutral,color)
            self.echo(s,game,w,h,now)
        self.hud(s,game,w,h,slot,now,color)
        if game.countdown>0 and not game.paused:
            self.countdown(s,game,w,h)
        elif game.finished:
            panel(s,(w*.18,230,w*.64,124),(12,32,44),GREEN if game.won else ORANGE,24)
            text(s,"RUN COMPLETE" if game.endless else "FINISHED!" if game.won else "TIME'S UP",(w*.5,272),40,GREEN if game.won else ORANGE,True,True)
            message="Other player still going / your score is safe" if len(a.match.games)>1 and not a.match.finished else f"{game.score:,} POINTS / RESULTS NEXT" if game.endless else "Your result is ready"
            fit_text(s,message,(w*.5,321),w*.60,18,MUTED,center=True)
        destination.blit(s,rect)
        pygame.draw.rect(destination,(73,104,123),rect,1,border_radius=17)

    def floor(self,s,w,h,color,elapsed):
        van=(w*.5,205)
        pygame.draw.polygon(s,(13,40,53),[(w*.36,215),(w*.64,215),(w+20,h),( -20,h)])
        for i in range(7):
            x=(i/6*w*1.45)-w*.225
            pygame.draw.line(s,(34,83,98),van,(x,h),2 if i in (0,6) else 1)
        for i in range(11):
            z=((i/11+elapsed*.035)%1)**1.8
            y=215+z*(h-215)
            left=w*.5-(w*.14+z*w*.6)
            right=w*.5+(w*.14+z*w*.6)
            pygame.draw.line(s,(36,77,91),(left,y),(right,y),1)
        pygame.draw.line(s,color,(w*.35,216),(-12,h),3)
        pygame.draw.line(s,color,(w*.65,216),(w+12,h),3)

    def race(self,s,g,w,h,now,color):
        racing=g.game_id=="sprint"
        light=color if racing else GREEN if g.phase=="GREEN" else RED
        radius=70+g.progress*110
        cx,cy=w*.5,240
        for delta,c in ((13,(17,40,54)),(7,(86,125,137)),(0,light),(-8,(183,218,216))):
            pygame.draw.circle(s,c,(round(cx),round(cy)),round(radius+delta),4 if delta==0 else 2)
        for i in range(12):
            angle=i*math.tau/12
            x,y=cx+math.sin(angle)*radius,cy+math.cos(angle)*radius
            x2,y2=cx+math.sin(angle)*(radius-8),cy+math.cos(angle)*(radius-8)
            pygame.draw.line(s,light,(x,y),(x2,y2),2)
        clock_icon(s,(round(cx),round(cy)),round(radius*.38),light,now*.8)
        if racing:
            message="TIME WARP! KEEP RUNNING" if g.boost else "JOG IN PLACE"
            if g.boost:
                for i in range(14):
                    angle=i*math.tau/14
                    r=radius+35+(now*90+i*13)%100
                    pygame.draw.line(s,ORANGE,(cx+math.sin(angle)*r,cy+math.cos(angle)*r),(cx+math.sin(angle)*(r+30),cy+math.cos(angle)*(r+30)),2)
        else:
            message="JOG IN PLACE" if g.phase=="GREEN" else "FREEZE" if not g.in_grace else "FREEZE / GET STILL"
            pill(s,g.phase+" LIGHT",(24,94),light,16)
            if g.elapsed<g.warning_until:
                panel(s,(w*.15,155,w*.7,53),(92,28,40),RED,14)
                fit_text(s,f"YOU MOVED / -{g.config.penalty_progress:.0%}",(w*.5,182),w*.65,25,RED,True,True)
        fit_text(s,message,(w*.5,143),w*.88,34,light,True,True)
        text(s,f"{g.progress*100:.0f}%",(w-80,h-62),30,light,True,center=True,mono=True)

    def lightning(self,s,g,w,h,actions,now,color):
        area=pygame.Rect(w*.09,150,w*.82,350)
        x,y=area.x+g.target[0]*area.width,area.y+g.target[1]*area.height
        glow(s,(x,y),25+math.sin(now*7)*3,ORANGE)
        ring(s,(round(x),round(y)),43,1-g.target_age/g.target_lifetime,ORANGE,4)
        # A readable bolt, two hand cursors and their dwell meters.
        pygame.draw.polygon(s,WHITE,[(x+3,y-18),(x-12,y+3),(x-1,y+3),(x-5,y+18),(x+13,y-5),(x+2,y-5)])
        for hand in (actions.left_hand,actions.right_hand):
            hx,hy=area.x+hand[0]*area.width,area.y+hand[1]*area.height
            pygame.draw.circle(s,(6,24,37),(round(hx),round(hy)),16)
            pygame.draw.circle(s,color,(round(hx),round(hy)),11,3)
            pygame.draw.circle(s,WHITE,(round(hx),round(hy)),4)
        fit_text(s,"TOUCH THE GLOWING ORB",(w*.5,126),w*.9,32,ORANGE,True,True)
        text(s,f"CHAIN x{g.combo}",(w-170,96),20,GREEN,True)

    def dodge(self,s,g,w,h,now):
        z=g.approach**2
        width=w*(.14+.75*z)
        height=42+200*z
        cx=w*.5
        bottom=235+240*z
        x,y=cx-width/2,bottom-height
        gap=width*.36
        col=(255,131,91)
        if g.required=="DUCK":
            blocks=[pygame.Rect(x,y,width,height*.5)]
            pygame.draw.rect(s,GREEN,(x+4,bottom-height*.43,width-8,height*.43),2,border_radius=3)
        else:
            blocks=[pygame.Rect(x+gap if g.required=="LEFT" else x,y,width-gap,height)]
            sx=x if g.required=="LEFT" else x+width-gap
            pygame.draw.rect(s,GREEN,(sx+2,y,gap-4,height),3,border_radius=4)
        for block in blocks:
            pygame.draw.rect(s,(104,53,44),block,border_radius=6)
            pygame.draw.rect(s,col,block,4,border_radius=6)
            for i in range(4):
                bx=block.x+block.width*(i+.5)/4
                pygame.draw.line(s,(165,82,58),(bx,block.top+8),(bx,block.bottom-8),2)
        label="DUCK DOWN" if g.required=="DUCK" else "LEAN "+g.required
        fit_text(s,label,(w*.5,130),w*.9,38,GREEN,True,True)
        text(s,f"IMPACT IN {max(0.,g.travel_seconds-g.obstacle_age):.1f}s",(w*.5,175),18,ORANGE,center=True,mono=True)
        for i in range(5):
            xx=33+i*28
            pygame.draw.polygon(s,CYAN if i<g.lives else EDGE,[(xx,100),(xx+9,105),(xx+7,117),(xx,123),(xx-7,117),(xx-9,105)])

    def timekeeper(self,s,g,w,h,now):
        center=(round(w*.69),315)
        target=67
        t=g.beat_age/g.target_time
        radius=round(max(24,167-t*100))
        near=abs(g.beat_age-g.target_time)<=g.window
        for i in range(24):
            angle=i*math.tau/24
            x,y=center[0]+math.sin(angle)*114,center[1]+math.cos(angle)*114
            pygame.draw.circle(s,(90,101,100),(round(x),round(y)),2)
        pygame.draw.circle(s,ORANGE,center,target,3)
        pygame.draw.circle(s,GREEN if near else (238,216,175),center,radius,6)
        clock_icon(s,center,33,ORANGE,now*.3)
        fit_text(s,"RAISE A HAND NOW!" if near else "LOWER. WATCH THE RINGS.",(w*.5,129),w*.9,31,GREEN if near else WHITE,True,True)
        text(s,"RINGS MEET = RAISE",(center[0],465),17,ORANGE,True,True)

    def echo(self,s,g,w,h,now):
        watching=g.stage=="WATCH"
        pose=g.sequence[g.shown_index] if watching else "IDLE"
        self.a.avatar.draw(s,demonstration_pose(pose,now),w*.74,248,245,4/3,now,True,neutral=neutral_pose(),color=PURPLE)
        if watching:
            message="WATCH: "+pose
        elif g.stage=="COMPLETE":
            message="ALL TIME ECHOES MASTERED!"
        elif g.stage=="REST":
            message="ECHO COMPLETE! NEXT SEQUENCE..."
        else:
            message=f"REPEAT POSE {g.step_index+1} OF {len(g.sequence)}"
            text(s,"?",(w*.74,218),47,PURPLE,True,True)
        fit_text(s,message,(w*.5,128),w*.93,31,PURPLE,True,True)
        box=44
        start=w/2-len(g.sequence)*(box+10)/2
        for i,value in enumerate(g.sequence):
            rect=pygame.Rect(start+i*(box+10),169,box,34)
            active=(watching and g.shown_index==i) or (not watching and i<g.step_index)
            panel(s,rect,(54,52,89) if active else (20,32,47),PURPLE if active else EDGE,9)
            label={"LEFT":"<","RIGHT":">","DUCK":"v","HANDS UP":"UP"}[value] if watching or i<g.step_index else "?"
            text(s,label,rect.center,18,WHITE,True,True)
        text(s,"YOU",(w*.27,521),16,CYAN,True,True)
        text(s,"YOUR TIME ECHO",(w*.74,521),16,PURPLE,True,True)
        if g.stage=="REPEAT":
            ring(s,(round(w*.27),round(228)),20,g.pose_held/g.config.pose_hold_seconds,PURPLE,4)

    def hud(self,s,g,w,h,slot,now,color):
        name=self.a.match.names[slot]
        pill(s,name.upper(),(21,19),color,15)
        panel(s,(w-146,17,125,72),(9,26,41),EDGE,14)
        text(s,"SURVIVED" if g.endless else "SECONDS",(w-126,28),12,MUTED,mono=True)
        text(s,f"{g.elapsed if g.endless else g.remaining:04.1f}",(w-129,46),30,WHITE,True,mono=True)
        if g.metric=="score":
            text(s,f"{g.score:,} PTS",(24,65),26,WHITE,True)
        else:
            text(s,f"{g.elapsed:.1f}s ELAPSED",(24,65),18,MUTED,mono=True)
        if hasattr(g,"feedback_until") and g.elapsed<g.feedback_until:
            y=225 if g.game_id=="echo" else h-79 if g.endless and g.game_id in ("sprint","red_green") else h-63 if g.endless else h-52
            fit_text(s,g.feedback,(w*.5,y),w*.8,24,RED if g.feedback_kind=="error" else GREEN,True,True)
        if g.endless:
            text(s,f"LEVEL {g.level:02d}",(24,h-31),17,color,True,mono=True)
            for i in range(g.max_lives):
                pygame.draw.circle(s,GREEN if i<g.lives else EDGE,(w-34-i*24,h-24),7,0 if i<g.lives else 2)
            if g.game_id in ("sprint","red_green"):
                panel(s,(w*.28,h-28,w*.42,8),(51,76,91),None,4)
                pygame.draw.rect(s,GREEN if g.energy>30 else ORANGE,(w*.28,h-28,max(2,w*.42*g.energy/100),8),border_radius=4)
                text(s,"TIME ENERGY",(w*.49,h-42),11,MUTED,center=True,mono=True)
            if g.elapsed<g.level_until:
                pill(s,"TIME ACCELERATES / LEVEL "+str(g.level),(w//2-146,19),ORANGE,13)
        elif g.game_id!="echo":
            panel(s,(24,h-25,w-48,7),(51,76,91),None,4)
            if g.progress:
                pygame.draw.rect(s,color,(24,h-25,max(5,(w-48)*g.progress),7),border_radius=4)

    def countdown(self,s,g,w,h):
        shade=pygame.Surface((w,h),pygame.SRCALPHA)
        shade.fill((6,20,34,130))
        s.blit(shade,(0,0))
        ring(s,(w//2,300),77,1-(g.countdown%1),ORANGE,6)
        text(s,str(max(1,math.ceil(g.countdown))),(w//2,296),90,WHITE,True,True)
        text(s,"GET READY",(w//2,410),28,WHITE,True,True)
