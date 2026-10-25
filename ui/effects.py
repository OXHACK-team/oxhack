"""Bounded arena feedback driven by immutable game events.

Call emit(slot, event, game, now, field_rect), update(dt), then draw(canvas, now).
Particles use canvas coordinates and never touch game state or its random seed.
"""
from dataclasses import dataclass
from collections import deque
import math
import random
import pygame
from ui.theme import CYAN, GREEN, ORANGE, PURPLE, RED, WHITE, font


@dataclass
class Particle:
    slot: int
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    life: float
    total: float
    color: tuple
    gravity: float
    clip: tuple
    streak: bool = False


@dataclass
class Wave:
    slot: int
    x: float
    y: float
    radius: float
    speed: float
    life: float
    total: float
    color: tuple
    clip: tuple
    clock: bool = False


@dataclass
class Caption:
    slot: int
    x: float
    y: float
    life: float
    total: float
    image: object
    shadow: object
    clip: tuple
    rise: float


class Effects:
    """Particles, clock shockwaves, score pops and quiet impact edges."""
    MAX_PARTICLES=240
    MAX_WAVES=24
    MAX_CAPTIONS=12

    def __init__(self,config,seed=2026):
        self.config=config
        self.rng=random.Random(seed)
        self.particles=deque(maxlen=self.MAX_PARTICLES)
        self.waves=deque(maxlen=self.MAX_WAVES)
        self.captions=deque(maxlen=self.MAX_CAPTIONS)
        self.flashes={}
        self.anchors={}
        self.runs={}
        self.layer=None

    @property
    def reduced_motion(self):
        return bool(getattr(self.config,"reduced_motion",False))

    @property
    def active_count(self):
        return len(self.particles)+len(self.waves)+len(self.captions)+len(self.flashes)

    def clear(self):
        self.particles.clear()
        self.waves.clear()
        self.captions.clear()
        self.flashes.clear()
        self.anchors.clear()
        self.runs.clear()

    def clear_slot(self,slot):
        self.particles=deque((p for p in self.particles if p.slot!=slot),maxlen=self.MAX_PARTICLES)
        self.waves=deque((p for p in self.waves if p.slot!=slot),maxlen=self.MAX_WAVES)
        self.captions=deque((p for p in self.captions if p.slot!=slot),maxlen=self.MAX_CAPTIONS)
        self.flashes.pop(slot,None)
        self.anchors.pop(slot,None)

    def _burst(self,slot,xy,color,count,clip,speed=160.,life=.65,gravity=80.):
        if self.reduced_motion:
            return
        for i in range(count):
            angle=self.rng.random()*math.tau
            velocity=speed*self.rng.uniform(.35,1.2)
            total=life*self.rng.uniform(.65,1.15)
            self.particles.append(Particle(slot,*xy,math.cos(angle)*velocity,math.sin(angle)*velocity,
                self.rng.uniform(1.4,3.6),total,total,color,gravity,clip,i%3==0))

    def _wave(self,slot,xy,color,clip,radius=10.,speed=170.,life=.6,clock=False):
        if self.reduced_motion:
            radius,speed,life=30.,0.,min(life,.3)
        self.waves.append(Wave(slot,*xy,radius,speed,life,life,color,clip,clock))

    def _caption(self,slot,value,xy,color,clip,size=31,life=.85):
        if not pygame.font.get_init():
            pygame.font.init()
        face=font(size,True)
        image=face.render(str(value),True,color)
        shadow=face.render(str(value),True,(3,15,26))
        offset=sum(c.slot==slot and c.life>c.total*.7 for c in self.captions)*19
        self.captions.append(Caption(slot,xy[0],xy[1]-min(offset,50),life,life,image,shadow,
                                     clip,0. if self.reduced_motion else 38.))

    def emit(self,slot,event,game,now,rect):
        """Queue one event. Field rect is in global canvas coordinates."""
        rect=pygame.Rect(rect)
        if self.runs.get(slot)!=id(game):
            self.clear_slot(slot)
            self.runs[slot]=id(game)
        kind=event.get("event","")
        if kind=="target_spawn":
            self.anchors[slot]=tuple(event.get("target",(.5,.45)))
            return
        if kind not in {"score","miss","red_violation","checkpoint","level_up","shield_restored",
                        "win","lose","round_started","time_power","time_block","time_power_ready"}:
            return
        clip=tuple(pygame.Rect(rect.x+5,rect.y+112,rect.width-10,rect.height-156))
        center=(rect.centerx,rect.y+rect.height*.52)
        color=CYAN if slot==0 else ORANGE
        if kind=="score":
            key=getattr(game,"game_id","")
            if key=="lightning":
                target=event.get("target",self.anchors.get(slot,(.5,.42)))
                center=(rect.x+rect.width*(.09+.82*target[0]),rect.y+150+350*target[1])
                color=ORANGE
            elif key=="timekeeper":
                center=(rect.x+rect.width*.69,rect.y+315)
                color=GREEN
            elif key=="echo":
                center=(rect.x+rect.width*.27,rect.y+320)
                color=PURPLE
            elif key=="dodge":
                center=(rect.centerx,rect.y+345)
                color=GREEN
            self._burst(slot,center,color,16,clip,150.,.55)
            self._wave(slot,center,color,clip,14.,145.,.45)
            if key=="timekeeper":
                self._wave(slot,center,WHITE,clip,58.,120.,.55,True)
            if event.get("points",0):
                self._caption(slot,f"+{event['points']:,}",(center[0],center[1]-24),WHITE,clip)
        elif kind in ("miss","red_violation"):
            if kind=="red_violation" and getattr(game,"endless",False):
                return
            self._burst(slot,center,RED,19,clip,190.,.48,145.)
            self._wave(slot,center,RED,clip,30.,210.,.42)
            if not self.reduced_motion:
                self.flashes[slot]=[rect,.32,.32,RED]
        elif kind in ("checkpoint","win"):
            self._burst(slot,center,ORANGE if kind=="checkpoint" else GREEN,52,clip,270.,1.0,65.)
            self._wave(slot,center,ORANGE,clip,25.,280.,.8,True)
            self._wave(slot,center,WHITE,clip,12.,210.,.6)
            if kind=="checkpoint":
                self._caption(slot,"PORTAL CLEARED",(rect.centerx,rect.y+235),ORANGE,clip,30,1.1)
        elif kind=="level_up":
            self._burst(slot,(rect.centerx,rect.y+185),ORANGE,25,clip,180.,.9,75.)
            self._wave(slot,center,ORANGE,clip,65.,190.,.85,True)
        elif kind in ("shield_restored","time_power_ready"):
            self._wave(slot,center,GREEN if kind=="shield_restored" else PURPLE,clip,25.,130.,.7,True)
            self._burst(slot,center,GREEN,16,clip,110.,.7,-25.)
            value=event.get("label","SHIELD RESTORED" if kind=="shield_restored" else "TIME SHIELD READY")
            self._caption(slot,value,(rect.centerx,rect.y+240),GREEN,clip,26,1.05)
        elif kind in ("time_power","time_block"):
            self._burst(slot,center,PURPLE,50 if kind=="time_power" else 28,clip,260.,.85,0.)
            for radius in (18,45,76):
                self._wave(slot,center,PURPLE if radius!=45 else CYAN,clip,radius,180.,.9,True)
            self._caption(slot,event.get("label","TIME SHIELD" if kind=="time_power" else "HIT ABSORBED"),
                          (rect.centerx,rect.y+245),CYAN,clip,32,1.0)
        elif kind=="round_started":
            self._wave(slot,center,color,clip,40.,230.,.6,True)
            self._caption(slot,"GO!",(rect.centerx,rect.y+245),WHITE,clip,47,.6)
        elif kind=="lose":
            self._wave(slot,center,ORANGE,clip,25.,120.,.6,True)

    def update(self,dt):
        dt=max(0.,float(dt))
        travel=min(dt,.1)
        if self.reduced_motion:
            self.particles.clear()
            self.flashes.clear()
            for wave in self.waves:
                wave.speed=0.
            for caption in self.captions:
                caption.rise=0.
        for p in self.particles:
            p.life-=dt
            p.vy+=p.gravity*travel
            p.x+=p.vx*travel
            p.y+=p.vy*travel
            drag=math.exp(-travel*1.35)
            p.vx*=drag
            p.vy*=drag
        self.particles=deque((p for p in self.particles if p.life>0),maxlen=self.MAX_PARTICLES)
        for wave in self.waves:
            wave.life-=dt
            wave.radius+=wave.speed*travel
        self.waves=deque((p for p in self.waves if p.life>0),maxlen=self.MAX_WAVES)
        for caption in self.captions:
            caption.life-=dt
            caption.y-=caption.rise*travel
        self.captions=deque((p for p in self.captions if p.life>0),maxlen=self.MAX_CAPTIONS)
        for slot in list(self.flashes):
            self.flashes[slot][1]-=dt
            if self.flashes[slot][1]<=0:
                del self.flashes[slot]

    def draw(self,surface,now=0.):
        if not self.active_count:
            return
        if self.layer is None or self.layer.get_size()!=surface.get_size():
            self.layer=pygame.Surface(surface.get_size(),pygame.SRCALPHA)
        layer=self.layer
        layer.fill((0,0,0,0))
        for rect,left,total,color in self.flashes.values():
            alpha=round(100*(left/total)**2)
            pygame.draw.rect(layer,(*color,alpha),rect.inflate(-5,-5),3,border_radius=16)
            pygame.draw.rect(layer,(*color,alpha//2),rect.inflate(-13,-13),2,border_radius=13)
        for p in self.particles:
            layer.set_clip(p.clip)
            fade=max(0.,p.life/p.total)
            xy=(round(p.x),round(p.y))
            color=(*p.color,round(230*fade))
            if p.streak:
                pygame.draw.line(layer,color,xy,(round(p.x-p.vx*.045),round(p.y-p.vy*.045)),max(1,round(p.radius*fade)))
            else:
                pygame.draw.circle(layer,color,xy,max(1,round(p.radius*(.4+.6*fade))))
                if fade>.65:
                    pygame.draw.circle(layer,(*WHITE,round(230*fade)),xy,1)
        for wave in self.waves:
            layer.set_clip(wave.clip)
            fade=max(0.,wave.life/wave.total)
            r=max(1,round(wave.radius))
            center=(round(wave.x),round(wave.y))
            color=(*wave.color,round(175*fade*fade))
            pygame.draw.circle(layer,color,center,r,max(1,round(3*fade)))
            if wave.clock:
                for i in range(12):
                    angle=i*math.tau/12
                    x,y=center[0]+math.sin(angle)*r,center[1]+math.cos(angle)*r
                    x2,y2=center[0]+math.sin(angle)*(r+6),center[1]+math.cos(angle)*(r+6)
                    pygame.draw.line(layer,color,(round(x),round(y)),(round(x2),round(y2)),2)
        for caption in self.captions:
            layer.set_clip(caption.clip)
            alpha=round(255*min(1.,caption.life/.25))
            caption.image.set_alpha(alpha)
            caption.shadow.set_alpha(alpha)
            rect=caption.image.get_rect(center=(round(caption.x),round(caption.y)))
            layer.blit(caption.shadow,rect.move(0,3))
            layer.blit(caption.image,rect)
        layer.set_clip(None)
        surface.blit(layer,(0,0))
