"""A dimensional, joint-driven sports mascot with shaded armor and sportswear."""
import math
import numpy as np
import pygame
from tracking_types import *
from ui.theme import CYAN,ORANGE


def demonstration_pose(name="IDLE",now=0.):
    p=neutral_pose()
    if name=="LEFT":
        p[[NOSE,LS,RS,LE,RE,LW,RW],0]-=.11
    elif name=="RIGHT":
        p[[NOSE,LS,RS,LE,RE,LW,RW],0]+=.11
    elif name=="DUCK":
        p[[NOSE,LS,RS,LE,RE,LW,RW,LH,RH],1]+=.13
        p[LK,0]-=.06
        p[RK,0]+=.06
    elif name in ("HANDS UP","LEFT HAND","RIGHT HAND"):
        if name!="RIGHT HAND":
            p[LW,:2],p[LE,:2]=(.29,.07),(.31,.2)
        if name!="LEFT HAND":
            p[RW,:2],p[RE,:2]=(.71,.07),(.69,.2)
    elif name=="RUN":
        swing=math.sin(now*11)
        p[LK,1]-=max(0,swing)*.12
        p[RK,1]-=max(0,-swing)*.12
        p[LA,1]-=max(0,swing)*.1
        p[RA,1]-=max(0,-swing)*.1
        p[LW,1]+=swing*.11
        p[RW,1]-=swing*.11
        p[LE,1]+=swing*.05
        p[RE,1]-=swing*.05
    else:
        p[[NOSE,LS,RS,LE,RE,LW,RW],1]+=math.sin(now*2)*.006
    return p


class Avatar:
    def __init__(self):
        from config import ROOT
        self.rig=None
        if (ROOT/"assets/athlete-rig.png").exists():
            from sprite_rig import SpriteRig
            self.rig=SpriteRig()

    def draw(self,surface,pose,center_x,top,height=430,aspect=4/3,now=0.,ghost=False,neutral=None,color=None):
        p=demonstration_pose(now=now) if pose is None else pose.copy()
        if pose is None:
            aspect=4/3
        # Before calibration the camera position is not an arena spawn point.
        # Normalize the visible body immediately so off-centre arrivals stay on
        # their own platform, at the same scale as a calibrated avatar.
        reference=neutral if neutral is not None else p
        if pose is not None:
            hip=np.mean(reference[[LH,RH],:2],axis=0)
            torso=max(.08,hip[1]-float(np.mean(reference[[LS,RS],1])))
            factor=.26/torso
            p[:,0]=.5+(p[:,0]-hip[0])*factor*aspect/(4/3)
            p[:,1]=.55+(p[:,1]-hip[1])*factor
            aspect=4/3
        suit=color or ((176,142,249) if ghost else (35,172,180))
        if self.rig is not None:
            tint=color or ((186,155,255) if ghost else (78,233,232))
            self.rig.draw(surface,p,center_x,top,height,aspect,now,tint)
            return
        shade=tuple(int(c*.57) for c in suit)
        bright=tuple(min(255,int(c*1.15+30)) for c in suit)
        light=(235,239,241) if not ghost else (207,201,239)
        dark=(20,37,54)
        scale=height/.8
        def point(i):
            return np.array([center_x+(p[i,0]-.5)*scale*aspect,top+(p[i,1]-.12)*scale])
        def ip(v):
            return tuple(map(round,v))
        def disk(pos,r,col):
            pygame.draw.circle(surface,col,ip(pos),max(1,round(r)))
        def capsule(a,b,width,base=light):
            a,b=point(a),point(b)
            width=max(4,round(width*height))
            radius=width/2
            low=tuple(int(c*.53) for c in base)
            mid=tuple(int(c*.81) for c in base)
            high=tuple(min(255,c+12) for c in base)
            for offset,w,col in (([2,3],width+4,dark),([0,0],width,low),([-width*.06,-width*.06],width*.84,mid),([-width*.13,-width*.09],width*.60,base),([-width*.22,-width*.11],width*.18,high)):
                va,vb=a+offset,b+offset
                pygame.draw.line(surface,col,ip(va),ip(vb),max(2,round(w)))
                disk(va,w/2,col)
                disk(vb,w/2,col)
        # Contact shadow and a luminous grounding ring.
        floor=pygame.Rect(0,0,height*.5,height*.075)
        floor.center=(round(center_x),round(top+height*1.04))
        pygame.draw.ellipse(surface,(9,26,36),floor)
        pygame.draw.ellipse(surface,tuple(int(c*.6) for c in suit),floor,2)
        for shoulder,elbow,wrist in ((RS,RE,RW),):
            capsule(shoulder,elbow,.079,suit)
            capsule(elbow,wrist,.071,light)
        for hip,knee,ankle in ((RH,RK,RA),(LH,LK,LA)):
            capsule(hip,knee,.10,(47,66,83))
            capsule(knee,ankle,.084,light)
            disk(point(knee),height*.044,dark)
            disk(point(knee)+[-height*.005,-height*.006],height*.033,(128,148,165))
            disk(point(knee)+[-height*.01,-height*.012],height*.021,light)
            foot=point(ankle)+[0,height*.015]
            shoe=pygame.Rect(0,0,height*.145,height*.066)
            shoe.center=ip(foot)
            pygame.draw.rect(surface,dark,shoe.inflate(5,4),border_radius=max(3,round(height*.026)))
            pygame.draw.rect(surface,(181,194,202),shoe,border_radius=max(3,round(height*.024)))
            pygame.draw.rect(surface,light,shoe.inflate(-4,-7).move(-2,-3),border_radius=max(3,round(height*.023)))
            pygame.draw.line(surface,suit,(shoe.left+4,shoe.bottom-3),(shoe.right-4,shoe.bottom-3),max(2,round(height*.011)))
        ls,rs,lh,rh=[point(i) for i in (LS,RS,LH,RH)]
        shoulder=(ls+rs)/2
        head=point(NOSE)+[0,height*.026]
        pygame.draw.line(surface,(80,104,120),ip(head+[0,height*.055]),ip(shoulder),max(4,round(height*.07)))
        pad=height*.034
        torso=[ls+[-pad,-pad*.25],rs+[pad,-pad*.25],rh+[pad*.7,pad*.7],lh+[-pad*.7,pad*.7]]
        pygame.draw.polygon(surface,dark,[ip(v+[0,3]) for v in torso])
        pygame.draw.polygon(surface,shade,[ip(v) for v in torso])
        pygame.draw.polygon(surface,suit,[ip(torso[0]),ip(torso[1]-[pad*.4,0]),ip(torso[2]-[pad*.6,0]),ip(torso[3])])
        pygame.draw.polygon(surface,bright,[ip(torso[0]+[pad*.1,0]),ip((ls+rs)/2),ip((lh+rh)/2),ip(torso[3]+[pad*.15,0])])
        # White chest yoke gives the character a recognizable sports silhouette.
        yoke=[torso[0],torso[1],rs+[0,height*.05],shoulder+[0,height*.085],ls+[0,height*.05]]
        pygame.draw.polygon(surface,light,[ip(v) for v in yoke])
        pygame.draw.line(surface,(255,255,249),ip(torso[0]),ip(torso[1]),max(2,round(height*.008)))
        pygame.draw.line(surface,dark,ip(lh+[-pad*.7,pad*.5]),ip(rh+[pad*.7,pad*.5]),max(3,round(height*.027)))
        chest=shoulder*.58+((lh+rh)/2)*.42
        disk(chest,height*.036,dark)
        disk(chest,height*.025,CYAN if not ghost else ORANGE)
        pygame.draw.line(surface,(248,255,251),ip(chest),ip(chest+[0,-height*.017]),max(2,round(height*.006)))
        pygame.draw.line(surface,(248,255,251),ip(chest),ip(chest+[height*.014,0]),max(2,round(height*.006)))
        capsule(LS,LE,.082,suit)
        capsule(LE,LW,.074,light)
        for i in (LS,RS):
            disk(point(i),height*.049,dark)
            disk(point(i)+[-height*.004,-height*.007],height*.042,light)
            disk(point(i)+[-height*.01,-height*.012],height*.026,(255,255,248))
        for wrist in (LW,RW):
            hand=point(wrist)
            disk(hand+[0,-height*.012],height*.04,dark)
            disk(hand,height*.034,(65,92,109))
            disk(hand+[-height*.003,-height*.006],height*.028,light)
            disk(hand+[-height*.01,-height*.011],height*.012,(255,255,247))
            pygame.draw.line(surface,suit,ip(hand+[-height*.025,height*.007]),ip(hand+[height*.025,height*.007]),max(2,round(height*.009)))
        # Rounded dimensional helmet and visor. Layers provide material highlights.
        radius=height*.091
        disk(head+[2,3],radius+3,dark)
        disk(head,radius,(146,167,184))
        disk(head+[-radius*.08,-radius*.10],radius*.95,(222,230,234))
        disk(head+[-radius*.15,-radius*.20],radius*.77,(249,248,239))
        visor=pygame.Rect(0,0,radius*1.82,radius*1.05)
        visor.center=ip(head+[0,radius*.10])
        pygame.draw.rect(surface,(5,22,35),visor,border_radius=max(4,round(radius*.40)))
        shine=pygame.Rect(visor.left+5,visor.top+3,visor.width-10,max(2,radius*.13))
        pygame.draw.rect(surface,(44,82,99),shine,border_radius=4)
        blink=math.sin(now*.61)>.995
        for dx in (-.37,.37):
            eye=pygame.Rect(0,0,radius*.22,radius*(.12 if blink else .39))
            eye.center=ip(head+[radius*dx,radius*.12])
            pygame.draw.rect(surface,(116,250,244) if not ghost else (255,184,125),eye,border_radius=max(2,round(radius*.08)))
        for sign in (-1,1):
            ear=pygame.Rect(0,0,height*.031,height*.066)
            ear.center=ip(head+[sign*radius*.94,0])
            pygame.draw.rect(surface,dark,ear.inflate(4,4),border_radius=5)
            pygame.draw.rect(surface,suit,ear,border_radius=5)
            pygame.draw.line(surface,bright,(ear.left+3,ear.top+4),(ear.left+3,ear.bottom-4),2)
        crest=pygame.Rect(0,0,radius*.27,radius*.17)
        crest.center=ip(head+[0,-radius*.83])
        pygame.draw.rect(surface,suit,crest,border_radius=3)
