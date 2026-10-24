"""Scenes, shared input, fair matches, party turns, persistence and rendering."""
import math
import random
import sqlite3
import time
from pathlib import Path
import numpy as np
import pygame
from audio import Audio
from avatar import Avatar
from camera import Camera
from config import ROOT
from games import GAMES,MODES
from gesture_controller import GestureController
from match import Match,ranking_key
from player_bank import PlayerBank
from pose_tracker import PoseTracker
from simulated_input import SimulatedInput
from storage import Storage
from tracking_types import TrackingFrame,neutral_pose,LS,RS,LH,RH
from ui.art import Art
from ui.components import cursor
from ui.screens import Screens
from ui.theme import *


class App:
    def __init__(self,config,demo=False,windowed=False,data_path=None,no_camera=False,settings_path=None):
        self.config,self.demo=config,demo
        self.settings_path=Path(settings_path) if settings_path else ROOT/"config.json"
        pygame.mixer.pre_init(44100,-16,2,512)
        pygame.init()
        self.fullscreen=config.fullscreen and not windowed
        self.window=pygame.display.set_mode((0,0) if self.fullscreen else (1152,720),pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE)
        pygame.display.set_caption("CHRONO ARENA | Own the next second")
        pygame.mouse.set_visible(False)
        self.canvas=pygame.Surface((W,H))
        self.clock=pygame.time.Clock()
        self.art=Art()
        self.avatar=Avatar()
        self.audio=Audio(config)
        self.storage=Storage(data_path)
        self.bank=PlayerBank(config)
        self.player=self.bank.players[0]
        self.movement=self.bank.movement[0]
        self.gesture=GestureController(config)
        self.sims=[SimulatedInput(),SimulatedInput()]
        self.sim=self.sims[0]
        self.dual_active=False
        self.demo_hands=[np.array([.5,.5]),np.array([.5,.5])]
        self.camera=self.tracker=None
        if not demo and not no_camera:
            self.camera=Camera(config)
            self.tracker=PoseTracker(self.camera,config)
            self.camera.start()
            self.tracker.start()
        stamp=time.perf_counter()
        self.source_frame=TrackingFrame(stamp,status="Camera disabled. Choose demo to play." if no_camera else "Opening camera...")
        self.frame=self.source_frame
        self.scene="welcome"
        self.scene_started=stamp
        self.after_join="menu"
        self.running=True
        self.selected_game="red_green"
        self.session_mode="solo"
        self.party_count=2
        self.party_index=0
        self.party_results=[]
        self.challenge_seed=2026
        self.match=None
        self.game=None
        self.rng=random.Random()
        self.result_id=None
        self.previous_best=None
        self.personal_best=False
        self.record_saved=False
        self.match_finished_at=None
        self.last_error=""
        self.diagnostics=False
        self.cursor_pos=None
        self.input_mode="mouse" if demo else "hand"
        self.hand_return_started=None
        self.focus=-1
        self.menu_controller=None
        self.buttons=[]
        self.hovered=None
        self.hover_levels={}
        self.last_render=None
        self.fps=0.
        self.viewport=pygame.Rect(0,0,*self.window.get_size())
        self.transition_start=stamp
        self.transition_from=None
        self.scaled_window=None
        self.screens=Screens(self)
        self._closed=False

    @property
    def mode(self):
        return "demo" if self.demo else "camera"

    @property
    def variant(self):
        return "endless" if self.config.endless else "challenge"

    @property
    def card(self):
        return GAMES[self.selected_game]

    @property
    def current_name(self):
        return f"Player {self.party_index+1}" if self.session_mode=="party" else self.config.player_name

    def change_scene(self,scene,now):
        if scene==self.scene:
            return
        self.transition_from=self.canvas.copy()
        self.transition_start=now
        self.scene,self.scene_started=scene,now
        self.gesture.reset(now)
        self.focus=-1
        self.hovered=None

    def set_demo(self,now):
        if self.tracker:
            self.tracker.close()
            self.tracker=None
        if self.camera:
            self.camera.close()
            self.camera=None
        self.demo=True
        self.dual_active=False
        self.bank.reset()
        self.match=self.game=None
        self.after_join="menu"
        self.input_mode="mouse"
        self.change_scene("welcome",now)

    def quick_join(self,now):
        if not self.demo:
            self.set_demo(now)
            return
        for i in range(2 if self.dual_active else 1):
            player=self.bank.players[i]
            frame=self.bank.frames[i] if len(self.bank.frames)>i else None
            p=frame.landmarks.copy() if frame and frame.landmarks is not None else neutral_pose()
            player.neutral=p.copy()
            player.smoothed=p.copy()
            aspect=frame.aspect if frame else 4/3
            player.body_scale=max(.08,float(np.linalg.norm((np.mean(p[[LH,RH],:2],axis=0)-np.mean(p[[LS,RS],:2],axis=0))*[aspect,1])))
            player.registered=player.valid=True
            player.needs_rejoin=False
            player.last_good=now
        self.audio.play("join")
        self.change_scene("briefing" if self.scene=="lobby" else "connected",now)

    def set_camera(self,now):
        self.demo=False
        self.dual_active=False
        self.bank.reset()
        self.match=self.game=None
        self.after_join="menu"
        self.input_mode="hand"
        self.source_frame=TrackingFrame(now,status="Opening camera...")
        self.camera=Camera(self.config)
        self.tracker=PoseTracker(self.camera,self.config)
        self.camera.start()
        self.tracker.start()
        self.change_scene("welcome",now)

    def start_match(self,now):
        if not all(p.registered and p.valid for p in self.bank.players[:2 if self.session_mode=="duo" else 1]):
            self.after_join="briefing"
            self.change_scene("lobby" if self.dual_active else "welcome",now)
            return
        names=[self.current_name,"Player 2"] if self.session_mode=="duo" else [self.current_name]
        self.match=Match(self.config,self.selected_game,self.session_mode,now,names,self.challenge_seed,self.config.ai_difficulty)
        self.game=self.match.games[0]
        lookup=self.storage.best if self.game.metric=="time" else self.storage.best_score
        self.previous_best=lookup(self.current_name,self.mode,self.selected_game,self.session_mode,self.variant)
        self.personal_best=self.record_saved=False
        self.match_finished_at=None
        self.last_error=""
        self.result_id=None
        for detector in self.bank.movement:
            detector.reset()
        self.change_scene("game",now)

    def choose_mode(self,mode,now):
        self.session_mode=mode
        self.party_index=0
        self.party_results=[]
        self.challenge_seed=self.rng.getrandbits(31)
        if mode=="duo":
            self.dual_active=True
            self.bank.reset()
            self.change_scene("lobby",now)
        else:
            if self.dual_active:
                self.dual_active=False
                self.bank.reset()
            if not self.player.registered or self.player.needs_rejoin:
                self.after_join="briefing"
                self.change_scene("welcome",now)
            else:
                self.change_scene("briefing",now)

    def go_back(self,now):
        if self.scene=="game" and self.match:
            if self.match.finished:
                self.change_scene("results",now)
                return
            self.match.manual_pause=not self.match.manual_pause
            self.gesture.reset(now)
            return
        target={"select":"menu","mode":"select","briefing":"mode","settings":"menu","how":"menu",
                "results":"select","lobby":"mode","handoff":"select","connected":"menu"}.get(self.scene)
        if target:
            self.change_scene(target,now)
        elif self.scene=="welcome":
            self.running=False

    def activate(self,key,now):
        self.audio.play("select")
        if key in ("demo","join_demo"):
            self.quick_join(now)
        elif key=="camera_mode":
            self.set_camera(now) if self.demo else self.set_demo(now)
        elif key=="input_toggle":
            self.input_mode="hand" if self.input_mode!="hand" else "mouse"
            self.gesture.reset(now)
        elif key=="play":
            self.change_scene("select",now)
        elif key in GAMES:
            self.selected_game=key
            self.change_scene("mode",now)
        elif key.startswith("mode_"):
            self.choose_mode(key[5:],now)
        elif key=="start":
            self.start_match(now)
        elif key in ("variant_endless","variant_challenge"):
            self.config.endless=key=="variant_endless"
        elif key=="again":
            self.party_index=0
            self.party_results=[]
            self.challenge_seed=self.rng.getrandbits(31)
            if self.session_mode=="party":
                self.bank.reset()
                self.after_join="briefing"
                self.change_scene("handoff",now)
            else:
                self.start_match(now)
        elif key=="next_player":
            self.party_index+=1
            self.bank.reset()
            self.after_join="briefing"
            self.change_scene("handoff",now)
        elif key in ("party_less","party_more"):
            self.party_count=max(2,min(4,self.party_count+(-1 if key=="party_less" else 1)))
        elif key.startswith("difficulty_"):
            self.config.ai_difficulty=key[11:]
            self._save_settings()
        elif key in ("how","settings"):
            self.change_scene(key,now)
        elif key=="back":
            self.go_back(now)
        elif key=="resume" and self.match:
            self.match.manual_pause=False
            self.gesture.reset(now)
        elif key in ("menu","all_games"):
            self.match=self.game=None
            self.change_scene("menu" if key=="menu" else "select",now)
        elif key=="rejoin" and self.scene=="game" and self.match:
            for i in range(self.match.human_count):
                if not self.bank.players[i].valid and not self.match.games[i].finished:
                    self.bank.players[i].request_rejoin()
                    self.bank.movement[i].reset()
        elif key=="end_run" and self.match:
            for game in self.match.games:
                game.finish(False)
            self._save_results()
            self.change_scene("results",now)
        elif key in ("calibrate","rejoin"):
            self.match=self.game=None
            self.bank.reset()
            self.after_join="briefing" if key=="rejoin" else "menu"
            self.change_scene("lobby" if self.dual_active else "welcome",now)
        elif key in ("less","more"):
            self.config.sensitivity=round(max(.4,min(2.,self.config.sensitivity+(-.2 if key=="less" else .2))),1)
            self._save_settings()
        elif key in ("sound","preview"):
            field="sound" if key=="sound" else "show_preview"
            setattr(self.config,field,not getattr(self.config,field))
            self._save_settings()
        elif key=="exit":
            self.running=False

    def _save_settings(self):
        try:
            self.config.save(self.settings_path)
        except OSError as exc:
            self.last_error=f"Settings could not be saved: {exc}"

    def _mouse_position(self,xy):
        if not self.viewport.collidepoint(xy):
            return None
        return ((xy[0]-self.viewport.x)*W/self.viewport.width,(xy[1]-self.viewport.y)*H/self.viewport.height)

    def _demo_frame(self,now,dt,keys,controls):
        specs=[dict(raise_hand=keys[pygame.K_h],running=keys[pygame.K_SPACE],crouch=keys[pygame.K_c],
                    lean=float(keys[pygame.K_RIGHT])-float(keys[pygame.K_LEFT]),lost=keys[pygame.K_l],both_up=keys[pygame.K_u]),
               dict(raise_hand=keys[pygame.K_t],running=keys[pygame.K_LSHIFT],crouch=keys[pygame.K_s],
                    lean=float(keys[pygame.K_d])-float(keys[pygame.K_a]),lost=False,both_up=keys[pygame.K_w])]
        specs[0].update({k:v for k,v in controls.items() if k!="p2"})
        specs[1].update(controls.get("p2",{}))
        if self.scene=="game" and self.selected_game=="lightning" and self.dual_active and "cursor" not in controls.get("p2",{}):
            delta=np.array([float(keys[pygame.K_d])-float(keys[pygame.K_a]),float(keys[pygame.K_s])-float(keys[pygame.K_w])])
            self.demo_hands[1]=np.clip(self.demo_hands[1]+delta*dt*.7,.02,.98)
            specs[1]["cursor"]=self.demo_hands[1]*[W,H]
        if self.scene=="game" and self.selected_game=="lightning" and self.input_mode=="mouse" and "cursor" not in controls:
            logical=self._mouse_position(pygame.mouse.get_pos())
            if logical:
                area=self.screens.hand_area(0)
                specs[0]["cursor"]=((logical[0]-area.x)/area.width*W,(logical[1]-area.y)/area.height*H)
        frames=[self.sims[i].sample(now,dt,**specs[i]) for i in range(2 if self.dual_active else 1)]
        if not self.dual_active:
            return frames[0]
        poses=[]
        for i,frame in enumerate(frames):
            if frame.landmarks is not None:
                p=frame.landmarks.copy()
                p[:,0]=(p[:,0]-.5)*.75+(.25 if i==0 else .75)
                p[:,1]=(p[:,1]-.5)*.75+.5
                poses.append(p)
        return TrackingFrame(now,people=len(poses),status="Two simulated players",poses=poses)

    def _save_results(self):
        if self.record_saved:
            return
        self.record_saved=True
        value=self.game.elapsed if self.game.metric=="time" else self.game.score
        self.personal_best=(self.game.won if self.game.metric=="time" else value>0) and (self.previous_best is None or
                            (value<self.previous_best if self.game.metric=="time" else value>self.previous_best))
        try:
            for i in range(self.match.human_count):
                ident=self.storage.save(self.match.names[i],self.mode,self.match.games[i],self.session_mode,self.challenge_seed)
                if i==0:
                    self.result_id=ident
        except (OSError,sqlite3.Error) as exc:
            self.last_error=f"Result could not be saved: {exc}"
        if self.session_mode=="party":
            self.party_results.append((self.current_name,self.game))

    def step(self,dt,now,events=None,controls=None):
        controls=controls or {}
        clicked=keyboard_activate=False
        for event in pygame.event.get() if events is None else events:
            if event.type==pygame.QUIT:
                self.running=False
            elif event.type==pygame.MOUSEMOTION and sum(abs(v) for v in event.rel)>2 and (self.demo or self.input_mode=="mouse"):
                self.input_mode="mouse"
                self.cursor_pos=self._mouse_position(event.pos)
            elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                self.input_mode="mouse"
                self.cursor_pos=self._mouse_position(event.pos)
                clicked=True
            elif event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE:
                    self.go_back(now)
                elif event.key==pygame.K_p and self.scene=="game":
                    self.go_back(now)
                elif event.key==pygame.K_F1:
                    self.diagnostics=not self.diagnostics
                elif event.key==pygame.K_F2:
                    self.set_demo(now)
                elif event.key==pygame.K_F3:
                    self.input_mode="hand"
                    self.gesture.reset(now)
                elif event.key==pygame.K_F11:
                    self.fullscreen=not self.fullscreen
                    self.window=pygame.display.set_mode((0,0) if self.fullscreen else (1152,720),pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE)
                elif event.key in (pygame.K_TAB,pygame.K_DOWN,pygame.K_UP,pygame.K_LEFT,pygame.K_RIGHT) and self.scene!="game":
                    self.input_mode="keyboard"
                    delta=-1 if event.key in (pygame.K_UP,pygame.K_LEFT) else 1
                    if self.scene=="select" and event.key in (pygame.K_UP,pygame.K_DOWN):
                        delta*=3
                    self.focus=0 if self.focus<0 else self.focus+delta
                elif event.key in (pygame.K_RETURN,pygame.K_KP_ENTER):
                    self.input_mode="keyboard"
                    keyboard_activate=True
        keys=pygame.key.get_pressed()
        if self.demo:
            self.source_frame=self._demo_frame(now,dt,keys,controls)
        elif self.tracker:
            self.tracker.track_hands=self.scene!="game"
            self.source_frame=self.tracker.latest()
        registered_before=[p.registered for p in self.bank.players]
        actions=self.bank.update(self.source_frame,now,self.dual_active)
        if any(p.registered and not registered_before[i] for i,p in enumerate(self.bank.players)):
            # Rejoining always gives body control back. Neither mouse movement
            # during setup nor a disconnected previous owner can strand the UI.
            if not self.demo:
                self.input_mode="hand"
            if self.menu_controller is None or any(p.registered and not registered_before[i] and i==self.menu_controller for i,p in enumerate(self.bank.players)):
                self.gesture.reset_owner(now)
            for i,p in enumerate(self.bank.players):
                if p.registered and not registered_before[i]:
                    self.bank.movement[i].reset()
        self.frame=self.bank.frames[0]
        if self.scene in ("welcome","handoff") and self.player.registered and self.player.valid:
            self.audio.play("join")
            self.change_scene("connected",now)
        elif self.scene=="lobby" and all(p.registered and p.valid for p in self.bank.players):
            self.audio.play("join")
            self.change_scene("briefing",now)
        elif self.scene=="connected" and now-self.scene_started>1.:
            self.change_scene(self.after_join,now)
        if self.scene=="game" and self.match:
            validity=[p.valid and p.registered for p in self.bank.players[:self.match.human_count]]
            for i,event in self.match.update(now,actions,validity):
                if i>=self.match.human_count:
                    continue
                if i>0 and event["event"] in ("phase_green","phase_red","beat_cue"):
                    continue
                if event["event"]=="red_violation" and self.game.endless:
                    continue  # the accompanying shield miss already plays this cue
                cue={"phase_green":"green","phase_red":"red","red_violation":"error","score":"select",
                     "miss":"error","beat_cue":"tick","win":"win","lose":"lose","checkpoint":"win","level_up":"tick","shield_restored":"join"}.get(event["event"])
                if cue:
                    self.audio.play(cue,(-.5 if i==0 else .5) if self.match.human_count==2 else 0.)
            if self.match.finished:
                self._save_results()
                if self.match_finished_at is None:
                    self.match_finished_at=now
                if now-self.match_finished_at>=1.8:
                    self.change_scene("results",now)
        self.buttons=self.screens.buttons()
        available=[b for b in self.buttons if b.enabled]
        controller=next((i for i in range(2 if self.dual_active else 1) if self.bank.players[i].valid and self.bank.players[i].registered),None)
        if controller!=self.menu_controller:
            self.menu_controller=controller
            self.gesture.reset_owner(now)
            if controller is not None and not self.demo:
                self.input_mode="hand"
        # An intentional raised hand also recovers body navigation after an
        # explicit mouse click. Casual mouse drift never disables hand input.
        if not self.demo and controller is not None and self.input_mode!="hand" and (self.scene!="game" or self.match.paused):
            if actions[controller].raised:
                self.hand_return_started=now if self.hand_return_started is None else self.hand_return_started
                if now-self.hand_return_started>=.65:
                    self.input_mode="hand"
                    self.gesture.reset_owner(now)
            else:
                self.hand_return_started=None
        else:
            self.hand_return_started=None
        if self.input_mode=="hand":
            self.cursor_pos=self.gesture.hand_position(self.bank.frames[controller],self.bank.players[controller].smoothed,dt) if controller is not None else None
        elif self.input_mode=="keyboard" and available:
            if self.focus<0:
                self.focus=0
            self.focus%=len(available)
            self.cursor_pos=available[self.focus].rect.center
        self.hovered=next((b.key for b in self.buttons if b.enabled and self.cursor_pos is not None and b.rect.collidepoint(self.cursor_pos)),None)
        gesture_buttons=self.buttons
        if self.scene=="game" and not self.match.paused:
            gesture_buttons=[b for b in self.buttons if b.key=="back" and not self.match.finished]
        action=self.gesture.update(self.cursor_pos,gesture_buttons,now,enabled=self.input_mode=="hand" and controller is not None)
        if (clicked or keyboard_activate) and self.hovered:
            action=self.hovered
        elif keyboard_activate and self.scene in ("welcome","handoff","lobby") and self.demo:
            action="join_demo"
        if action:
            self.activate(action,now)
            self.buttons=self.screens.buttons()
        self.fps+=(1-math.exp(-dt/.5))*(1/max(dt,.001)-self.fps)
        self.audio.update(self.scene,self.selected_game)

    def render(self,now):
        dt=1/60 if self.last_render is None else max(0.,now-self.last_render)
        self.last_render=now
        self.screens.draw(now)
        for button in self.buttons:
            old=self.hover_levels.get(button.key,0.)
            level=old+(1-math.exp(-dt/.085))*(float(self.hovered==button.key)-old)
            self.hover_levels[button.key]=level
            button.draw(self.canvas,level,now)
        if self.scene not in ("welcome","handoff","lobby","connected","game") and not any(p.registered and p.valid for p in self.bank.players[:2 if self.dual_active else 1]):
            self.screens.reconnect_overlay(now)
        if self.diagnostics:
            panel(self.canvas,(20,91,550,89),(5,15,26),CYAN,12)
            text(self.canvas,f"DRAW {self.fps:5.1f} FPS | INFER {self.source_frame.inference_ms:5.1f} ms",(34,100),17,CYAN,mono=True)
            text(self.canvas,f"CONF {self.frame.confidence:.2f} | RUN {self.movement.run_score:.2f} | MOTION {self.movement.motion_score:.2f}",(34,127),17,WHITE,mono=True)
            text(self.canvas,f"{self.input_mode.upper()} | {self.source_frame.people} BODIES | {self.session_mode.upper()}",(34,153),16,MUTED,mono=True)
        if self.last_error:
            panel(self.canvas,(40,814,1360,30),(68,26,37),RED,8)
            text(self.canvas,self.last_error[:145],(52,819),15,WHITE)
        if self.transition_from is not None:
            alpha=round(255*max(0.,1-(now-self.transition_start)/.22))
            if alpha:
                self.transition_from.set_alpha(alpha)
                self.canvas.blit(self.transition_from,(0,0))
            else:
                self.transition_from=None
        near_pause=self.cursor_pos is not None and any(b.key=="back" and b.rect.inflate(160,90).collidepoint(self.cursor_pos) for b in self.buttons)
        if self.scene!="game" or not self.match or self.match.paused or (self.input_mode=="hand" and near_pause):
            cursor(self.canvas,self.cursor_pos,self.gesture.progress,ORANGE if self.input_mode!="hand" else CYAN)
        ww,wh=self.window.get_size()
        ratio=min(ww/W,wh/H)
        target=(max(1,round(W*ratio)),max(1,round(H*ratio)))
        self.viewport=pygame.Rect((ww-target[0])//2,(wh-target[1])//2,*target)
        self.window.fill(BG)
        if target==(W,H):
            self.window.blit(self.canvas,self.viewport)
        else:
            if self.scaled_window is None or self.scaled_window.get_size()!=target:
                self.scaled_window=pygame.Surface(target)
            pygame.transform.smoothscale(self.canvas,target,self.scaled_window)
            self.window.blit(self.scaled_window,self.viewport)
        pygame.display.flip()

    def run(self,max_frames=0,screenshot=None):
        last=time.perf_counter()
        count=0
        while self.running:
            now=time.perf_counter()
            self.step(max(.0001,now-last),now)
            last=now
            self.render(now)
            count+=1
            if max_frames and count>=max_frames:
                break
            self.clock.tick(self.config.target_fps)
        if screenshot:
            path=Path(screenshot)
            path.parent.mkdir(parents=True,exist_ok=True)
            pygame.image.save(self.canvas,str(path))

    def close(self):
        if self._closed:
            return
        self._closed=True
        if self.tracker:
            self.tracker.close()
        if self.camera:
            self.camera.close()
        self.storage.close()
        pygame.mouse.set_visible(True)
        pygame.quit()
