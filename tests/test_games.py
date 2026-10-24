import random
import sqlite3
import tempfile
from pathlib import Path
import unittest
import numpy as np
from ai_opponent import AIController,pose_input
from config import Config
from games import GAMES
from match import Match,update_game,ranking_key
from motion_input import MotionInput,from_player
from player_bank import PlayerBank
from simulated_input import SimulatedInput
from storage import Storage
from gesture_controller import GestureController
from tracking_types import TrackingFrame,neutral_pose,LH,RH


def ideal(game):
    key=game.game_id
    if key=="red_green":
        return MotionInput(run=1. if game.phase=="GREEN" else 0.)
    if key=="sprint":
        return MotionInput(run=1.)
    if key=="lightning":
        return MotionInput(right_hand=game.target)
    if key=="dodge":
        return pose_input(game.required)
    if key=="timekeeper":
        return MotionInput(left_up=game.target_time-.04<=game.beat_age<game.target_time+.12)
    if key=="echo" and game.stage=="REPEAT":
        return pose_input(game.expected)
    return MotionInput()


def run_game(key,policy=ideal,seed=123):
    game=GAMES[key]["factory"](Config(endless=False),0,random.Random(seed))
    for i in range(1,60*100):
        update_game(game,i/60,policy(game),True)
        if game.finished:
            return game
    raise AssertionError(f"{key} did not terminate")


class ArcadeTests(unittest.TestCase):
    def test_all_six_can_be_won(self):
        for key in GAMES:
            with self.subTest(game=key):
                g=run_game(key)
                self.assertTrue(g.won)
                self.assertGreater(g.score,0)
                self.assertLessEqual(g.elapsed,g.duration+.001)

    def test_all_six_idle_players_lose(self):
        for key in GAMES:
            with self.subTest(game=key):
                g=run_game(key,lambda g:MotionInput())
                self.assertFalse(g.won)

    def test_all_five_new_clocks_pause_without_catchup(self):
        for key in GAMES:
            if key=="red_green":
                continue
            with self.subTest(game=key):
                g=GAMES[key]["factory"](Config(endless=False),0,random.Random(1))
                g.update(4,MotionInput(),True)
                before=(g.elapsed,g.progress,g.score)
                g.update(4.01,ideal(g),False)
                g.update(100,ideal(g),False)
                g.update(101,ideal(g),True)
                self.assertEqual(before,(g.elapsed,g.progress,g.score))
                g.update(101.1,MotionInput(),True)
                self.assertAlmostEqual(g.elapsed,before[0]+.1)

    def test_holding_one_hand_up_does_not_farm_beats(self):
        g=run_game("timekeeper",lambda g:MotionInput(left_up=True))
        self.assertEqual(g.score,0)
        self.assertFalse(g.won)

    def test_orbs_require_reaching_and_holding(self):
        g=GAMES["lightning"]["factory"](Config(endless=False),0,random.Random(1))
        g.update(3,MotionInput())
        target=g.target
        g.update(3.03,MotionInput(right_hand=target))
        self.assertEqual(g.score,0)
        g.update(3.08,MotionInput())
        self.assertEqual(g.touch_held,0)
        g.update(3.2,MotionInput(right_hand=target))
        self.assertGreater(g.score,0)
        self.assertNotEqual(g.target,target)

    def test_echo_score_alone_cannot_replace_sequence_completion(self):
        g=GAMES["echo"]["factory"](Config(endless=False),0,random.Random(1))
        g.score=10000
        g.update(60,MotionInput())
        self.assertTrue(g.finished)
        self.assertFalse(g.won)

    def test_only_correct_dodge_saves_shield(self):
        g=GAMES["dodge"]["factory"](Config(endless=False),0,random.Random(3))
        g.update(3,MotionInput())
        required=g.required
        wrong=pose_input("RIGHT" if required!="RIGHT" else "DUCK")
        for i in range(1,160):
            g.update(3+i/60,wrong)
        self.assertLess(g.lives,5)


class OpponentAndMatchTests(unittest.TestCase):
    def test_ai_finishes_every_game_without_external_services(self):
        for key in GAMES:
            with self.subTest(game=key):
                brain=AIController("normal",7)
                game=run_game(key,brain.act)
                self.assertTrue(game.finished)

    def test_opponents_are_reproducible(self):
        for key in GAMES:
            first=run_game(key,AIController("hard",42).act)
            second=run_game(key,AIController("hard",42).act)
            self.assertEqual((first.score,first.won,round(first.elapsed,4)),(second.score,second.won,round(second.elapsed,4)))

    def test_shared_match_clock_and_identical_seeded_challenges(self):
        match=Match(Config(endless=False),"dodge","duo",0,seed=9)
        self.assertEqual(match.games[0].required,match.games[1].required)
        match.update(4,[MotionInput(),MotionInput()],[True,True])
        before=[g.elapsed for g in match.games]
        match.update(5,[MotionInput(),MotionInput()],[True,False])
        match.update(40,[MotionInput(),MotionInput()],[True,False])
        self.assertEqual(before,[g.elapsed for g in match.games])
        match.update(41,[MotionInput(),MotionInput()],[True,True])
        self.assertEqual(before,[g.elapsed for g in match.games])

    def test_two_players_control_independent_scores(self):
        match=Match(Config(endless=False),"lightning","duo",0,seed=1)
        for i in range(1,60*45):
            match.update(i/60,[MotionInput(),ideal(match.games[1])],[True,True])
            if match.finished:
                break
        self.assertTrue(match.finished)
        self.assertEqual(match.games[0].score,0)
        self.assertGreater(match.games[1].score,1000)
        self.assertEqual(match.winner_indices,[1])

    def test_completed_human_does_not_pause_ai_when_leaving(self):
        match=Match(Config(endless=False),"sprint","ai",0,seed=7)
        match.games[0].finished=match.games[0].won=True
        match.update(4,[MotionInput()],[False])
        self.assertGreater(match.games[1].elapsed,0)
        self.assertFalse(match.paused)

    def test_party_turns_get_same_pose_sequences(self):
        first=Match(Config(endless=False),"echo","party",0,seed=77)
        second=Match(Config(endless=False),"echo","party",500,seed=77)
        self.assertEqual(first.games[0].sequence,second.games[0].sequence)


class LaneTests(unittest.TestCase):
    def test_hand_switch_margin_scales_with_camera_distance(self):
        from tracking_types import LW,RW
        g=GestureController(Config(endless=False))
        p=neutral_pose()
        p[:,:2]=(p[:,:2]-.5)*.6+.5
        p[LW,1]-=.3
        f=TrackingFrame(0,p,people=1)
        g.hand_position(f,p,.03)
        self.assertEqual(g.active_wrist,LW)
        p[LW,1]+=.3
        p[RW,1]=p[LW,1]-.04
        g.hand_position(f,p,.03)
        self.assertEqual(g.active_wrist,RW)

    def test_cursor_mapping_is_consistent_between_solo_and_duo(self):
        sim=SimulatedInput()
        source=sim.sample(0,.03,cursor=(1080,770))
        g=GestureController(Config(endless=False))
        solo=g.hand_position(source,source.landmarks,.03)
        p=source.landmarks.copy()
        p[:,0]=(p[:,0]-.5)*1.5+.5
        p[:,1]=(p[:,1]-.5)*.75+.5
        duo=TrackingFrame(0,p,people=1,aspect=2/3)
        mapped=GestureController(Config(endless=False)).hand_position(duo,p,.03)
        np.testing.assert_allclose(solo,mapped,atol=1e-8)

    def frame(self,t,reverse=False,centers=(.25,.75)):
        poses=[]
        for center in centers:
            p=neutral_pose()
            p[:,0]=(p[:,0]-.5)*.75+center
            p[:,1]=(p[:,1]-.5)*.75+.5
            poses.append(p)
        if reverse:
            poses.reverse()
        return TrackingFrame(t,people=len(poses),poses=poses)

    def test_detector_order_does_not_swap_lanes(self):
        bank=PlayerBank(Config(endless=False))
        bank.update(self.frame(1),1,True)
        first=[p.smoothed.copy() for p in bank.players]
        bank.update(self.frame(1.04,True),1.04,True)
        for i,p in enumerate(bank.players):
            self.assertTrue(p.valid)
            np.testing.assert_allclose(first[i],p.smoothed)

    def test_crossing_lanes_requires_explicit_rejoin(self):
        bank=PlayerBank(Config(endless=False))
        bank.update(self.frame(1),1,True)
        for p in bank.players:
            p.registered=True
        bank.update(self.frame(1.04,centers=(.49,.51)),1.04,True)
        self.assertTrue(all(p.needs_rejoin for p in bank.players))
        bank.update(self.frame(1.08),1.08,True)
        self.assertFalse(any(p.registered for p in bank.players))

    def test_missing_partner_does_not_give_other_body_to_them(self):
        bank=PlayerBank(Config(endless=False))
        bank.update(self.frame(1,centers=(.75,)),1,True)
        self.assertFalse(bank.players[0].valid)
        self.assertTrue(bank.players[1].valid)

    def test_two_people_are_rejected_in_solo_mode(self):
        bank=PlayerBank(Config(endless=False))
        bank.update(self.frame(1),1,False)
        self.assertFalse(bank.players[0].valid)


class RecordMigrationTests(unittest.TestCase):
    def test_old_database_migrates_without_losing_records(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"old.sqlite3"
            c=sqlite3.connect(path)
            c.execute("CREATE TABLE results (id INTEGER PRIMARY KEY,created_utc TEXT,player TEXT,mode TEXT,won INTEGER,elapsed REAL,remaining REAL,violations INTEGER,events TEXT)")
            c.execute("INSERT INTO results VALUES(1,'old','Player 1','camera',1,24.5,35.5,0,'[]')")
            c.commit()
            c.close()
            store=Storage(path)
            self.assertEqual(store.best("Player 1"),24.5)
            self.assertEqual(store.connection.execute("SELECT COUNT(*) FROM results").fetchone()[0],1)
            store.close()

    def test_games_and_modes_keep_separate_bests_and_boards(self):
        with tempfile.TemporaryDirectory() as temp:
            store=Storage(Path(temp)/"records.sqlite3")
            g=run_game("lightning")
            store.save("P1","demo",g,"ai",4)
            self.assertEqual(store.best_score("P1","demo","lightning","ai"),g.score)
            self.assertIsNone(store.best_score("P1","demo","timekeeper","ai"))
            self.assertIsNone(store.best_score("P1","camera","lightning","ai"))
            self.assertIsNone(store.best_score("P1","demo","lightning","solo"))
            self.assertEqual(len(store.leaderboard("demo",5,"lightning","ai","score")),1)
            store.close()


if __name__=="__main__":
    unittest.main()
