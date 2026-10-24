"""Original synthesized cues, generated once. Audio device failure is nonfatal."""
import numpy as np
import pygame


class Audio:
    def __init__(self, config):
        self.config = config
        self.sounds = {}
        self.ambience=None
        self.music_channel=None
        self.music_playing=False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            for name, notes in {"select":[660,880], "join":[440,660,880], "green":[523,784],
                                "red":[392,262], "error":[170,130], "win":[523,659,784,1047],
                                "lose":[330,262,196], "tick":[880]}.items():
                pieces = []
                for frequency in notes:
                    t = np.arange(int(44100 * .1)) / 44100
                    envelope = np.minimum(1., t / .008) * np.exp(-t * 24)
                    pieces.append(np.sin(2 * np.pi * frequency * t) * envelope * .2)
                mono = (np.concatenate(pieces) * 32767).astype(np.int16)
                self.sounds[name] = pygame.sndarray.make_sound(np.ascontiguousarray(np.column_stack((mono, mono))))
            pygame.mixer.set_num_channels(12)
            pygame.mixer.set_reserved(1)
            self.music_channel=pygame.mixer.Channel(0)
            pieces=[]
            for notes in ((130.81,155.56,196.),(103.83,130.81,155.56),(116.54,146.83,174.61),(98.,123.47,146.83)):
                t=np.arange(88200)/44100
                envelope=np.minimum(1.,t/.18)*np.minimum(1.,(2.-t)/.18)
                chord=sum(np.sin(2*np.pi*f*t)+.2*np.sin(2*np.pi*f*2*t) for f in notes)*.008
                pulse=t%.5
                kick=np.sin(2*np.pi*65*pulse)*np.exp(-pulse*28)*.025
                pieces.append(chord*envelope+kick)
            mono=(np.concatenate(pieces)*32767).astype(np.int16)
            self.ambience=pygame.sndarray.make_sound(np.ascontiguousarray(np.column_stack((mono,mono))))
        except pygame.error:
            self.sounds.clear()

    def update(self,scene,game_id=None):
        desired=self.config.sound and not (scene=="game" and game_id=="timekeeper")
        if desired and not self.music_playing and self.ambience is not None:
            self.music_channel.play(self.ambience,loops=-1,fade_ms=500)
            self.music_playing=True
        elif not desired and self.music_playing:
            self.music_channel.fadeout(250)
            self.music_playing=False

    def play(self, name,pan=0.):
        if self.config.sound and name in self.sounds:
            channel=self.sounds[name].play()
            if channel:
                channel.set_volume(min(1.,1-pan*.5),min(1.,1+pan*.5))
