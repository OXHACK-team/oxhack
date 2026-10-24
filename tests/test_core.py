import json
import math
from pathlib import Path
import random
import tempfile
import unittest
import numpy as np
from config import Config
from games.red_light_green_light import RedLightGreenLight
from gesture_controller import GestureController
from movement import MovementDetector
from player_manager import PlayerManager
from simulated_input import SimulatedInput
from storage import Storage
from tracking_types import *


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.cfg=Config()
        self.player=PlayerManager(self.cfg)
        self.sim=SimulatedInput()
        self.now=0.

    def feed(self, seconds, **kwargs):
        for _ in range(math.ceil(seconds*30)):
            self.now+=1/30
            self.player.update(self.sim.sample(self.now,1/30,**kwargs),self.now)

    def join(self):
        self.feed(1.2)
        self.feed(1.3,raise_hand=True)

    def test_requires_neutral_calibration_then_hold(self):
        self.feed(1.4,raise_hand=True)
        self.assertIsNone(self.player.neutral)
        self.feed(1.2)
        self.assertIsNotNone(self.player.neutral)
        self.feed(.7,raise_hand=True)
        self.assertFalse(self.player.registered)
        self.feed(.7,raise_hand=True)
        self.assertTrue(self.player.registered)

    def test_interrupted_hold_resets(self):
        self.feed(1.2)
        self.feed(.8,raise_hand=True)
        self.feed(.1)
        self.feed(.8,raise_hand=True)
        self.assertFalse(self.player.registered)

    def test_poor_confidence_and_clipped_feet_rejected(self):
        frame=self.sim.sample(1,1/30)
        frame.landmarks[LA,3]=.2
        self.player.update(frame,1)
        self.assertFalse(self.player.valid)
        frame.landmarks[LA,3]=.99
        frame.landmarks[LA,1]=1.05
        self.player.update(frame,1)
        self.assertFalse(self.player.valid)

    def test_stale_and_multiple_people_rejected(self):
        frame=self.sim.sample(1,1/30)
        self.player.update(frame,2)
        self.assertFalse(self.player.valid)
        frame.people=2
        self.player.update(frame,1)
        self.assertFalse(self.player.valid)

    def test_rejoin_required_after_long_gap(self):
        self.join()
        self.feed(3.2,lost=True)
        self.assertTrue(self.player.needs_rejoin)
        self.feed(.5)
        self.assertFalse(self.player.valid)

    def test_unexpected_player_jump_rejected(self):
        self.join()
        frame=self.sim.sample(self.now+.03,.03)
        frame.landmarks[:,0]+=.4
        self.player.update(frame,self.now+.03)
        self.assertFalse(self.player.valid)

    def test_short_gap_can_recover(self):
        self.join()
        self.feed(.3,lost=True)
        self.feed(.1)
        self.assertTrue(self.player.valid)


class MovementTests(unittest.TestCase):
    def measure(self, generator, scale=.26):
        d=MovementDetector(Config())
        scores=[]
        for i in range(180):
            t=i/30
            p=generator(t)
            scores.append(d.update(p,t,scale))
        return np.array(scores)

    def test_stationary_and_camera_jitter_not_running(self):
        rng=np.random.default_rng(5)
        def jitter(t):
            p=neutral_pose()
            p[:,:2]+=rng.normal(0,.0005,(33,2))
            return p
        scores=self.measure(jitter)
        self.assertLess(float(scores[:,0].max()),.01)
        self.assertLess(float(np.mean(scores[:,1])),.3)

    def test_single_hand_shaking_cannot_advance(self):
        def hand(t):
            p=neutral_pose()
            p[LW,1]+=.12*math.sin(t*14)
            return p
        scores=self.measure(hand)
        self.assertEqual(float(scores[:,0].max()),0.)
        self.assertGreater(float(scores[:,1].max()),.65)

    def test_alternating_jog_advances(self):
        sim=SimulatedInput()
        scores=self.measure(lambda t:sim.sample(t,1/30,running=True).landmarks)
        self.assertGreater(float(scores[-90:,0].mean()),.45)

    def test_distance_normalization(self):
        sim1,sim2=SimulatedInput(),SimulatedInput()
        first=self.measure(lambda t:sim1.sample(t,1/30,running=True).landmarks)
        def far(t):
            p=sim2.sample(t,1/30,running=True).landmarks
            p[:,:2]=(p[:,:2]-.5)*.6+.5
            return p
        second=self.measure(far,.26*.6)
        np.testing.assert_allclose(first,second,atol=1e-10)

    def test_duplicate_frames_do_not_create_motion(self):
        d=MovementDetector(Config())
        p=neutral_pose()
        d.update(p,1,.26)
        p[LW,1]-=.2
        self.assertEqual(d.update(p,1,.26),(0.,0.))


class DwellTests(unittest.TestCase):
    def setUp(self):
        import pygame
        from ui.components import Button
        self.g=GestureController(Config())
        self.buttons=[Button("one",pygame.Rect(0,0,100,100),"ONE"),Button("two",pygame.Rect(150,0,100,100),"TWO",enabled=False)]

    def test_dwell_select_once_then_requires_release(self):
        self.assertIsNone(self.g.update((50,50),self.buttons,0))
        self.assertEqual(self.g.update((50,50),self.buttons,1.1),"one")
        self.assertIsNone(self.g.update((50,50),self.buttons,4))
        self.g.update((120,50),self.buttons,4.1)
        self.g.update((50,50),self.buttons,4.2)
        self.assertEqual(self.g.update((50,50),self.buttons,5.3),"one")

    def test_disabled_and_invalid_tracking_never_select(self):
        self.g.update((180,50),self.buttons,0)
        self.assertIsNone(self.g.update((180,50),self.buttons,4))
        self.g.update((50,50),self.buttons,5)
        self.g.update((50,50),self.buttons,5.9,enabled=False)
        self.assertIsNone(self.g.update((50,50),self.buttons,6.1))

    def test_new_screen_requires_a_cursor_move_before_selecting_again(self):
        self.g.position=np.array([50.,50.])
        self.g.reset(0)
        self.assertIsNone(self.g.update((50,50),self.buttons,2))
        self.g.update((90,50),self.buttons,2.1)
        self.assertEqual(self.g.update((90,50),self.buttons,3.2),"one")


class GameTests(unittest.TestCase):
    def game(self,**changes):
        cfg=Config(**changes)
        g=RedLightGreenLight(cfg,0,random.Random(5))
        g.update(3,0,0)
        return g

    def test_phase_ranges(self):
        g=self.game()
        for i in range(1,3000):
            g.update(3+i/60,0,0)
            lo,hi=g.config.green_seconds if g.phase=="GREEN" else g.config.red_seconds
            self.assertTrue(lo<=g.phase_duration<=hi)

    def test_red_grace_jitter_penalty_and_cooldown(self):
        g=self.game(green_seconds=[2.,2.],red_seconds=[4.,4.])
        g.update(5,1,0)
        self.assertEqual(g.phase,"RED")
        g.update(5.3,0,5)
        self.assertEqual(g.violations,0)
        for i in range(1,31):
            g.update(5.3+i/60,0,.1)
        self.assertEqual(g.violations,0)
        for i in range(1,31):
            g.update(5.8+i/60,0,3)
        self.assertEqual(g.violations,1)
        self.assertAlmostEqual(g.progress,.22-.07,places=5)
        for i in range(1,31):
            g.update(6.3+i/60,0,3)
        self.assertEqual(g.violations,1)

    def test_tracking_pause_stops_all_clocks(self):
        g=self.game()
        g.update(4,1,0)
        before=(g.elapsed,g.phase_elapsed,g.progress,g.remaining)
        g.update(4.01,1,20,False)
        g.update(100,1,20,False)
        self.assertEqual(before,(g.elapsed,g.phase_elapsed,g.progress,g.remaining))
        g.update(101,0,20,True)
        self.assertEqual(before,(g.elapsed,g.phase_elapsed,g.progress,g.remaining))
        g.update(101.1,0,0,True)
        self.assertAlmostEqual(g.elapsed,before[0]+.1)

    def test_long_frame_does_not_count_grace_as_motion(self):
        g=self.game(green_seconds=[2.,2.],red_seconds=[4.,4.])
        g.update(5,1,0)
        g.update(5.6,0,5)
        self.assertEqual(g.violations,0)
        g.update(5.67,0,5)
        self.assertEqual(g.violations,1)

    def test_countdown_overshoot_and_exact_finish_timestamp(self):
        g=RedLightGreenLight(Config(forward_speed=1.),0,random.Random(1))
        g.update(3.5,1,0)
        self.assertAlmostEqual(g.elapsed,.5)
        self.assertAlmostEqual(g.progress,.5)
        g.update(4.8,1,0)
        self.assertTrue(g.won)
        self.assertAlmostEqual(g.elapsed,1.)
        self.assertAlmostEqual(g.events[-1]["monotonic_offset_s"],4.)

    def test_win_and_lose(self):
        win=self.game(forward_speed=1.)
        win.update(4.1,1,0)
        self.assertTrue(win.finished and win.won)
        lose=self.game(time_limit_seconds=2.)
        lose.update(5.1,0,0)
        self.assertTrue(lose.finished and not lose.won)
        self.assertEqual(lose.remaining,0)

    def test_finished_is_idempotent_and_events_timestamped(self):
        g=self.game(time_limit_seconds=1.)
        g.update(5,0,0)
        events=list(g.events)
        g.update(20,1,10)
        self.assertEqual(events,g.events)
        times=[e["monotonic_offset_s"] for e in events]
        self.assertEqual(times,sorted(times))


class StorageAndConfigTests(unittest.TestCase):
    def test_results_best_leaderboard_and_demo_separation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"test.sqlite3"
            s=Storage(path)
            g=GameTests().game(forward_speed=1.)
            g.update(4.2,1,0)
            s.save("Player 1","demo",g)
            self.assertIsNone(s.best("Player 1","camera"))
            self.assertAlmostEqual(s.best("Player 1","demo"),1.)
            self.assertEqual(len(s.leaderboard("demo")),1)
            s.close()
            s=Storage(path)
            self.assertAlmostEqual(s.best("Player 1","demo"),1.)
            s.close()

    def test_unfinished_round_not_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            s=Storage(Path(folder)/"test.sqlite3")
            with self.assertRaises(ValueError):
                s.save("P","demo",GameTests().game())
            s.close()

    def test_config_round_trip_and_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"config.json"
            cfg=Config(sensitivity=1.4)
            cfg.save(path)
            self.assertEqual(Config.load(path).sensitivity,1.4)
            path.write_text(json.dumps({"red_seconds":[5,2]}))
            with self.assertRaises(ValueError):
                Config.load(path)


if __name__ == "__main__":
    unittest.main()
