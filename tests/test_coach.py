import unittest
import os
import tempfile
import time
from pathlib import Path
from config import Config
from motion_input import MotionInput
from ui.coach import PracticeCoach,LESSONS


def correct(step):
    return MotionInput(run=.7,motion=0.,lean=-.4 if step.kind=="LEFT" else .4 if step.kind=="RIGHT" else 0.,
                       crouch=step.kind=="DUCK",left_up=step.kind in ("RAISE","HANDS UP"),right_up=step.kind=="HANDS UP",
                       right_hand=step.target if step.kind=="REACH" else (.75,.9))


class PracticeCoachTests(unittest.TestCase):
    def test_all_six_real_action_vocabularies_can_finish_their_lesson(self):
        for game_id in LESSONS:
            with self.subTest(game=game_id):
                coach=PracticeCoach(game_id,Config())
                for _ in range(300):
                    coach.update(1/30,[correct(coach.players[0].current_step)],[True])
                    if coach.complete:
                        break
                self.assertTrue(coach.complete)

    def test_lost_tracking_resets_hold_and_cannot_complete_freeze(self):
        coach=PracticeCoach("red_green",Config())
        p=coach.players[0]
        p.step_index=1
        for _ in range(20):
            coach.update(1/30,[MotionInput()],[True])
        self.assertGreater(p.hold_progress,0.)
        for _ in range(100):
            coach.update(1/30,[MotionInput()],[False])
        self.assertFalse(coach.complete)
        self.assertEqual(p.hold_progress,0.)

    def test_wrong_move_interrupts_a_pose_hold(self):
        coach=PracticeCoach("dodge",Config())
        coach.update(.1,[MotionInput(lean=-.5)],[True])
        self.assertGreater(coach.players[0].hold_progress,0.)
        coach.update(.1,[MotionInput(lean=.5)],[True])
        self.assertEqual(coach.players[0].hold_progress,0.)
        self.assertEqual(coach.players[0].step_index,0)

    def test_partner_practice_progress_is_independent(self):
        coach=PracticeCoach("sprint",Config(),2)
        for _ in range(60):
            coach.update(1/30,[MotionInput(run=.8),MotionInput()],[True,True])
        self.assertTrue(coach.players[0].complete)
        self.assertFalse(coach.players[1].complete)
        self.assertFalse(coach.complete)

    def test_hand_shaking_does_not_teach_the_jog_and_lag_does_not_skip_it(self):
        coach=PracticeCoach("sprint",Config())
        for _ in range(60):
            coach.update(1/30,[MotionInput(motion=8.)],[True])
        self.assertEqual(coach.players[0].hold_progress,0.)
        coach.update(10,[MotionInput(run=1.)],[True])
        self.assertFalse(coach.complete)
        self.assertLess(coach.players[0].hold_progress,.1)

    def test_six_body_input_practices_start_games_without_writing_results(self):
        os.environ["SDL_VIDEODRIVER"]="dummy"
        os.environ["SDL_AUDIODRIVER"]="dummy"
        from game_manager import App
        with tempfile.TemporaryDirectory() as temp:
            app=App(Config(sound=False),demo=True,windowed=True,data_path=Path(temp)/"practice.sqlite3",settings_path=Path(temp)/"settings.json")
            now=time.perf_counter()
            try:
                app.step(1/30,now,events=[])
                app.quick_join(now)
                for game_id in LESSONS:
                    with self.subTest(game=game_id):
                        app.selected_game=game_id
                        app.choose_mode("solo",now)
                        self.assertEqual(app.scene,"briefing")
                        app.activate("practice",now)
                        self.assertIsNone(app.match)
                        for _ in range(600):
                            state=app.practice.players[0]
                            kind=state.current_step.kind
                            controls=dict(running=kind=="RUN",raise_hand=kind=="RAISE",both_up=kind=="HANDS UP",
                                          lean=-1 if kind=="LEFT" else 1 if kind=="RIGHT" else 0,crouch=kind=="DUCK")
                            if kind=="REACH":
                                controls["cursor"]=(720,315)
                            now+=1/30
                            app.step(1/30,now,events=[],controls=controls)
                            if app.practice.complete:
                                break
                        self.assertTrue(app.practice.complete)
                        self.assertEqual(app.storage.connection.execute("SELECT COUNT(*) FROM results").fetchone()[0],0)
                        app.activate("start",now)
                        self.assertEqual(app.scene,"game")
                        app.activate("all_games",now)
            finally:
                app.close()


if __name__=="__main__":
    unittest.main()
