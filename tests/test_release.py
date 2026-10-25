"""Release-time regressions: stable demo controls, focus pauses and clean bundles."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import pygame
from tests import test_survival


class ReleaseControlTests(unittest.TestCase):
    def test_window_switch_pauses_and_never_resumes_itself(self):
        fixture=test_survival.BodyOnlyAppTests()
        fixture.setUp()
        try:
            fixture.join_duo()
            fixture.app.start_match(fixture.now)
            fixture.tick(3.3,[{},{}])
            before=fixture.app.game.elapsed
            fixture.app.step(.1,fixture.now+.1,events=[pygame.event.Event(pygame.WINDOWFOCUSLOST)])
            self.assertTrue(fixture.app.match.manual_pause)
            self.assertEqual(fixture.app.game.elapsed,before)
            fixture.app.step(.1,fixture.now+.2,events=[pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
            self.assertTrue(fixture.app.match.manual_pause)
        finally:
            fixture.tearDown()

    def test_mouse_leaving_lightning_playfield_never_disconnects_demo_player(self):
        fixture=test_survival.BodyOnlyAppTests()
        fixture.setUp()
        app=fixture.app
        try:
            app.demo=True
            app.session_mode="duo"
            app.dual_active=True
            app.selected_game="lightning"
            app.step(1/30,fixture.now,events=[])
            app.quick_join(fixture.now)
            app.start_match(fixture.now)
            app.input_mode="mouse"
            with patch("pygame.mouse.get_pos",return_value=(0,0)):
                for i in range(1,15):
                    app.step(1/30,fixture.now+i/30,events=[])
            self.assertTrue(all(p.valid and p.registered for p in app.bank.players))
            self.assertFalse(app.match.paused)
        finally:
            fixture.tearDown()


class BundleSelectionTests(unittest.TestCase):
    def test_source_bundle_keeps_models_and_excludes_personal_local_state(self):
        root=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location("arena_release_builder",root/"scripts/build_release.py")
        module=importlib.util.module_from_spec(spec)
        # Make the adjacent validator importable just as when the script runs.
        import sys
        sys.path.insert(0,str(root/"scripts"))
        try:
            spec.loader.exec_module(module)
            names={p.relative_to(root).as_posix() for p in module.release_files(root)}
        finally:
            sys.path.remove(str(root/"scripts"))
        self.assertIn("models/pose_landmarker_lite.task",names)
        self.assertIn("models/hand_landmarker.task",names)
        self.assertIn("START_HERE.md",names)
        self.assertIn("Setup CHRONO ARENA.cmd",names)
        self.assertFalse(any(any(part in {"data",".git",".venv","artifacts","__pycache__","release"} for part in Path(name).parts) for name in names))


if __name__=="__main__":
    unittest.main()
