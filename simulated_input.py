"""Synthetic landmarks exercise the SAME registration/motion path as the webcam."""
import math
from tracking_types import *


class SimulatedInput:
    def __init__(self):
        self.phase = 0.

    def sample(self, now, dt, raise_hand=False, running=False, crouch=False, lean=0., lost=False, cursor=None,both_up=False,right_up=False):
        if lost:
            return TrackingFrame(now, status="Simulated tracking lost")
        p = neutral_pose()
        if running:
            self.phase += dt * 12
            swing = math.sin(self.phase)
            p[LK, 1] -= max(0, swing) * .12
            p[RK, 1] -= max(0, -swing) * .12
            p[LA, 1] -= max(0, swing) * .1
            p[RA, 1] -= max(0, -swing) * .1
            p[LW, 1] += swing * .1
            p[RW, 1] -= swing * .1
            p[LE, 1] += swing * .045
            p[RE, 1] -= swing * .045
            p[[NOSE, LS, RS, LH, RH], 1] += abs(swing) * .012
        if raise_hand:
            p[LW, :2], p[LE, :2] = (.3, .07), (.33, .2)
        if both_up:
            p[LW,:2],p[LE,:2]=(.3,.07),(.33,.2)
            p[RW,:2],p[RE,:2]=(.7,.07),(.67,.2)
        elif right_up:
            p[RW,:2],p[RE,:2]=(.7,.07),(.67,.2)
        if crouch:
            p[[NOSE, LS, RS, LE, RE, LW, RW, LH, RH], 1] += .13
            p[LK, 0] -= .05
            p[RK, 0] += .05
        p[[NOSE, LS, RS, LE, RE, LW, RW], 0] += lean * .09
        if cursor is not None:
            shoulder=np.mean(p[[LS,RS],:2],axis=0)
            torso=float(np.mean(p[[LH,RH],1])-shoulder[1])
            p[RW,:2]=[shoulder[0]+(cursor[0]/1440-.5)*torso*2.9,
                      shoulder[1]-torso*.65+(cursor[1]/900)*torso*1.6]
            p[RE,:2]=(p[RS,:2]+p[RW,:2])/2
        return TrackingFrame(now, p, people=1, status="Demo player", aspect=4/3)
