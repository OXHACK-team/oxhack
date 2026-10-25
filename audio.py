"""Original layered cues and a quiet clockwork sports soundtrack, made locally.

PCM is generated once per sample rate. Device failure remains nonfatal, and
Timekeeper keeps music silent so its timing cue is clear.
"""
import math
import time
import numpy as np
import pygame


_PCM_CACHE={}


def _voice(rate,frequency,duration,gain=.2,tone="bell",end=None):
    t=np.arange(round(rate*duration),dtype=np.float64)/rate
    phase=math.tau*frequency*t if end is None else math.tau*(frequency*t+(end-frequency)*t*t/(2*duration))
    envelope=np.minimum(1.,t/.004)*np.clip((duration-t)/.035,0.,1.)*np.exp(-t*(8.5 if tone=="pluck" else 5.5))
    if tone=="warm":
        wave=np.sin(phase)+.23*np.sin(phase*2)+.09*np.sin(phase*3)
    elif tone=="bass":
        wave=np.sin(phase)+.18*np.sin(phase*2)
    else:
        wave=np.sin(phase)+.19*np.sin(phase*2.76)+.055*np.sin(phase*4.18)
    return wave*envelope*gain


def _arrange(rate,duration,notes,noise=0.,seed=17):
    result=np.zeros(round(rate*duration),dtype=np.float64)
    for start,freq,length,gain,tone,*end in notes:
        sample=_voice(rate,freq,length,gain,tone,end[0] if end else None)
        begin=round(rate*start)
        count=min(len(sample),len(result)-begin)
        if count>0:
            result[begin:begin+count]+=sample[:count]
    if noise:
        rng=np.random.default_rng(seed)
        t=np.arange(len(result))/rate
        hiss=np.convolve(rng.normal(0,1,len(result)),np.ones(7)/7,mode="same")
        result+=hiss*np.minimum(1.,t/.003)*np.exp(-t*23)*noise
    return (np.tanh(result)*30000).astype(np.int16)


def _pcm(rate):
    if rate in _PCM_CACHE:
        return _PCM_CACHE[rate]
    note=lambda t,f,d=.18,g=.15,tone="bell",*end:(t,f,d,g,tone,*end)
    cues={
        "select":(.15,[note(0,660,.11,.11),note(.04,990,.11,.09)],0.),
        "score":(.22,[note(0,1047,.15,.105),note(.035,1568,.17,.075),note(0,210,.09,.055,"bass")],0.),
        "join":(.48,[note(i*.075,f,.25,.115,"warm") for i,f in enumerate((392,523,659,784))],0.),
        "green":(.30,[note(0,523,.24,.16,"warm"),note(.065,784,.22,.13)],0.),
        "red":(.31,[note(0,262,.24,.20,"warm",196),note(.04,131,.24,.13,"bass")],.04),
        "hit":(.34,[note(0,115,.32,.32,"bass",42),note(0,220,.18,.10,"warm",95)],.20),
        "tick":(.105,[note(0,880,.09,.12),note(0,1760,.045,.045)],.025),
        "countdown":(.16,[note(0,440,.14,.16,"warm"),note(0,110,.13,.075,"bass")],0.),
        "checkpoint":(.62,[note(i*.055,f,.35,.11,"warm") for i,f in enumerate((523,659,784,1047))]+[note(0,131,.45,.17,"bass")],.025),
        "level_up":(.51,[note(i*.07,f,.25,.13) for i,f in enumerate((587,784,880,1175))],0.),
        "shield":(.52,[note(i*.06,f,.28,.105) for i,f in enumerate((1047,1319,1568))]+[note(0,262,.4,.10,"warm")],0.),
        "time_power":(.72,[note(0,1700,.65,.13,"bell",240),note(.06,330,.55,.19,"warm",110),note(0,75,.6,.23,"bass",42)],.075),
        "time_block":(.39,[note(0,784,.32,.18),note(.02,1175,.3,.12),note(0,196,.23,.13,"bass")],.035),
        "time_power_ready":(.51,[note(i*.075,f,.28,.105) for i,f in enumerate((659,784,988))],0.),
        "win":(.91,[note(i*.11,f,.44,.13,"warm") for i,f in enumerate((523,659,784,1047))]+[note(.33,523,.5,.095),note(.33,659,.5,.075)],0.),
        "lose":(.73,[note(i*.12,f,.35,.14,"warm") for i,f in enumerate((330,294,220))]+[note(0,110,.6,.12,"bass")],0.),
    }
    sounds={name:_arrange(rate,*spec) for name,spec in cues.items()}
    sounds["error"]=sounds["hit"]
    beat=60/110.
    music=np.zeros(round(rate*beat*16),dtype=np.float64)
    rng=np.random.default_rng(2026)
    chords=((130.81,155.56,196.),(103.83,130.81,155.56),(116.54,146.83,174.61),(98.,123.47,146.83))
    def add(start,sample):
        begin=round(start*rate)
        count=min(len(sample),len(music)-begin)
        if count>0:
            music[begin:begin+count]+=sample[:count]
    for bar,chord in enumerate(chords):
        duration=beat*4
        t=np.arange(round(rate*duration))/rate
        pad=sum(np.sin(math.tau*f*t)+.12*np.sin(math.tau*f*2*t) for f in chord)
        envelope=np.minimum(1.,t/.2)*np.clip((duration-t)/.2,0.,1.)
        add(bar*duration,pad*envelope*.007)
        for step in range(8):
            add(bar*duration+step*beat/2,_voice(rate,chord[step%3]*2,beat*.65,.011,"pluck"))
    for step in range(16):
        at=step*beat
        add(at,_voice(rate,78,.21,.045,"bass",42))
        add(at,_voice(rate,chords[step//4][0]/2,.3,.024,"bass"))
        if step%2:
            t=np.arange(round(rate*.13))/rate
            add(at,rng.normal(0,1,len(t))*np.exp(-t*42)*.006)
        for half in (0,.5):
            t=np.arange(round(rate*.055))/rate
            add(at+half*beat,rng.normal(0,1,len(t))*np.exp(-t*90)*.0035)
    ramp=min(round(rate*.02),len(music)//2)
    music[:ramp]*=np.linspace(0,1,ramp)
    music[-ramp:]*=np.linspace(1,0,ramp)
    sounds["ambience"]=(np.tanh(music)*32767).astype(np.int16)
    _PCM_CACHE[rate]=sounds
    return sounds


class Audio:
    def __init__(self,config):
        self.config=config
        self.sounds={}
        self.ambience=None
        self.music_channel=None
        self.music_playing=False
        self._last_played={}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100,size=-16,channels=2,buffer=512)
            rate,_,channels=pygame.mixer.get_init()
            for name,mono in _pcm(rate).items():
                data=np.ascontiguousarray(np.column_stack((mono,mono))) if channels==2 else mono
                sound=pygame.sndarray.make_sound(data)
                if name=="ambience":
                    self.ambience=sound
                else:
                    self.sounds[name]=sound
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(1)
            self.music_channel=pygame.mixer.Channel(0)
        except (pygame.error,ValueError):
            self.sounds.clear()
            self.ambience=self.music_channel=None

    def update(self,scene,game_id=None):
        if self.music_channel is None or not pygame.mixer.get_init():
            self.music_playing=False
            return
        desired=self.config.sound and getattr(self.config,"music",True) and not (scene=="game" and game_id=="timekeeper")
        try:
            if desired and not self.music_playing and self.ambience is not None:
                self.music_channel.play(self.ambience,loops=-1,fade_ms=450)
                self.music_playing=True
            elif not desired and self.music_playing:
                self.music_channel.fadeout(200)
                self.music_playing=False
            self.music_channel.set_volume(.75 if scene=="game" else .52)
        except pygame.error:
            self.music_playing=False

    def play(self,name,pan=0.):
        if not self.config.sound or name not in self.sounds or not pygame.mixer.get_init():
            return
        now=time.perf_counter()
        key=(name,round(float(pan),1))
        interval=.05 if name in ("select","score","tick") else .10 if name in ("hit","error") else .035
        if now-self._last_played.get(key,-99.)<interval:
            return
        self._last_played[key]=now
        try:
            channel=self.sounds[name].play()
            if channel is None and name in ("win","lose","checkpoint","time_power","shield"):
                channel=pygame.mixer.Channel(15)
                channel.play(self.sounds[name])
            if channel:
                angle=(max(-1.,min(1.,float(pan)))+1)*math.pi/4
                channel.set_volume(math.cos(angle)*.92,math.sin(angle)*.92)
        except pygame.error:
            return
