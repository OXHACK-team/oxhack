"""Mirrored camera guidance using detected body geometry, never result ordering."""
import numpy as np
import pygame
from tracking_types import NOSE,LS,RS,LE,RE,LW,RW,LH,RH,LK,RK,LA,RA,CORE
from ui.theme import CYAN,ORANGE,font


BONES=((NOSE,LS),(NOSE,RS),(LS,RS),(LS,LE),(LE,LW),(RS,RE),(RE,RW),
       (LS,LH),(RS,RH),(LH,RH),(LH,LK),(LK,LA),(RH,RK),(RK,RA))


def labelled_bodies(source,dual=False):
    """Return (label, colour, landmarks), assigning lanes by reliable hip centre."""
    bodies=list(source.poses) if source.poses else ([source.landmarks] if source.landmarks is not None else [])
    if not dual:
        return [("BODY" if len(bodies)>1 else "YOU",CYAN,p) for p in bodies]
    centers=[]
    for p in bodies:
        hips=p[[LH,RH]]
        centers.append(float(np.mean(hips[:,0])) if np.isfinite(hips).all() and np.min(hips[:,3])>=.35 else None)
    valid=[c for c in centers if c is not None]
    ambiguous=len(bodies)>2 or len(valid)!=len(bodies) or (len(valid)==2 and (min(valid)>.48 or max(valid)<.52 or max(valid)-min(valid)<.14))
    labelled=[]
    for p,c in zip(bodies,centers):
        if c is None:
            labelled.append(("HIPS UNCLEAR",ORANGE,p))
        elif ambiguous or .48<=c<=.52:
            labelled.append(("SEPARATE / OWN LANE",ORANGE,p))
        else:
            labelled.append(("P1 / LEFT" if c<.48 else "P2 / RIGHT",CYAN if c<.48 else ORANGE,p))
    return labelled


def _tag(surface,value,pos,color,clip):
    size=max(9,min(13,round(clip.height*.065)))
    rendered=font(size,True).render(value,True,color)
    box=rendered.get_rect(topleft=pos).inflate(10,6)
    box.clamp_ip(clip)
    pygame.draw.rect(surface,(5,18,30),box,border_radius=4)
    pygame.draw.rect(surface,color,box,1,border_radius=4)
    surface.blit(rendered,rendered.get_rect(center=box.center))


def _stand_marker(surface,rect,slot,dual):
    cx=rect.x+rect.width*((slot+.5)/2 if dual else .5)
    half=rect.width*(.20 if dual else .29)
    color=(81,147,163) if slot==0 else (172,126,89)
    y=rect.y+rect.height*.86
    for side in (-1,1):
        x=cx+side*half
        pygame.draw.lines(surface,color,False,[(x,y-rect.height*.16),(x,y),(x-side*10,y)],2)
    _tag(surface,("P1 LEFT" if slot==0 else "P2 RIGHT") if dual else "STAND IN VIEW",(round(cx-half),round(y+4)),color,rect)


def draw_tracking_overlay(surface,rect,source,dual=False,now=0):
    """Draw onto the exact aspect-fitted RGB image rectangle supplied by Screens.

    Source landmarks must remain global mirrored image coordinates. The caller
    passes the image bounds, not the outer camera-preview panel, so letterboxing
    never shifts the skeleton away from the actual body.
    """
    rect=pygame.Rect(rect)
    if rect.width<24 or rect.height<24:
        return
    previous_clip=surface.get_clip()
    surface.set_clip(previous_clip.clip(rect))
    try:
        bodies=labelled_bodies(source,dual)
        if dual:
            for y in range(rect.y+4,rect.bottom-4,9):
                pygame.draw.line(surface,(228,164,105),(rect.centerx,y),(rect.centerx,min(y+4,rect.bottom-4)),1)
            occupied={0 if label.startswith("P1") else 1 for label,_,_ in bodies if label.startswith(("P1","P2"))}
            for slot in range(2):
                if slot not in occupied:
                    _stand_marker(surface,rect,slot,True)
        elif not bodies:
            _stand_marker(surface,rect,0,False)
        radius=max(2,min(4,round(rect.height*.014)))
        line_width=max(1,min(3,round(rect.height*.009)))
        for label,color,p in bodies:
            finite=np.isfinite(p[:,:2]).all(axis=1)
            visible=finite & np.isfinite(p[:,3]) & (p[:,3]>=.35)
            def point(i):
                x,y=np.clip(p[i,:2],-1.,2.)
                return (round(rect.x+x*rect.width),round(rect.y+y*rect.height))
            for a,b in BONES:
                if visible[a] and visible[b]:
                    pygame.draw.line(surface,(5,18,28),point(a),point(b),line_width+2)
                    pygame.draw.line(surface,color,point(a),point(b),line_width)
            points=[]
            for i in CORE:
                if not finite[i]:
                    continue
                xy=point(i)
                if visible[i]:
                    pygame.draw.circle(surface,(5,18,28),xy,radius+1)
                    pygame.draw.circle(surface,color,xy,radius)
                    points.append(xy)
                elif -.1<=p[i,0]<=1.1 and -.1<=p[i,1]<=1.1:
                    pygame.draw.circle(surface,ORANGE,xy,radius+2,1)
            if len(points)>=3:
                xs,ys=zip(*points)
                bounds=pygame.Rect(min(xs)-7,min(ys)-7,max(xs)-min(xs)+14,max(ys)-min(ys)+14).clip(rect)
                corner=max(5,min(13,round(rect.height*.06)))
                for x,y,sx,sy in ((bounds.left,bounds.top,1,1),(bounds.right-1,bounds.top,-1,1),
                                  (bounds.left,bounds.bottom-1,1,-1),(bounds.right-1,bounds.bottom-1,-1,-1)):
                    pygame.draw.lines(surface,color,False,[(x,y+sy*corner),(x,y),(x+sx*corner,y)],2)
                if label!="SEPARATE / OWN LANE":
                    _tag(surface,label,(bounds.left,max(rect.y+3,bounds.top-21)),color,rect)
        if any(label=="SEPARATE / OWN LANE" for label,_,_ in bodies):
            _tag(surface,"SEPARATE / OWN LANE",(rect.x+5,rect.y+5),ORANGE,rect)
        if now and now-source.timestamp>.55:
            _tag(surface,"WAITING FOR FRAME",(rect.x+5,rect.y+5),ORANGE,rect)
    finally:
        surface.set_clip(previous_clip)
