"""Feedback must stay bounded, respect accessibility and never alter game rules."""
import os
import random
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import pygame
from audio import Audio,_pcm
from config import Config
from games.lightning_strike import LightningStrike
from ui.effects import Effects


class FeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"]="dummy"
        os.environ["SDL_AUDIODRIVER"]="dummy"
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.config=Config()
        self.game=LightningStrike(self.config,0,random.Random(9))
        self.rect=pygame.Rect(40,190,668,574)

    def test_visual_feedback_never_consumes_game_randomness_or_changes_score(self):
        fx=Effects(self.config)
        before=(self.game.rng.getstate(),self.game.score,list(self.game.events),self.game.target)
        fx.emit(0,{"event":"score","points":150,"target":self.game.target},self.game,1,self.rect)
        fx.update(.1)
        fx.draw(pygame.Surface((1440,900)),1.1)
        self.assertEqual(before,(self.game.rng.getstate(),self.game.score,self.game.events,self.game.target))

    def test_bursts_are_bounded_under_sustained_scoring_and_expire(self):
        fx=Effects(self.config)
        for _ in range(500):
            fx.emit(0,{"event":"score","points":150},self.game,1,self.rect)
            fx.emit(1,{"event":"checkpoint"},self.game,1,pygame.Rect(732,190,668,574))
        self.assertLessEqual(len(fx.particles),240)
        self.assertLessEqual(len(fx.waves),24)
        self.assertLessEqual(len(fx.captions),12)
        fx.update(10)
        self.assertEqual(fx.active_count,0)

    def test_particle_seed_is_reproducible_and_effects_leave_hud_untouched(self):
        one,two=Effects(self.config,7),Effects(self.config,7)
        for fx in (one,two):
            fx.emit(0,{"event":"time_power"},self.game,1,self.rect)
            fx.update(.1)
        self.assertEqual(list(one.particles),list(two.particles))
        surface=pygame.Surface((1440,900))
        surface.fill((12,24,36))
        before=pygame.surfarray.array3d(surface)
        one.draw(surface,1.1)
        after=pygame.surfarray.array3d(surface)
        np.testing.assert_array_equal(before[:,:302],after[:,:302])
        np.testing.assert_array_equal(before[710:,:],after[710:,:])
        self.assertTrue(np.any(before!=after))

    def test_reduced_motion_uses_static_cues_without_particles_or_flashes(self):
        config=SimpleNamespace(reduced_motion=True)
        fx=Effects(config)
        fx.emit(0,{"event":"time_power"},self.game,1,self.rect)
        fx.emit(0,{"event":"miss"},self.game,1,self.rect)
        self.assertEqual(len(fx.particles),0)
        self.assertFalse(fx.flashes)
        radii=[p.radius for p in fx.waves]
        y=[p.y for p in fx.captions]
        fx.update(.1)
        self.assertEqual(radii,[p.radius for p in fx.waves])
        self.assertEqual(y,[p.y for p in fx.captions])

    def test_new_game_in_same_slot_discards_previous_match_feedback(self):
        fx=Effects(self.config)
        fx.emit(0,{"event":"time_power"},self.game,1,self.rect)
        self.assertGreater(fx.active_count,0)
        replacement=LightningStrike(self.config,2,random.Random(2))
        fx.emit(0,{"event":"target_spawn","target":(.25,.3)},replacement,2,self.rect)
        self.assertEqual(fx.active_count,0)
        self.assertEqual(fx.anchors[0],(.25,.3))

    def test_audio_pcm_has_distinct_non_clipping_cues(self):
        sounds=_pcm(44100)
        expected={"score","hit","checkpoint","level_up","countdown","shield","time_power","time_block","time_power_ready"}
        self.assertTrue(expected.issubset(sounds))
        for name in expected:
            self.assertGreater(np.max(np.abs(sounds[name].astype(np.int32))),100)
            self.assertLess(np.max(np.abs(sounds[name].astype(np.int32))),32767)
        self.assertFalse(np.array_equal(sounds["score"],sounds["hit"]))
        self.assertEqual(int(sounds["ambience"][0]),0)
        self.assertEqual(int(sounds["ambience"][-1]),0)

    def test_audio_device_failure_and_shutdown_are_nonfatal(self):
        with patch("audio.pygame.mixer.get_init",return_value=None),patch("audio.pygame.mixer.init",side_effect=pygame.error("No device")):
            sound=Audio(self.config)
            sound.update("game","sprint")
            sound.play("time_power")
        self.assertFalse(sound.sounds)

    def test_rhythm_game_music_silences_and_other_scenes_restore_it(self):
        sound=Audio(self.config)
        self.assertIn("time_power",sound.sounds)
        sound.update("menu")
        self.assertTrue(sound.music_playing)
        sound.update("game","timekeeper")
        self.assertFalse(sound.music_playing)
        sound.update("game","dodge")
        self.assertTrue(sound.music_playing)


if __name__=="__main__":
    unittest.main()
