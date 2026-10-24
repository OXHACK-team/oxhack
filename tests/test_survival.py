"""Regression coverage for survival, body-only recovery and stable player spawns."""
import os
import random
import tempfile
import time
import unittest
from pathlib import Path
import numpy as np
from avatar import Avatar
from config import Config
from games import GAMES
from match import Match,update_game
from motion_input import MotionInput
from player_bank import PlayerBank
from simulated_input import SimulatedInput
from storage import Storage
from tests.test_games import ideal
from tracking_types import TrackingFrame,LH,RH,LS,RS,RW


class SurvivalTests(unittest.TestCase):
    def game(self,key):
        return GAMES[key]["factory"](Config(),0,random.Random(17))

    def test_all_six_continue_past_old_deadlines_with_good_play(self):
        for key in GAMES:
            with self.subTest(game=key):
                g=self.game(key)
                for i in range(1,60*183+1):
                    update_game(g,i/60,ideal(g),True)
                self.assertFalse(g.finished)
                self.assertEqual(g.metric,"score")
                self.assertAlmostEqual(g.elapsed,180,places=5)
                self.assertGreater(g.score,0)
                self.assertEqual(g.level,8)
                if key in ("sprint","red_green"):
                    self.assertGreater(g.laps,3)
                if key=="echo":
                    self.assertGreater(g.round,3)
                    self.assertLessEqual(len(g.sequence),6)

    def test_all_six_end_when_idle_and_save_one_final_outcome(self):
        for key in GAMES:
            with self.subTest(game=key):
                g=self.game(key)
                for i in range(1,60*200):
                    update_game(g,i/60,MotionInput(),True)
                    if g.finished:
                        break
                self.assertTrue(g.finished)
                self.assertFalse(g.won)
                self.assertEqual(g.lives,0)
                self.assertEqual(sum(e["event"]=="lose" for e in g.events),1)

    def test_speed_floors_and_reaction_windows_stay_playable(self):
        for key in GAMES:
            with self.subTest(game=key):
                g=self.game(key)
                g.elapsed=3600
                if key=="lightning":
                    g.spawn()
                    self.assertGreaterEqual(g.target_lifetime,1.4)
                elif key=="dodge":
                    g.spawn()
                    self.assertGreaterEqual(g.travel_seconds,1.6)
                elif key=="echo":
                    g.round=500
                    g.new_sequence()
                    self.assertEqual(len(g.sequence),6)
                    self.assertGreaterEqual(g.show_seconds,.8)
                    self.assertGreaterEqual(g.repeat_seconds,12.)
                elif key=="timekeeper":
                    g.beat_age=g.period-.001
                    g.advance(.01,MotionInput())
                    self.assertGreaterEqual(g.period,1.8)
                    self.assertGreaterEqual(g.window,.20)

    def test_lag_does_not_resolve_unseen_obstacles_or_damage(self):
        g=self.game("dodge")
        g.countdown=0
        update_game(g,8,MotionInput(),True)
        self.assertAlmostEqual(g.elapsed,.1)
        self.assertEqual(g.lives,5)

    def test_chain_restores_one_shield_but_never_exceeds_capacity(self):
        g=self.game("lightning")
        g.miss()
        for _ in range(24):
            g.award(100)
        self.assertEqual(g.lives,g.max_lives)
        self.assertEqual(sum(e["event"]=="shield_restored" for e in g.events),1)

    def test_red_motion_costs_at_most_one_shield_per_light(self):
        g=self.game("red_green")
        g.countdown=0
        g.phase="RED"
        g.phase_duration=4.
        for i in range(1,60*3):
            update_game(g,i/60,MotionInput(motion=5.),True)
        self.assertEqual(g.lives,2)
        self.assertEqual(g.violations,1)

    def test_survival_records_never_mix_with_timed_challenges(self):
        with tempfile.TemporaryDirectory() as folder:
            s=Storage(Path(folder)/"records.sqlite3")
            try:
                g=self.game("lightning")
                g.award(250)
                g.finish(False)
                s.save("P1","demo",g)
                self.assertIsNone(s.best_score("P1","demo","lightning"))
                self.assertEqual(s.best_score("P1","demo","lightning","solo","endless"),250)
                self.assertEqual(len(s.leaderboard("demo",5,"lightning","solo","score","endless")),1)
            finally:
                s.close()

    def test_reconnection_has_countdown_and_preserves_the_same_games(self):
        m=Match(Config(),"dodge","duo",0)
        m.update(3,[MotionInput(),MotionInput()],[True,True])
        m.update(3.05,[MotionInput(),MotionInput()],[True,True])
        original=list(m.games)
        before=[(g.elapsed,g.score,g.lives) for g in m.games]
        m.update(4,[MotionInput(),MotionInput()],[True,False])
        m.update(15,[MotionInput(),MotionInput()],[True,False])
        m.update(16,[MotionInput(),MotionInput()],[True,True])
        self.assertEqual(m.recovery_countdown,2.)
        self.assertEqual(before,[(g.elapsed,g.score,g.lives) for g in m.games])
        for i in range(1,125):
            m.update(16+i/60,[ideal(g) for g in m.games],[True,True])
        self.assertFalse(m.paused)
        self.assertEqual(original,m.games)
        self.assertGreater(m.games[0].elapsed,before[0][0])

    def test_ai_cannot_keep_eliminated_human_waiting_forever(self):
        m=Match(Config(),"sprint","ai",0)
        m.games[0].finish(False)
        m.update(4,[MotionInput()],[False])
        self.assertTrue(m.finished)


def source(t,sims,specs,centers=(.25,.75)):
    poses=[]
    for i,spec in enumerate(specs):
        if spec is None:
            continue
        p=sims[i].sample(t,1/30,**spec).landmarks.copy()
        p[:,0]=(p[:,0]-.5)*.75+centers[i]
        p[:,1]=(p[:,1]-.5)*.75+.5
        poses.append(p)
    return TrackingFrame(t,people=len(poses),poses=poses)


class PlayerRecoveryTests(unittest.TestCase):
    def test_reaching_across_divider_does_not_disconnect_hip_lane(self):
        bank=PlayerBank(Config())
        sims=[SimulatedInput(),SimulatedInput()]
        f=source(1,sims,[{},{}])
        f.poses[0][RW,0]=.57  # hand over the divider; hips remain on the left
        bank.update(f,1,True)
        self.assertTrue(bank.players[0].valid)
        f.poses[0][RW,0]=1.1  # actual camera edge must still be respected
        bank.update(f,1,True)
        self.assertFalse(bank.players[0].valid)

    def test_partner_entering_does_not_steal_existing_solo_controls(self):
        sims=[SimulatedInput(),SimulatedInput()]
        bank=PlayerBank(Config())
        f=sims[0].sample(1,1/30)
        bank.update(f,1)
        bank.players[0].registered=True
        new=source(1.03,sims,[{},{}],centers=(.5,.82))
        new.poses.reverse()
        bank.update(new,1.03)
        self.assertTrue(bank.players[0].registered and bank.players[0].valid)
        self.assertAlmostEqual(float(np.mean(bank.frames[0].landmarks[[LH,RH],0])),.5)

    def test_off_centre_arrivals_render_at_the_same_spawn_before_calibration(self):
        class Rig:
            def draw(self,s,p,*args):
                self.pose=p.copy()
        avatar=Avatar.__new__(Avatar)
        avatar.rig=Rig()
        sims=[SimulatedInput(),SimulatedInput()]
        for center in (.18,.4,.62,.83):
            p=source(1,sims,[{},None],centers=(center,.75)).poses[0]
            avatar.draw(None,p,334,250,244,2/3)
            normalized=avatar.rig.pose
            np.testing.assert_allclose(np.mean(normalized[[LH,RH],:2],axis=0),[.5,.55],atol=1e-8)
            self.assertAlmostEqual(float(np.mean(normalized[[LH,RH],1])-np.mean(normalized[[LS,RS],1])),.26)


class BodyOnlyAppTests(unittest.TestCase):
    def setUp(self):
        os.environ["SDL_VIDEODRIVER"]="dummy"
        os.environ["SDL_AUDIODRIVER"]="dummy"
        from game_manager import App
        self.temp=tempfile.TemporaryDirectory()
        self.app=App(Config(sound=False),windowed=True,no_camera=True,data_path=Path(self.temp.name)/"records.sqlite3",settings_path=Path(self.temp.name)/"settings.json")
        self.sims=[SimulatedInput(),SimulatedInput()]
        self.now=time.perf_counter()

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def tick(self,seconds,specs):
        for _ in range(round(seconds*30)):
            self.now+=1/30
            self.app.source_frame=source(self.now,self.sims,specs)
            self.app.step(1/30,self.now,events=[])

    def join_duo(self):
        self.app.choose_mode("duo",self.now)
        self.tick(1.3,[{},None])
        self.tick(1.35,[{"raise_hand":True},None])
        self.assertTrue(self.app.bank.players[0].registered)
        self.tick(6,[{},None])
        self.assertEqual(self.app.scene,"lobby")
        self.tick(1.3,[{},{}])
        self.tick(1.35,[{},{"raise_hand":True}])
        self.assertEqual(self.app.scene,"briefing")

    def test_late_partner_joins_and_selects_start_without_mouse(self):
        self.join_duo()
        self.tick(.8,[{},{}])
        button=next(b for b in self.app.screens.buttons() if b.key=="start")
        self.tick(.3,[{"cursor":(720,200)},{}])
        self.tick(1.7,[{"cursor":button.rect.center},{}])
        self.assertEqual(self.app.scene,"game")
        self.assertEqual(self.app.input_mode,"hand")

    def test_lost_player_rejoins_same_run_then_player2_can_navigate(self):
        self.join_duo()
        self.app.selected_game="dodge"
        self.app.start_match(self.now)
        self.tick(3.3,[{},{}])
        match=self.app.match
        before=[(g.elapsed,g.score,g.lives) for g in match.games]
        self.tick(5,[{},None])
        self.assertTrue(match.paused)
        self.assertTrue(self.app.bank.players[1].needs_rejoin)
        self.app.input_mode="mouse"  # someone touched the laptop while P2 was away
        self.tick(1.3,[{},{}])
        self.tick(1.35,[{},{"raise_hand":True}])
        self.assertTrue(self.app.bank.players[1].registered)
        self.assertEqual(self.app.input_mode,"hand")
        self.assertIs(self.app.match,match)
        self.assertEqual(before,[(g.elapsed,g.score,g.lives) for g in match.games])
        self.tick(2.2,[{},{}])
        self.assertFalse(match.paused)
        self.assertGreater(match.games[0].elapsed,before[0][0])
        self.app.go_back(self.now)
        self.tick(.2,[None,{}])
        button=next(b for b in self.app.screens.buttons() if b.key=="end_run")
        self.tick(.3,[None,{"cursor":(720,200)}])
        self.tick(1.7,[None,{"cursor":button.rect.center}])
        self.assertEqual(self.app.menu_controller,1)
        self.assertEqual(self.app.scene,"results")
        self.assertEqual(self.app.storage.connection.execute("SELECT COUNT(*) FROM results").fetchone()[0],2)

    def test_mouse_drift_does_not_disable_body_navigation(self):
        import pygame
        self.join_duo()
        self.app.step(1/30,self.now,events=[pygame.event.Event(pygame.MOUSEMOTION,pos=(20,20),rel=(12,4),buttons=(0,0,0))])
        self.assertEqual(self.app.input_mode,"hand")

    def test_body_can_pause_and_resume_a_running_game(self):
        self.join_duo()
        self.app.selected_game="sprint"
        self.app.start_match(self.now)
        self.tick(3.2,[{},{}])
        button=next(b for b in self.app.screens.buttons() if b.key=="back")
        self.tick(.3,[{"cursor":(720,200)},{}])
        self.tick(1.7,[{"cursor":button.rect.center},{}])
        self.assertTrue(self.app.match.manual_pause)
        button=next(b for b in self.app.screens.buttons() if b.key=="resume")
        self.tick(.3,[{"cursor":(720,200)},{}])
        self.tick(1.7,[{"cursor":button.rect.center},{}])
        self.assertFalse(self.app.match.manual_pause)
        self.tick(2.2,[{},{}])
        self.assertFalse(self.app.match.paused)

    def test_elimination_announces_result_before_changing_screens(self):
        self.join_duo()
        self.app.start_match(self.now)
        self.app.match.games[0].finish(False)
        self.app.match.games[1].finish(False)
        self.tick(.2,[{},{}])
        self.assertEqual(self.app.scene,"game")
        self.tick(1.8,[{},{}])
        self.assertEqual(self.app.scene,"results")
        self.assertEqual(self.app.storage.connection.execute("SELECT COUNT(*) FROM results").fetchone()[0],2)


if __name__=="__main__":
    unittest.main()
