"""Runtime loading/cropping of the original generated arena and six-cell atlas."""
from functools import lru_cache
import pygame
from config import ROOT


class Art:
    def __init__(self):
        self.stadium=self.load("chrono-stadium.png")
        self.atlas=self.load("game-atlas.png")

    def load(self,name):
        path=ROOT/"assets"/name
        return pygame.image.load(str(path)).convert() if path.exists() else None

    @lru_cache(maxsize=80)
    def image(self,key,width,height,shade=0):
        source=self.stadium if key=="stadium" else self.atlas
        if source is None:
            surface=pygame.Surface((width,height))
            surface.fill((22,37,57))
            return surface
        if key!="stadium":
            cw,ch=source.get_width()//3,source.get_height()//2
            index=int(key)
            source=source.subsurface((index%3*cw,index//3*ch,cw,ch))
        ratio=max(width/source.get_width(),height/source.get_height())
        scaled=pygame.transform.smoothscale(source,(round(source.get_width()*ratio),round(source.get_height()*ratio)))
        surface=pygame.Surface((width,height))
        surface.blit(scaled,scaled.get_rect(center=(width//2,height//2)))
        if shade:
            overlay=pygame.Surface((width,height),pygame.SRCALPHA)
            overlay.fill((4,12,26,shade))
            surface.blit(overlay,(0,0))
        return surface


@lru_cache(maxsize=48)
def gradient(width,height,alpha_top=0,alpha_bottom=240):
    result=pygame.Surface((width,height),pygame.SRCALPHA)
    for y in range(height):
        t=y/max(1,height-1)
        alpha=round(alpha_top+(alpha_bottom-alpha_top)*t)
        pygame.draw.line(result,(5,13,28,alpha),(0,y),(width,y))
    return result
