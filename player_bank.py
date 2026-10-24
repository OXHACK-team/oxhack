"""Fixed spatial lanes prevent MediaPipe result ordering from swapping controls."""
import numpy as np
from movement import MovementDetector
from motion_input import from_player
from player_manager import PlayerManager
from tracking_types import TrackingFrame,LH,RH


class PlayerBank:
    def __init__(self,config):
        self.config=config
        self.players=[PlayerManager(config,f"Player {i+1}") for i in range(2)]
        self.movement=[MovementDetector(config),MovementDetector(config)]
        self.frames=[]
        self.actions=[]

    def reset(self):
        for player,detector in zip(self.players,self.movement):
            player.reset()
            detector.reset()
        self.frames=[]
        self.actions=[]

    def update(self,source,now,dual=False):
        frames=[]
        if not dual:
            frames=[source]
            # A partner walking into view must not steal the registered player's
            # controls or lock the menu before they can choose Two Players.
            anchor=self.players[0].last_center
            if source.people>1 and anchor is not None and source.poses:
                ordered=sorted(source.poses,key=lambda p:float(np.linalg.norm(np.mean(p[[LH,RH],:2],axis=0)-anchor)))
                distances=[float(np.linalg.norm(np.mean(p[[LH,RH],:2],axis=0)-anchor)) for p in ordered]
                if distances[0]<.18 and (len(distances)==1 or distances[1]-distances[0]>.08):
                    frames=[TrackingFrame(source.timestamp,ordered[0],source.frame,source.hands,1,
                                          "Registered player tracked",source.inference_ms,source.aspect)]
        else:
            bodies=source.poses or ([source.landmarks] if source.landmarks is not None else [])
            centers=[float(np.mean(p[[LH,RH],0])) for p in bodies]
            safe=len(bodies)<=2 and not (len(centers)==2 and (min(centers)>.48 or max(centers)<.52 or max(centers)-min(centers)<.14))
            for slot in range(2):
                eligible=[p for p,c in zip(bodies,centers) if (c<.48 if slot==0 else c>.52)] if safe else []
                p=eligible[0].copy() if len(eligible)==1 else None
                if not safe and self.players[slot].registered:
                    self.players[slot].request_rejoin()
                if p is not None:
                    p[:,0]=(p[:,0]-slot*.5)*2
                hands=[np.array([(h[0]-slot*.5)*2,h[1]]) for h in source.hands if slot*.5<=h[0]<(slot+1)*.5]
                message="Stay in your lane. Player 1 LEFT, Player 2 RIGHT." if not safe else f"Player {slot+1}: stand fully in your half of the camera."
                frames.append(TrackingFrame(source.timestamp,p,source.frame,hands,1 if p is not None else 0,
                                            message,source.inference_ms,source.aspect/2,
                                            x_bounds=(.03-slot,1.97-slot)))
        self.frames=frames
        self.actions=[]
        for i,frame in enumerate(frames):
            player,detector=self.players[i],self.movement[i]
            player.update(frame,now)
            if player.valid and player.smoothed is not None:
                detector.update(player.smoothed,frame.timestamp,player.body_scale,frame.aspect)
            else:
                detector.reset()
            self.actions.append(from_player(player,detector,frame.aspect))
        return self.actions
