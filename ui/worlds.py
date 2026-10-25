"""Distinct clockwork sports arenas with cheap perspective geometry and live avatars."""
from collections import deque
import math
import pygame
from avatar import demonstration_pose
from tracking_types import neutral_pose
from ui.art import gradient
from ui.theme import *
from ui.world_geometry import blend,polygon_ring,prism,chevron,shield


def playfields(count):
    return [pygame.Rect(40,190,1360,574)] if count==1 else [pygame.Rect(40,190,668,574),pygame.Rect(732,190,668,574)]


def hand_area(rect):
    # Shared with simulated input and effects. This is a gameplay coordinate space.
    return pygame.Rect(rect.x+rect.width*.09,rect.y+150,rect.width*.82,350)


PALETTES={
    "red_green":((49,101,98),(111,217,166),"THE CHRONOGATE"),
    "sprint":((58,80,117),(255,166,105),"INFINITE EXPRESS"),
    "lightning":((58,68,104),(255,204,111),"THE ENERGY VAULT"),
    "dodge":((35,88,103),(82,229,234),"THE FRACTURE RUN"),
    "timekeeper":((91,69,105),(255,213,131),"THE CELESTIAL CLOCK"),
    "echo":((67,57,115),(180,149,255),"THE MEMORY CHAMBER"),
}


def glow(surface,center,radius,color):
    x,y=map(round,center)
    for i in range(4,0,-1):
        r=round(radius*(1+i*.18))
        pygame.draw.circle(surface,tuple(round(c*(.08+.045*(4-i))) for c in color),(x,y),r)
    pygame.draw.circle(surface,color,(x,y),round(radius))
    pygame.draw.circle(surface,tuple(min(255,c+45) for c in color),(x-round(radius*.2),y-round(radius*.22)),max(2,round(radius*.42)))


class Worlds:
    def __init__(self,app):
        self.a=app
        self.surfaces={}
        self.backgrounds={}
        self.trails={}
        self.trail_stamps={}
        self.match_id=None

    @property
    def reduced_motion(self):
        return getattr(self.a.config,"reduced_motion",False)

    def background(self,key,w,h):
        cache=(key,w,h)
        if cache in self.backgrounds:
            return self.backgrounds[cache]
        base,accent,_=PALETTES[key]
        s=self.a.art.image("stadium",w,h,105).copy()
        tint=pygame.Surface((w,h),pygame.SRCALPHA)
        tint.fill((*base,55))
        s.blit(tint,(0,0))
        s.blit(gradient(w,h,65,220),(0,0))
        # The arena is built into the stadium: stepped retaining walls and solid
        # support towers, rather than a flat wireframe floating over a picture.
        for side in (-1,1):
            for i in range(4):
                z=(i+1)/5
                y=215+z*z*240
                x=w*.5+side*(w*.18+z*w*.34)
                width=10+z*31
                height=24+z*105
                r=pygame.Rect(x-width/2,y-height,width,height)
                prism(s,r,blend(base,(103,133,146),.25),5+z*10,blend(accent,(12,29,40),.55))
                pygame.draw.rect(s,blend(accent,(14,28,42),.25),(r.x+r.width*.35,r.y+8,max(2,r.width*.12),r.height*.67),border_radius=2)
        # A dark protective HUD band is baked once, keeping all stats readable.
        shade=pygame.Surface((w,104),pygame.SRCALPHA)
        shade.fill((5,16,29,215))
        s.blit(shade,(0,0))
        pygame.draw.line(s,blend(accent,(9,24,38),.7),(0,103),(w,103))
        self.backgrounds[cache]=s
        return s

    def draw(self,destination,rect,game,slot,now):
        a=self.a
        w,h=rect.size
        if rect.size not in self.surfaces:
            self.surfaces[rect.size]=pygame.Surface(rect.size)
        s=self.surfaces[rect.size]
        key=game.game_id
        s.blit(self.background(key,w,h),(0,0))
        color=CYAN if slot==0 else ORANGE
        _,accent,_=PALETTES[key]
        actions=a.match.last_inputs[slot]
        pose=neutral=None
        aspect=4/3
        if slot<a.match.human_count:
            player=a.bank.players[slot]
            pose,neutral=player.smoothed,player.neutral
            aspect=a.bank.frames[slot].aspect if len(a.bank.frames)>slot else aspect
        else:
            name="TIME SHIELD" if getattr(actions,"time_power",False) else "RUN" if actions.run>.1 else "DUCK" if actions.crouch else "LEFT" if actions.lean<-.2 else "RIGHT" if actions.lean>.2 else "HANDS UP" if actions.left_up and actions.right_up else "LEFT HAND" if actions.left_up else "IDLE"
            pose,neutral=demonstration_pose(name,now),neutral_pose()
        if id(a.match)!=self.match_id:
            self.match_id=id(a.match)
            self.trails.clear()
            self.trail_stamps.clear()
        ambient=0. if self.reduced_motion else game.elapsed
        self.floor(s,w,h,accent,ambient,key,actions.run)
        if key in ("red_green","sprint"):
            self.race(s,game,w,h,ambient,color)
            a.avatar.draw(s,pose,w*.5,250,244,aspect,now,slot>0,neutral,color)
        elif key=="lightning":
            self.energy_vault(s,w,h,ambient,accent)
            a.avatar.draw(s,pose,w*.5,250,244,aspect,now,slot>0,neutral,color)
            self.lightning(s,game,w,h,actions,ambient,color,slot)
        elif key=="dodge":
            self.dodge(s,game,w,h,ambient)
            x=w*.5+max(-.7,min(.7,actions.lean))*w*.23
            a.avatar.draw(s,pose,x,250,244,aspect,now,slot>0,neutral,color)
        elif key=="timekeeper":
            self.platform(s,(w*.25,505),75,color)
            a.avatar.draw(s,pose,w*.25,252,240,aspect,now,slot>0,neutral,color)
            self.timekeeper(s,game,w,h,ambient)
        elif key=="echo":
            self.platform(s,(w*.27,505),78,color)
            self.platform(s,(w*.74,505),78,PURPLE)
            a.avatar.draw(s,pose,w*.27,248,245,aspect,now,slot>0,neutral,color)
            self.echo(s,game,w,h,ambient)
        if getattr(game,"time_power_active",False) and not game.finished:
            cx=w*(.25 if key=="timekeeper" else .27 if key=="echo" else .5)
            if key=="dodge":
                cx+=max(-.7,min(.7,actions.lean))*w*.23
            pulse=0. if self.reduced_motion else math.sin(game.elapsed*4.)*3.
            field=pygame.Rect(0,0,194+pulse,287+pulse)
            field.center=(round(cx),382)
            pygame.draw.ellipse(s,(62,61,115),field.inflate(10,10),2)
            pygame.draw.ellipse(s,PURPLE,field,2)
            for angle in (-.8,.8,2.3,3.9):
                px=field.centerx+math.sin(angle)*field.width/2
                py=field.centery+math.cos(angle)*field.height/2
                pygame.draw.circle(s,CYAN,(round(px),round(py)),4)
        self.hud(s,game,w,h,slot,now,color)
        if game.countdown>0 and not game.paused:
            self.countdown(s,game,w,h)
        elif game.finished:
            panel(s,(w*.12,235,w*.76,132),(8,23,39),GREEN if game.won else ORANGE,22)
            fit_text(s,"RUN COMPLETE" if game.endless else "FINISHED!" if game.won else "TIME'S UP",(w*.5,276),w*.7,39,GREEN if game.won else ORANGE,True,True)
            message="Other player still going / your score is safe" if len(a.match.games)>1 and not a.match.finished else f"{game.score:,} POINTS / RESULTS NEXT" if game.endless else "Your result is ready"
            fit_text(s,message,(w*.5,328),w*.70,18,MUTED,center=True)
        destination.blit(s,rect)
        pygame.draw.rect(destination,blend(accent,(45,65,84),.55),rect,1,border_radius=17)
        # A short highlight joins the top edge, like a lit physical console frame.
        pygame.draw.line(destination,accent,(rect.x+18,rect.y),(rect.x+min(rect.width*.32,215),rect.y),2)

    def floor(self,s,w,h,color,elapsed,key="sprint",run=0.):
        van=(w*.5,221)
        pygame.draw.polygon(s,(8,23,36),[(w*.36,218),(w*.64,218),(w+20,h),(-20,h)])
        speed=.027+min(1.,run)*.035 if key in ("sprint","red_green") else .018
        for i in range(8):
            z=((i/8+elapsed*speed)%1)**1.75
            next_z=min(1.,z+.022+z*.055)
            y,y2=221+z*(h-221),221+next_z*(h-221)
            left,right=w*.5-(w*.13+z*w*.59),w*.5+(w*.13+z*w*.59)
            left2,right2=w*.5-(w*.13+next_z*w*.59),w*.5+(w*.13+next_z*w*.59)
            pygame.draw.polygon(s,(18+round(z*6),39+round(z*9),52+round(z*10)),[(left,y),(right,y),(right2,y2),(left2,y2)])
            pygame.draw.line(s,blend(color,(8,22,37),.78),(left,y),(right,y),1)
        for frac in (-1,-.52,0,.52,1):
            end=(w*.5+frac*w*.75,h)
            pygame.draw.line(s,(33,66,79),van,end,1)
        # Raised track rails: a dark solid face, a bright edge and regular lamps.
        for side in (-1,1):
            inner_top=(w*.5+side*w*.145,219)
            inner_bottom=(w*.5+side*w*.59,h)
            outer_top=(inner_top[0]+side*9,215)
            outer_bottom=(inner_bottom[0]+side*26,h)
            pygame.draw.polygon(s,(34,53,63),[inner_top,inner_bottom,outer_bottom,outer_top])
            pygame.draw.line(s,blend(color,(255,248,226),.22),inner_top,inner_bottom,2)
            for i in range(9):
                z=((i/9+elapsed*speed)%1)**1.65
                x=w*.5+side*(w*.145+z*w*.445)
                y=219+z*(h-219)
                pygame.draw.circle(s,color,(round(x),round(y)),max(1,round(1+z*2)))
        if key in ("sprint","red_green") and run>.25 and not self.reduced_motion:
            for i in range(10):
                phase=(elapsed*(.9+run)+i*.193)%1
                side=-1 if i%2 else 1
                z=phase**1.6
                x=w*.5+side*(w*.25+z*w*.36)
                y=220+z*310
                pygame.draw.line(s,blend(color,(255,255,246),.25),(x,y),(x+side*(8+z*21),y+12+z*40),max(1,round(z*3)))

    def platform(self,s,center,radius,color):
        x,y=center
        pygame.draw.ellipse(s,(3,15,27),(x-radius-8,y-13,radius*2+16,31))
        polygon_ring(s,(x,y),radius,5,blend(color,(18,42,59),.3),squash=.17,segments=40)
        pygame.draw.ellipse(s,blend(color,(14,36,49),.75),(x-radius*.73,y-7,radius*1.46,15),1)

    def prompt(self,s,value,w,y,color,size=34):
        # Prompts never compete directly with bright scenery or active obstacles.
        width=min(w-36,max(w*.55,font(size,True).size(value)[0]+48))
        panel(s,(w*.5-width*.5,y-26,width,53),(8,24,39),blend(color,(8,24,39),.65),14)
        fit_text(s,value,(w*.5,y),width-30,size,color,True,True)

    def portal(self,s,center,radius,color,elapsed):
        cx,cy=center
        # Back rim projects to the right, giving the gate visible physical depth.
        pygame.draw.circle(s,(3,14,28),(round(cx+9),round(cy-5)),round(radius+17))
        polygon_ring(s,(cx+9,cy-5),radius+17,13,(63,80,94),segments=48)
        pygame.draw.circle(s,(5,22,36),(round(cx),round(cy)),round(radius-6))
        for i in range(3):
            r=radius*(.43+i*.16)
            rect=pygame.Rect(cx-r,cy-r,r*2,r*2)
            angle=elapsed*(.18+i*.035)+i*1.9
            pygame.draw.arc(s,blend(color,(9,31,48),.63),rect,angle,angle+3.7,2)
        polygon_ring(s,(cx,cy),radius+8,16,(113,133,145),segments=48)
        pygame.draw.circle(s,color,(round(cx),round(cy)),round(radius),4)
        pygame.draw.circle(s,blend(color,(255,255,239),.45),(round(cx),round(cy)),round(radius-8),1)
        for i in range(24):
            a=i*math.tau/24+elapsed*.04
            outer=radius+7
            inner=radius-1 if i%2 else radius-7
            pygame.draw.line(s,WHITE if i%6==0 else color,(cx+math.sin(a)*inner,cy+math.cos(a)*inner),(cx+math.sin(a)*outer,cy+math.cos(a)*outer),2)
        clock_icon(s,(round(cx),round(cy)),round(radius*.23),blend(color,(255,253,235),.3),elapsed*.35)

    def race(self,s,g,w,h,now,color):
        racing=g.game_id=="sprint"
        light=ORANGE if racing and g.boost else color if racing else GREEN if g.phase=="GREEN" else RED
        radius=107+g.progress*63
        self.portal(s,(w*.5,306),radius,light,now)
        self.platform(s,(w*.5,506),94,color)
        if racing:
            message="TIME WARP / KEEP RUNNING" if g.boost else "JOG IN PLACE"
            if g.boost and not self.reduced_motion:
                for i in range(12):
                    a=i*math.tau/12
                    r=radius+22+(now*90+i*13)%55
                    pygame.draw.line(s,ORANGE,(w*.5+math.sin(a)*r,306+math.cos(a)*r),(w*.5+math.sin(a)*(r+19),306+math.cos(a)*(r+19)),2)
        else:
            message="GREEN / JOG IN PLACE" if g.phase=="GREEN" else "RED / FREEZE" if not g.in_grace else "FREEZE / GET STILL"
            if g.in_grace:
                remaining=1-g.phase_elapsed/max(.001,g.config.red_grace_seconds)
                pygame.draw.rect(s,(46,50,61),(w*.31,169,w*.38,5),border_radius=2)
                pygame.draw.rect(s,ORANGE,(w*.31,169,max(2,w*.38*remaining),5),border_radius=2)
            if g.elapsed<g.warning_until:
                self.prompt(s,"ONE SHIELD LOST" if g.endless else f"YOU MOVED / -{g.config.penalty_progress:.0%}",w,194,RED,22)
        self.prompt(s,message,w,133,light,31)
        pill(s,f"PORTAL {getattr(g,'laps',0)+1:02d}" if g.endless else "FINISH PORTAL",(20,177),color,12)
        text(s,f"{g.progress*100:.0f}%",(w-77,h-85),29,light,True,center=True,mono=True)

    def energy_vault(self,s,w,h,now,color):
        center=(round(w*.5),round(h*.54))
        for i in range(3):
            r=100+i*47
            rect=(center[0]-r,center[1]-r*.6,r*2,r*1.2)
            pygame.draw.ellipse(s,blend(color,(11,27,45),.82),rect,1)
        for i in range(7):
            a=i*math.tau/7+now*.08
            x,y=center[0]+math.sin(a)*w*.35,center[1]+math.cos(a)*122
            pygame.draw.circle(s,(13,30,47),(round(x),round(y)),15)
            pygame.draw.circle(s,blend(color,(28,49,64),.5),(round(x),round(y)),15,1)
            pygame.draw.line(s,blend(color,(11,27,45),.8),center,(x,y),1)
            pygame.draw.circle(s,color,(round(x),round(y)),3)

    def lightning(self,s,g,w,h,actions,now,color,slot=0):
        area=pygame.Rect(w*.09,150,w*.82,350)
        x,y=area.x+g.target[0]*area.width,area.y+g.target[1]*area.height
        # Faceted energy core, orbiting conductor arcs and an expiry ring.
        for i in range(3):
            angle=now*(.7+i*.12)+i*2.1
            r=35+i*7
            pygame.draw.arc(s,(98+i*25,94+i*14,69),(x-r,y-r,r*2,r*2),angle,angle+1.9,2)
        glow(s,(x,y),24+(0 if self.reduced_motion else math.sin(now*7)*2),ORANGE)
        ring(s,(round(x),round(y)),48,max(0.,1-g.target_age/g.target_lifetime),ORANGE,4)
        pygame.draw.polygon(s,WHITE,[(x+3,y-17),(x-11,y+3),(x-1,y+3),(x-4,y+17),(x+12,y-5),(x+2,y-5)])
        held=min(1.,g.touch_held/max(.001,g.config.target_hold_seconds))
        if held>0:
            ring(s,(round(x),round(y)),56,held,GREEN,5)
        for hand_index,hand in enumerate((actions.left_hand,actions.right_hand)):
            hx,hy=area.x+hand[0]*area.width,area.y+hand[1]*area.height
            key=(slot,hand_index)
            points=self.trails.setdefault(key,deque(maxlen=9))
            if not self.reduced_motion and self.trail_stamps.get(key)!=g.elapsed:
                points.append((hx,hy))
                self.trail_stamps[key]=g.elapsed
            if len(points)>1 and not self.reduced_motion:
                for i in range(1,len(points)):
                    pygame.draw.line(s,blend((10,29,45),color,i/len(points)*.65),points[i-1],points[i],max(1,round(i/len(points)*5)))
            pygame.draw.circle(s,(4,18,32),(round(hx),round(hy)),17)
            pygame.draw.circle(s,color,(round(hx),round(hy)),12,2)
            pygame.draw.circle(s,WHITE,(round(hx),round(hy)),4)
            for dx,dy in ((-21,0),(21,0),(0,-21),(0,21)):
                pygame.draw.line(s,color,(hx+dx*.78,hy+dy*.78),(hx+dx,hy+dy),2)
        self.prompt(s,"TOUCH THE ENERGY CORE",w,130,ORANGE,30)

    def dodge(self,s,g,w,h,now):
        z=g.approach**2
        width=w*(.14+.75*z)
        height=42+200*z
        bottom=235+240*z
        x,y=w*.5-width/2,bottom-height
        gap=width*.36
        if g.required=="DUCK":
            blocks=[pygame.Rect(x,y,width,height*.5)]
            safe=pygame.Rect(x+4,bottom-height*.43,width-8,height*.43)
        else:
            blocks=[pygame.Rect(x+gap if g.required=="LEFT" else x,y,width-gap,height)]
            sx=x if g.required=="LEFT" else x+width-gap
            safe=pygame.Rect(sx+2,y,gap-4,height)
        # Lit safe openings live on the same depth plane as the solid wall.
        pygame.draw.rect(s,(16,62,60),safe,border_radius=3)
        pygame.draw.rect(s,GREEN,safe,2,border_radius=3)
        if safe.width>22 and safe.height>18:
            if g.required=="DUCK":
                for i in (-1,0,1):
                    px=safe.centerx+i*safe.width*.2
                    pygame.draw.lines(s,GREEN,False,[(px-7,safe.centery-4),(px,safe.centery+4),(px+7,safe.centery-4)],2)
            else:
                for i in range(3):
                    chevron(s,(safe.centerx,safe.y+safe.height*(i+1)/4),min(10,safe.width*.14),GREEN,-1 if g.required=="LEFT" else 1,2)
        for block in blocks:
            prism(s,block,(255,141,96),10+z*26)
            inset=block.inflate(-12,-10)
            if inset.width>18 and inset.height>18:
                for i in range(max(1,int(block.width/42))):
                    px=inset.left+(i+.5)*inset.width/max(1,int(block.width/42))
                    pygame.draw.line(s,(133,79,59),(px,inset.top+4),(px,inset.bottom-4),2)
                pygame.draw.line(s,(255,185,116),(inset.left,inset.top+4),(inset.right,inset.top+4),2)
        # Arrival line and its projected shadow make the approach easy to read.
        pygame.draw.line(s,blend(ORANGE,(5,19,33),.55),(x,bottom+6),(x+width,bottom+6),max(1,round(2+z*3)))
        label="DUCK DOWN" if g.required=="DUCK" else "LEAN "+g.required
        self.prompt(s,label,w,132,GREEN,35)
        text(s,f"IMPACT IN {max(0.,g.travel_seconds-g.obstacle_age):.1f}s",(w*.5,178),17,ORANGE,center=True,mono=True)
        if not g.endless:
            for i in range(5):
                shield(s,(27+i*22,191),7,CYAN if i<g.lives else EDGE,i<g.lives)

    def timekeeper(self,s,g,w,h,now):
        center=(round(w*.69),323)
        target=67
        radius=round(max(24,167-g.beat_age/g.target_time*100))
        near=abs(g.beat_age-g.target_time)<=g.window
        # Raised clock housing with a complete chapter ring and mechanical spokes.
        pygame.draw.circle(s,(7,16,30),(center[0]+5,center[1]-4),145)
        polygon_ring(s,center,137,11,(139,111,77),segments=48)
        pygame.draw.circle(s,(18,30,44),center,126)
        for i in range(60):
            a=i*math.tau/60
            r1,r2=(113,123) if i%5==0 else (119,123)
            pygame.draw.line(s,ORANGE if i%5==0 else (113,105,90),(center[0]+math.sin(a)*r1,center[1]+math.cos(a)*r1),(center[0]+math.sin(a)*r2,center[1]+math.cos(a)*r2),2 if i%5==0 else 1)
        for i in range(8):
            a=i*math.tau/8+now*.09
            r1,r2=82,99
            pygame.draw.line(s,(63,67,68),(center[0]+math.sin(a)*r1,center[1]+math.cos(a)*r1),(center[0]+math.sin(a)*r2,center[1]+math.cos(a)*r2),4)
        pygame.draw.circle(s,(244,177,99),center,target,4)
        pygame.draw.circle(s,GREEN if near else (250,230,183),center,radius,5)
        pygame.draw.circle(s,(8,24,37),center,39)
        clock_icon(s,center,29,ORANGE,now*.3)
        if near:
            pygame.draw.circle(s,GREEN,center,target+7,2)
        self.prompt(s,"RAISE A HAND NOW!" if near else "LOWER / WATCH THE RINGS",w,130,GREEN if near else WHITE,29)
        pill(s,f"BEAT {g.beat_number:02d}",(center[0]-52,472),ORANGE,12)
        text(s,"RINGS MEET = RAISE",(center[0],455),14,ORANGE,True,True)

    def echo(self,s,g,w,h,now):
        watching=g.stage=="WATCH"
        pose=g.sequence[g.shown_index] if watching else "IDLE"
        # A holographic cell, a floor reflection and scanlines distinguish the echo.
        left,top,width,height=w*.74-76,246,152,250
        pygame.draw.ellipse(s,(20,26,53),(left,top-7,width,19),1)
        pygame.draw.line(s,(56,47,91),(left,top+2),(left,492),1)
        pygame.draw.line(s,(56,47,91),(left+width,top+2),(left+width,492),1)
        for i in range(7):
            yy=top+(i*37+now*14)%height
            pygame.draw.line(s,(35,35,65),(left+5,yy),(left+width-5,yy),1)
        self.a.avatar.draw(s,demonstration_pose(pose,now),w*.74,248,245,4/3,now,True,neutral=neutral_pose(),color=PURPLE)
        if watching:
            message="WATCH: "+pose
        elif g.stage=="COMPLETE":
            message="ALL TIME ECHOES MASTERED!"
        elif g.stage=="REST":
            message="ECHO COMPLETE / NEXT SEQUENCE"
        else:
            message=f"REPEAT POSE {g.step_index+1} OF {len(g.sequence)}"
            text(s,"?",(w*.74,220),44,PURPLE,True,True)
        self.prompt(s,message,w,130,PURPLE,29)
        box=40
        gap=8
        start=w/2-(len(g.sequence)*(box+gap)-gap)/2
        for i,value in enumerate(g.sequence):
            rect=pygame.Rect(start+i*(box+gap),173,box,34)
            active=(watching and g.shown_index==i) or (not watching and i<g.step_index)
            panel(s,rect,(65,48,105) if active else (13,26,43),PURPLE if active else EDGE,8)
            label={"LEFT":"<","RIGHT":">","DUCK":"v","HANDS UP":"UP"}[value] if watching or i<g.step_index else "?"
            text(s,label,rect.center,17,WHITE,True,True)
        text(s,"YOU",(w*.27,517),10,CYAN,True,True)
        text(s,"TIME ECHO",(w*.74,517),10,PURPLE,True,True)
        if g.stage=="REPEAT":
            ring(s,(round(w*.27),228),18,g.pose_held/g.config.pose_hold_seconds,PURPLE,4)

    def hud(self,s,g,w,h,slot,now,color):
        name=self.a.match.names[slot]
        pill(s,name.upper()[:22],(18,14),color,13)
        panel(s,(w-137,13,119,77),(7,21,37),blend(color,(8,24,39),.65),13)
        text(s,"SURVIVED" if g.endless else "TIME LEFT",(w-122,25),10,MUTED,mono=True)
        text(s,f"{g.elapsed if g.endless else g.remaining:04.1f}",(w-123,43),30,WHITE,True,mono=True)
        if g.metric=="score":
            text(s,f"{g.score:,}",(21,51),32,WHITE,True,mono=True)
            score_width=font(32,True,True).size(f"{g.score:,}")[0]
            text(s,"PTS",(29+score_width,69),11,MUTED,mono=True)
        else:
            text(s,f"{g.elapsed:.1f}s ELAPSED",(23,61),18,WHITE,mono=True)
        if g.endless and g.elapsed<g.level_until:
            fit_text(s,"TIME ACCELERATES",(w*.52,26),w*.34,13,ORANGE,True,True)
            text(s,f"LEVEL {g.level:02d}",(w*.52,53),22,ORANGE,True,True,True)
        elif getattr(g,"combo",0)>1:
            text(s,f"x{g.combo}",(w*.52,40),29,color,True,True,True)
            text(s,"CURRENT CHAIN",(w*.52,66),10,MUTED,center=True,mono=True)
        else:
            fit_text(s,PALETTES[g.game_id][2],(w*.52,40),w*.32,12,MUTED,False,True)
        # The reserved bottom rail separates feedback from status and powers.
        panel(s,(12,h-50,w-24,42),(6,20,34),(37,59,77),10)
        if g.endless:
            text(s,"LEVEL",(24,h-42),9,MUTED,mono=True)
            text(s,f"{g.level:02d}",(24,h-29),19,color,True,mono=True)
            power=getattr(g,"time_power_charges",None)
            if power is not None:
                active=getattr(g,"time_power_active",False)
                pc=PURPLE if active else CYAN if power else MUTED
                text(s,"TIME SHIELD" if not active else "SHIELD ACTIVE",(88,h-43),11,pc,True,mono=True)
                text(s,"CROSS ARMS / R" if slot==0 else "CROSS ARMS / F",(88,h-25),11,MUTED,mono=True)
                for i in range(2):
                    pygame.draw.circle(s,pc if i<power else EDGE,(235+i*14,h-33),4,0 if i<power else 1)
                progress=getattr(g,"time_power_progress",0.)
                if progress>0:
                    pygame.draw.rect(s,pc,(88,h-12,162*min(1.,progress),2),border_radius=1)
            elif hasattr(g,"laps"):
                text(s,f"PORTALS {g.laps}",(88,h-30),13,MUTED,mono=True)
            if g.game_id in ("sprint","red_green"):
                x,width=w*.43,w*.22
                text(s,"TIME ENERGY",(x,h-41),9,MUTED,mono=True)
                pygame.draw.rect(s,(33,54,68),(x,h-23,width,7),border_radius=3)
                pygame.draw.rect(s,GREEN if g.energy>30 else ORANGE,(x,h-23,max(2,width*g.energy/100),7),border_radius=3)
            elif getattr(g,"best_combo",0)>0:
                fit_text(s,f"BEST CHAIN x{g.best_combo}",(w*.53,h-30),w*.23,11,MUTED,center=True,mono=True)
            # Two rows keep five shields legible even in the narrow split view.
            text(s,"SHIELDS",(w-114,h-42),9,MUTED,mono=True)
            for i in range(g.max_lives):
                shield(s,(w-27-i*19,h-24),6.5,GREEN if i<g.lives else EDGE,i<g.lives)
        else:
            text(s,"CHALLENGE PROGRESS",(24,h-39),9,MUTED,mono=True)
            pygame.draw.rect(s,(35,56,73),(24,h-22,w-48,6),border_radius=3)
            pygame.draw.rect(s,color,(24,h-22,max(2,(w-48)*min(1.,g.progress)),6),border_radius=3)
        if hasattr(g,"feedback_until") and g.elapsed<g.feedback_until:
            y=225 if g.game_id=="echo" else h-76
            size=20 if w<900 else 25
            c=RED if g.feedback_kind=="error" else GREEN
            if g.game_id!="echo":
                width=min(w-48,font(size,True).size(g.feedback)[0]+36)
                panel(s,(w*.5-width*.5,y-18,width,35),(7,23,35),blend(c,(8,24,39),.65),12)
            fit_text(s,g.feedback,(w*.5,y),w*.86,size,c,True,True)

    def countdown(self,s,g,w,h):
        shade=pygame.Surface((w,h),pygame.SRCALPHA)
        shade.fill((3,14,28,155))
        s.blit(shade,(0,0))
        ring(s,(w//2,300),76,1-(g.countdown%1),ORANGE,5)
        text(s,str(max(1,math.ceil(g.countdown))),(w//2,297),86,WHITE,True,True)
        text(s,"YOUR NEXT SECOND STARTS HERE",(w//2,414),18,WHITE,True,True)
