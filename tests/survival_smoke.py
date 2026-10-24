"""All six survival games and all four player modes through real body-input code."""
import json
import tempfile
import time
from pathlib import Path
import pygame
from config import Config,ROOT
from game_manager import App
from games import GAMES
from tests.smoke import controls_for


def run():
    folder=ROOT/"artifacts/survival"
    folder.mkdir(parents=True,exist_ok=True)
    report={"status":"RUNNING","matches":[],"screenshots":[]}
    with tempfile.TemporaryDirectory() as temp:
        app=App(Config(),demo=True,windowed=True,data_path=Path(temp)/"records.sqlite3",settings_path=Path(temp)/"config.json")
        now=time.perf_counter()
        def tick(seconds,**controls):
            nonlocal now
            for _ in range(round(seconds*30)):
                now+=1/30
                app.step(1/30,now,events=[],controls=controls)
        def capture(name):
            app.transition_from=None
            app.buttons=app.screens.buttons()
            app.render(now)
            pygame.image.save(app.canvas,str(folder/(name+".png")))
            report["screenshots"].append(name+".png")
        def join():
            if app.scene=="lobby":
                tick(1.3)
                tick(1.35,raise_hand=True,p2={"raise_hand":True})
            elif app.scene in ("welcome","handoff"):
                tick(1.3)
                tick(1.35,raise_hand=True)
                tick(1.1)
        try:
            join()
            for mode in ("solo","ai","duo","party"):
                for key in GAMES:
                    app.activate("all_games",now)
                    app.activate(key,now)
                    app.choose_mode(mode,now)
                    join()
                    assert app.scene=="briefing",(key,mode,app.scene)
                    if mode=="solo":
                        capture("briefing-"+key)
                    for turn in range(2 if mode=="party" else 1):
                        if turn:
                            app.activate("next_player",now)
                            join()
                        tick(.2)
                        app.activate("start",now)
                        assert app.scene=="game",(key,mode,app.scene)
                        for _ in range(30*79):
                            controls=controls_for(app.game)
                            if mode=="duo":
                                controls["p2"]=controls_for(app.match.games[1])
                            tick(1/30,**controls)
                            assert app.scene=="game",(key,mode,app.game.elapsed,app.game.lives)
                        assert app.game.elapsed>75,(key,app.game.elapsed,app.player.message)
                        assert all(not g.finished for g in app.match.games[:app.match.human_count])
                        if mode in ("solo","duo"):
                            capture(mode+"-"+key)
                        values=[{"score":g.score,"survived":round(g.elapsed,2),"shields":g.lives,"level":g.level} for g in app.match.games]
                        app.activate("end_run",now)
                        assert app.scene=="results"
                        report["matches"].append({"game":key,"mode":mode,"turn":turn+1,"players":values})
                    if mode=="party" and key=="dodge":
                        capture("party-standings")
            saved=app.storage.connection.execute("SELECT COUNT(*) FROM results WHERE variant='endless'").fetchone()[0]
            assert saved==36,saved
            report["saved_human_results"]=saved
            report["status"]="PASS"
            report["input"]="30 Hz synthetic landmarks through calibration, motion, lane assignment and smoothing"
            (folder/"acceptance-report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
            print(json.dumps({"status":report["status"],"game_mode_combinations":24,"human_runs":saved,"minimum_active_seconds":75,"report":str(folder/"acceptance-report.json")},indent=2))
        except Exception:
            capture("FAILURE-"+app.scene)
            raise
        finally:
            app.close()
    return 0
