"""Time powers, responsive filtering and earned local progression regressions."""
import random
import tempfile
import unittest
from pathlib import Path
import numpy as np
from config import Config
from games import GAMES
from match import Match,update_game
from motion_input import MotionInput,from_player
from player_manager import PlayerManager
from movement import MovementDetector
from progression import profile_for,xp_for
from simulated_input import SimulatedInput
from ai_opponent import pose_input
from storage import Storage
from tracking_types import TrackingFrame,neutral_pose,RW


class TimePowerTests(unittest.TestCase):
    def make(self,key="lightning",**changes):
        g=GAMES[key]["factory"](Config(**changes),0,random.Random(4))
        g.countdown=0.
        return g

    def cross(self,g,start=0.,seconds=.7):
        for i in range(1,round(seconds*60)+1):
            update_game(g,start+i/60,MotionInput(time_power=True),True)

    def test_every_game_accepts_power_hold_through_match_adapter(self):
        for key in GAMES:
            with self.subTest(game=key):
                g=self.make(key)
                self.cross(g)
                self.assertTrue(g.time_power_active)
                self.assertEqual(g.time_power_charges,0)
                before=(g.score,g.violations,g.lives)
                g.miss()
                self.assertEqual(before,(g.score,g.violations,g.lives))
                self.assertEqual(g.blocks,1)
                self.assertFalse(g.time_power_active)
                g.miss()
                self.assertEqual(g.lives,before[2]-1)

    def test_shield_expires_and_cannot_be_farmed_by_holding(self):
        g=self.make()
        g.time_power_charges=2
        self.cross(g,seconds=1.)
        self.assertEqual(g.time_power_charges,1)
        self.cross(g,start=1.,seconds=6.)
        self.assertFalse(g.time_power_active)
        self.assertEqual(sum(e["event"]=="time_power" for e in g.events),1)
        update_game(g,7.1,MotionInput(),True)
        self.cross(g,start=7.1)
        self.assertEqual(sum(e["event"]=="time_power" for e in g.events),2)

    def test_pause_interrupts_gesture_without_consuming_charge(self):
        g=self.make()
        self.cross(g,seconds=.4)
        update_game(g,5,MotionInput(time_power=True),False)
        update_game(g,6,MotionInput(time_power=True),True)
        self.cross(g,start=6,seconds=.4)
        self.assertFalse(g.time_power_active)
        self.assertEqual(g.time_power_charges,1)
        self.cross(g,start=6.4,seconds=.3)
        self.assertTrue(g.time_power_active)

    def test_clean_combos_charge_but_never_overflow(self):
        g=self.make()
        for _ in range(48):
            g.award(100)
        self.assertEqual(g.time_power_charges,2)
        self.assertEqual(sum(e["event"]=="time_power_ready" for e in g.events),1)

    def test_time_shield_does_not_change_opponents_clock_or_health(self):
        m=Match(Config(),"dodge","duo",0)
        for i in range(1,60*7):
            m.update(i/60,[MotionInput(time_power=True),MotionInput()],[True,True])
        self.assertAlmostEqual(m.games[0].elapsed,m.games[1].elapsed)
        self.assertGreater(m.games[0].lives,m.games[1].lives)
        self.assertEqual(m.games[1].blocks,0)

    def test_timed_challenges_keep_original_rules(self):
        g=self.make(endless=False)
        self.cross(g)
        self.assertEqual(g.time_power_charges,0)
        self.assertFalse(g.time_power_active)


class ResponsiveInputTests(unittest.TestCase):
    def test_body_power_works_after_real_calibration_in_two_player_app(self):
        from tests.test_survival import BodyOnlyAppTests
        fixture=BodyOnlyAppTests()
        fixture.setUp()
        try:
            fixture.join_duo()
            fixture.app.selected_game="dodge"
            fixture.app.start_match(fixture.now)
            fixture.tick(3.2,[{},{}])
            fixture.tick(.95,[{"time_power":True},{}])
            self.assertTrue(fixture.app.game.time_power_active)
            self.assertEqual(fixture.app.game.time_power_charges,0)
            self.assertFalse(fixture.app.match.games[1].time_power_active)
            self.assertGreater(fixture.app.effects.active_count,0)
        finally:
            fixture.tearDown()

    def test_actual_crossed_landmarks_activate_and_other_poses_do_not(self):
        sim=SimulatedInput()
        player=PlayerManager(Config())
        player.neutral=neutral_pose()
        player.valid=True
        detector=MovementDetector(Config())
        for controls in ({},{"raise_hand":True},{"both_up":True},{"lean":1},{"crouch":True},{"time_power":True}):
            player.smoothed=sim.sample(0,1/30,**controls).landmarks
            self.assertEqual(from_player(player,detector).time_power,controls.get("time_power",False))

    def test_adaptive_pose_reaches_fast_movement_before_old_filter(self):
        cfg=Config()
        p=PlayerManager(cfg)
        initial=neutral_pose()
        p.update(TrackingFrame(0,initial,people=1),0)
        moved=initial.copy()
        moved[RW,0]-=.18
        p.update(TrackingFrame(1/30,moved,people=1),1/30)
        fixed_alpha=1-np.exp(-(1/30)/cfg.pose_smoothing_seconds)
        fixed_x=initial[RW,0]+fixed_alpha*(moved[RW,0]-initial[RW,0])
        self.assertLess(abs(p.smoothed[RW,0]-moved[RW,0]),abs(fixed_x-moved[RW,0]))

    def test_stationary_noise_still_gets_filtered(self):
        p=PlayerManager(Config())
        body=neutral_pose()
        p.update(TrackingFrame(0,body,people=1),0)
        noisy=body.copy()
        noisy[RW,0]+=.0003
        p.update(TrackingFrame(1/30,noisy,people=1),1/30)
        self.assertLess(p.smoothed[RW,0]-body[RW,0],.0002)


class ProgressionTests(unittest.TestCase):
    def test_no_xp_for_idle_or_instant_banking(self):
        g=GAMES["lightning"]["factory"](Config(),0)
        g.elapsed=2
        g.score=1000
        g.finish(False)
        self.assertEqual(xp_for(g),0)
        g.elapsed=60
        g.score=0
        self.assertEqual(xp_for(g),0)

    def test_rank_boundaries_and_progress_are_real(self):
        self.assertEqual(profile_for(99)["level"],1)
        self.assertEqual(profile_for(100)["level"],2)
        self.assertEqual(profile_for(260)["level"],3)
        self.assertEqual(profile_for(260)["level_xp"],0)
        self.assertEqual(profile_for(340)["progress"],80/220)

    def test_saved_progress_survives_restart_and_separates_demo(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"progress.sqlite3"
            s=Storage(path)
            g=GAMES["lightning"]["factory"](Config(),0)
            g.elapsed=90
            g.score=10000
            g.finish(False)
            s.save("P1","camera",g)
            earned=xp_for(g)
            s.close()
            s=Storage(path)
            try:
                self.assertEqual(s.profile("P1","camera")["xp"],earned)
                self.assertEqual(s.profile("P1","camera")["runs"],1)
                self.assertEqual(s.profile("P1","demo")["xp"],0)
                self.assertEqual(s.profile("P2","camera")["xp"],0)
            finally:
                s.close()


class PauseFairnessTests(unittest.TestCase):
    def test_first_deliberate_raise_after_recovery_can_catch_the_beat(self):
        g=GAMES["timekeeper"]["factory"](Config(),0,random.Random(2))
        g.countdown=0
        g.beat_age=g.target_time-.1
        update_game(g,.01,MotionInput(),False)
        update_game(g,10,MotionInput(),True)
        update_game(g,10.1,MotionInput(left_up=True),True)
        self.assertGreater(g.score,0)

    def test_hand_already_up_at_recovery_never_manufactures_a_beat(self):
        g=GAMES["timekeeper"]["factory"](Config(),0,random.Random(2))
        g.countdown=0
        g.beat_age=g.target_time-.1
        update_game(g,.01,MotionInput(),False)
        update_game(g,10,MotionInput(left_up=True),True)
        update_game(g,10.1,MotionInput(left_up=True),True)
        self.assertEqual(g.score,0)

    def test_correct_dodge_is_not_lost_to_pause_just_before_impact(self):
        g=GAMES["dodge"]["factory"](Config(),0,random.Random(2))
        g.countdown=0
        for i in range(1,167):
            update_game(g,i/60,pose_input(g.required),True)
        lives=g.lives
        update_game(g,3,pose_input(g.required),False)
        update_game(g,13,pose_input(g.required),True)
        update_game(g,13.06,pose_input(g.required),True)
        self.assertEqual(g.lives,lives)
        self.assertGreater(g.score,0)

    def test_nearly_charged_orb_is_not_lost_to_pause_at_expiry(self):
        g=GAMES["lightning"]["factory"](Config(),0,random.Random(2))
        g.countdown=0
        for i in range(1,145):
            update_game(g,i/60,MotionInput(),True)
        for i in range(145,150):
            update_game(g,i/60,MotionInput(right_hand=g.target),True)
        self.assertEqual(g.score,0)
        update_game(g,2.5,MotionInput(),False)
        update_game(g,13,MotionInput(right_hand=g.target),True)
        update_game(g,13.05,MotionInput(right_hand=g.target),True)
        self.assertGreater(g.score,0)
        self.assertEqual(g.violations,0)

    def test_echo_hold_survives_pause_near_recall_deadline(self):
        g=GAMES["echo"]["factory"](Config(),0,random.Random(2))
        g.countdown=0
        g.stage="REPEAT"
        g.stage_age=g.repeat_seconds-.1
        g.pose_held=g.config.pose_hold_seconds-.04
        expected=g.expected
        update_game(g,.01,pose_input(expected),False)
        update_game(g,10,pose_input(expected),True)
        update_game(g,10.05,pose_input(expected),True)
        self.assertEqual(g.step_index,1)
        self.assertEqual(g.violations,0)


if __name__=="__main__":
    unittest.main()
