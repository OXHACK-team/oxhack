import unittest
from types import SimpleNamespace
from ui.ratings import rate_run


def game(**changes):
    data=dict(game_id="lightning",endless=True,elapsed=0.,score=0,violations=0,events=[],best_combo=0,won=False,metric="score",goal=1200,duration=36.,progress=0.)
    data.update(changes)
    return SimpleNamespace(**data)


class RunRatingTests(unittest.TestCase):
    def test_survival_medals_have_explicit_time_boundaries(self):
        for seconds,grade in ((0,"D"),(19.99,"D"),(20,"C"),(45,"B"),(90,"A"),(180,"S"),(3600,"S")):
            with self.subTest(seconds=seconds):
                result=rate_run(game(elapsed=seconds,score=100))
                self.assertEqual(result.grade,grade)
                self.assertTrue(0<=result.progress<=1)

    def test_idle_score_cannot_earn_a_survival_medal(self):
        self.assertEqual(rate_run(game(elapsed=180,score=0)).grade,"D")

    def test_failed_challenge_cannot_earn_a_completion_medal(self):
        self.assertEqual(rate_run(game(endless=False,score=10000,won=False)).grade,"D")

    def test_fast_time_and_clean_dodges_are_rewarded(self):
        self.assertEqual(rate_run(game(game_id="sprint",endless=False,metric="time",elapsed=12,duration=40,won=True)).grade,"S")
        self.assertEqual(rate_run(game(game_id="dodge",endless=False,elapsed=36,won=True)).grade,"S")
        self.assertEqual(rate_run(game(game_id="dodge",endless=False,elapsed=36,won=True,violations=4)).grade,"C")

    def test_highlight_counts_actual_scored_actions(self):
        result=rate_run(game(events=[{"event":"score"},{"event":"miss"},{"event":"score"}],best_combo=2))
        self.assertEqual(result.highlight,"2 ORBS CHARGED  /  BEST CHAIN 2")


if __name__=="__main__":
    unittest.main()
