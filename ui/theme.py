import math
from functools import lru_cache
import pygame

W, H = 1440, 900
BG = (8, 20, 35)
PANEL = (17, 34, 51)
EDGE = (53, 76, 94)
WHITE = (249, 246, 235)
MUTED = (170, 187, 201)
CYAN = (78, 233, 232)
GREEN = (155, 246, 124)
PURPLE = (162, 135, 255)
ORANGE = (255, 157, 111)
RED = (255, 105, 125)


@lru_cache(maxsize=64)
def font(size, bold=False, mono=False):
    name = "consolas" if mono else "bahnschrift,dejavusans,arial"
    return pygame.font.SysFont(name, size, bold=bold)


def text(surface, value, pos, size=22, color=WHITE, bold=False, center=False, mono=False):
    rendered = font(size, bold, mono).render(str(value), True, color)
    rect = rendered.get_rect(center=pos) if center else rendered.get_rect(topleft=pos)
    surface.blit(rendered, rect)
    return rect


def fit_text(surface,value,pos,max_width,size=22,color=WHITE,bold=False,center=False,mono=False):
    while size>12 and font(size,bold,mono).size(str(value))[0]>max_width:
        size-=1
    return text(surface,value,pos,size,color,bold,center,mono)


def wrapped(surface,value,pos,width,size=22,color=MUTED,line_height=None,bold=False):
    x,y=pos
    words=str(value).split()
    line=""
    for word in words:
        candidate=(line+" "+word).strip()
        if line and font(size,bold).size(candidate)[0]>width:
            text(surface,line,(x,y),size,color,bold)
            y+=line_height or round(size*1.4)
            line=word
        else:
            line=candidate
    if line:
        text(surface,line,(x,y),size,color,bold)
        y+=line_height or round(size*1.4)
    return y


def panel(surface, rect, color=PANEL, border=EDGE, radius=22):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surface, border, rect, 1, border_radius=radius)


def pill(surface, value, pos, color=CYAN, size=16):
    width = font(size).size(value)[0] + 32
    rect = pygame.Rect(*pos, width, 32)
    panel(surface, rect, tuple(int(c * .13 + 10) for c in color), tuple(int(c * .35) for c in color), 16)
    text(surface, value, rect.center, size, color, center=True)
    return rect


def ring(surface, center, radius, progress=1., color=CYAN, width=5):
    rect = pygame.Rect(0, 0, radius * 2, radius * 2)
    rect.center = center
    pygame.draw.circle(surface, EDGE, center, radius, width)
    if progress > .001:
        pygame.draw.arc(surface, color, rect, -math.pi / 2, -math.pi / 2 + math.tau * min(progress, .9999), width)


def clock_icon(surface, center, radius=16, color=CYAN, time_angle=0.):
    pygame.draw.circle(surface, color, center, radius, 2)
    x, y = center
    pygame.draw.line(surface, color, center, (x + math.sin(time_angle) * radius * .65, y - math.cos(time_angle) * radius * .65), 2)
    pygame.draw.line(surface, color, center, (x + radius * .45, y + radius * .2), 2)


def progress_track(surface,rect,progress,color=CYAN):
    rect=pygame.Rect(rect)
    pygame.draw.rect(surface,(35,54,71),rect,border_radius=max(2,rect.height//2))
    value=max(0.,min(1.,progress))
    if value:
        fill=pygame.Rect(rect.x,rect.y,max(rect.height,round(rect.width*value)),rect.height)
        pygame.draw.rect(surface,color,fill,border_radius=max(2,rect.height//2))


def medal(surface,center,grade,color=ORANGE,radius=57,phase=0.):
    x,y=center
    for i in range(24):
        angle=i*math.tau/24
        length=8 if i%2==0 else 4
        outer=(x+math.sin(angle)*(radius+12),y+math.cos(angle)*(radius+12))
        inner=(x+math.sin(angle)*(radius+12-length),y+math.cos(angle)*(radius+12-length))
        pygame.draw.line(surface,color if i%2==0 else EDGE,inner,outer,2)
    points=[(x+math.sin(i*math.tau/6)*radius,y+math.cos(i*math.tau/6)*radius) for i in range(6)]
    pygame.draw.polygon(surface,(10,26,42),points)
    pygame.draw.polygon(surface,color,points,3)
    pygame.draw.circle(surface,tuple(round(c*.35) for c in color),(round(x),round(y)),radius-11,1)
    text(surface,grade,(x,y-3),round(radius*1.15),color,True,True)
    for dx in (-17,0,17):
        pygame.draw.circle(surface,color,(round(x+dx),round(y+radius*.60)),2)


class Background:
    def __init__(self):
        self.base = pygame.Surface((W, H))
        for y in range(H):
            t = y / H
            pygame.draw.line(self.base, (int(9+6*t), int(14+8*t), int(31+10*t)), (0,y),(W,y))
        for x in range(0, W, 44):
            for y in range(0, H, 44):
                pygame.draw.circle(self.base, (26, 37, 56), (x,y), 1)

    def draw(self, surface, now):
        surface.blit(self.base, (0,0))
        for i in range(4):
            x, y = 1130, 380
            r = 150 + i * 72
            rect = (x-r,y-r,r*2,r*2)
            pygame.draw.arc(surface, (25+i*2, 46+i*2, 65+i*2), rect, now * .07 + i, now * .07 + i + 1.8, 1)
        for i in range(18):
            x = (i * 97 + now * (6 + i % 3)) % W
            y = (i * 181) % H
            pygame.draw.circle(surface, (38,80,95), (int(x),y), 2 if i % 5 == 0 else 1)
