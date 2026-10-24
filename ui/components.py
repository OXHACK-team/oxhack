from dataclasses import dataclass
import pygame
from ui.theme import *


@dataclass
class Button:
    key: str
    rect: pygame.Rect
    label: str
    subtitle: str = ""
    color: tuple = CYAN
    enabled: bool = True
    primary: bool = False

    def draw(self, surface, hovered=False, now=0.):
        color = self.color if self.enabled else MUTED
        amount=float(hovered) if self.enabled else 0.
        mix=lambda left,right: tuple(int(a+(b-a)*amount) for a,b in zip(left,right))
        fill = mix(PANEL,(27,52,62))
        if self.primary:
            fill = mix(color,tuple(min(255,c+22) for c in color)) if self.enabled else EDGE
        panel(surface,self.rect.move(0,5),(4,14,25),None,17)
        panel(surface, self.rect, fill, color if self.primary else mix(EDGE,color), 17)
        ink = BG if self.primary else WHITE if self.enabled else MUTED
        if self.subtitle:
            fit_text(surface, self.label, (self.rect.x+26,self.rect.y+15),self.rect.width-82, 26, ink, True)
            text(surface, self.subtitle, (self.rect.x+26,self.rect.y+49), 16, BG if self.primary else MUTED)
        else:
            fit_text(surface, self.label, (self.rect.x+24, self.rect.centery-14),self.rect.width-72, 25, ink, True)
        x, y = self.rect.right-30, self.rect.centery
        if self.enabled:
            pygame.draw.lines(surface, ink, False, [(x-6,y-6),(x,y),(x-6,y+6)], 2)


class GameCard(Button):
    def __init__(self,card,rect,art):
        super().__init__(card["id"],pygame.Rect(rect),card["short"],color=card["color"])
        self.card=card
        from ui.art import gradient
        self.image=art.image(card["art"],self.rect.width,self.rect.height).copy()
        self.image.blit(gradient(self.rect.width,self.rect.height,0,252),(0,0))
        mask=pygame.Surface(self.rect.size,pygame.SRCALPHA)
        pygame.draw.rect(mask,(255,255,255),mask.get_rect(),border_radius=20)
        self.image=self.image.convert_alpha()
        self.image.blit(mask,(0,0),special_flags=pygame.BLEND_RGBA_MULT)

    def draw(self,surface,hovered=False,now=0.):
        amount=float(hovered)
        rect=self.rect.move(0,-round(amount*4))
        panel(surface,rect.move(0,8),(4,12,22),None,20)
        surface.blit(self.image,rect)
        pygame.draw.rect(surface,self.color if amount>.1 else (72,89,107),rect,round(1+amount*2),border_radius=20)
        pill(surface,self.card["tag"],(rect.x+19,rect.y+16),self.color,12)
        fit_text(surface,self.label,(rect.x+21,rect.bottom-74),rect.width-78,28,WHITE,True)
        text(surface,self.card["control"],(rect.x+22,rect.bottom-33),13,MUTED,mono=True)
        x,y=rect.right-36,rect.bottom-51
        pygame.draw.circle(surface,self.color,(x,y),17)
        pygame.draw.polygon(surface,BG,[(x-4,y-7),(x-4,y+7),(x+6,y)])


class ModeCard(Button):
    def __init__(self,key,rect,label,subtitle,number,color=CYAN):
        super().__init__(key,pygame.Rect(rect),label,subtitle,color)
        self.number=number

    def draw(self,surface,hovered=False,now=0.):
        amount=float(hovered)
        fill=tuple(round(a+(b-a)*amount) for a,b in zip(PANEL,(30,57,70)))
        panel(surface,self.rect.move(0,6),(4,14,26),None,22)
        panel(surface,self.rect,fill,self.color if amount>.1 else EDGE,22)
        cx,cy=self.rect.x+65,self.rect.centery
        ring(surface,(cx,cy),33,.78,self.color,2)
        if self.number==0:
            clock_icon(surface,(cx,cy),19,self.color,now*.4)
        else:
            count=min(self.number,3)
            for i in range(count):
                x=cx+(i-(count-1)/2)*17
                pygame.draw.circle(surface,self.color,(round(x),cy-7),6)
                pygame.draw.line(surface,self.color,(x,cy+3),(x,cy+16),9)
        text(surface,self.label,(self.rect.x+123,self.rect.y+29),30,WHITE,True)
        wrapped(surface,self.subtitle,(self.rect.x+124,self.rect.y+79),self.rect.width-155,20,MUTED)


def cursor(surface, position, progress, color=CYAN):
    if position is None:
        return
    x,y = map(int,position)
    pygame.draw.circle(surface, BG, (x,y), 17)
    pygame.draw.circle(surface, color, (x,y), 7)
    pygame.draw.circle(surface, WHITE, (x,y), 3)
    ring(surface, (x,y), 24, progress, color, 4)
