"""Textured body-part rig: 3D-shaded sprites transformed by live tracked joints."""
import math
from functools import lru_cache
import numpy as np
import pygame
from config import ROOT
from tracking_types import *


class SpriteRig:
    def __init__(self):
        atlas=pygame.image.load(str(ROOT/"assets/athlete-rig.png")).convert_alpha()
        cw,ch=atlas.get_width()//3,atlas.get_height()//3
        self.parts=[]
        for i in range(9):
            part=atlas.subsurface((i%3*cw,i//3*ch,cw,ch)).copy()
            bounds=part.get_bounding_rect(min_alpha=210)
            self.parts.append(part.subsurface(bounds).copy())

    @lru_cache(maxsize=64)
    def variant(self,index,color,flip):
        part=self.parts[index].copy()
        if color!=(78,233,232):
            pixels=pygame.surfarray.pixels3d(part)
            data=pixels.astype(np.float32)
            mask=(data[:,:,1]>data[:,:,0]*1.17)&(data[:,:,2]>data[:,:,0]*1.17)&(data[:,:,1]>65)
            strength=data[:,:,1]/210
            for channel in range(3):
                pixels[:,:,channel][mask]=np.clip(strength[mask]*color[channel],0,255).astype(np.uint8)
            del pixels
        return pygame.transform.flip(part,True,False) if flip else part

    @lru_cache(maxsize=640)
    def transformed(self,index,width,height,angle,color,flip=False):
        source=self.variant(index,color,flip)
        scaled=pygame.transform.smoothscale(source,(max(2,width),max(2,height)))
        return pygame.transform.rotate(scaled,angle)

    def draw(self,surface,p,cx,top,height,aspect,now,color):
        scale=height/.8
        def point(i):
            return np.array([cx+(p[i,0]-.5)*scale*aspect,top+(p[i,1]-.12)*scale])
        def part(index,center,w,h,angle=0,flip=False):
            image=self.transformed(index,max(2,round(w)),max(2,round(h)),round(angle),tuple(color),flip)
            surface.blit(image,image.get_rect(center=tuple(map(round,center))))
        def bone(index,a,b,width,flip=False):
            start,end=point(a),point(b)
            vector=end-start
            length=float(np.linalg.norm(vector))
            angle=math.degrees(math.atan2(vector[0],vector[1]))
            part(index,(start+end)/2,width*height,length+height*.035,angle,flip)
        def glove(elbow,wrist,flip=False):
            direction=point(wrist)-point(elbow)
            length=max(1.,float(np.linalg.norm(direction)))
            center=point(wrist)+direction/length*height*.023
            angle=math.degrees(math.atan2(direction[0],direction[1]))
            part(4,center,height*.087,height*.12,angle,flip)
        # Shadow anchors the character to the arena surface.
        shadow=pygame.Rect(0,0,height*.52,height*.075)
        shadow.center=(round(cx),round(top+height*1.04))
        pygame.draw.ellipse(surface,(8,29,39),shadow)
        pygame.draw.ellipse(surface,tuple(round(c*.6) for c in color),shadow,2)
        bone(2,RS,RE,.092,True)
        bone(3,RE,RW,.079,True)
        glove(RE,RW,True)
        for hip,knee,ankle,flip in ((RH,RK,RA,True),(LH,LK,LA,False)):
            bone(5,hip,knee,.104,flip)
            bone(6,knee,ankle,.09,flip)
            part(7,point(ankle)+[0,height*.023],height*.132,height*.101,flip=flip)
        shoulder=np.mean([point(LS),point(RS)],axis=0)
        hip=np.mean([point(LH),point(RH)],axis=0)
        torso_vector=hip-shoulder
        angle=math.degrees(math.atan2(torso_vector[0],torso_vector[1]))
        torso_width=float(np.linalg.norm(point(LS)-point(RS)))+height*.13
        torso_height=float(np.linalg.norm(torso_vector))+height*.095
        part(1,(shoulder+hip)/2,torso_width,torso_height,angle)
        bone(2,LS,LE,.092)
        bone(3,LE,LW,.079)
        glove(LE,LW)
        part(8,point(LS),height*.105,height*.104)
        part(8,point(RS),height*.105,height*.104,flip=True)
        head=point(NOSE)+[0,height*.025]
        part(0,head,height*.215,height*.212,angle*.28)
