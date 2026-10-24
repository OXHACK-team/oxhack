"""Integration acceptance: real synthetic landmarks, UI dwell, six games and modes."""
import json
import tempfile
import time
from pathlib import Path
import pygame
from config import Config,ROOT
from game_manager import App
from games import GAMES


def controls_for(game,perfect=True):
    if not perfect or game.finished:
        return {}
    key=game.game_id
    if key=="red_green":
        return {"running":game.phase=="GREEN"}
    if key=="sprint":
        return {"running":True}
    if key=="lightning":
        return {"cursor":(game.target[0]*1440,game.target[1]*900)}
    if key=="dodge":
        return {"lean":-1 if game.required=="LEFT" else 1 if game.required=="RIGHT" else 0,"crouch":game.required=="DUCK"}
    if key=="timekeeper":
        return {"raise_hand":game.target_time-.085<=game.beat_age<game.target_time+.13}
    if key=="echo" and game.stage=="REPEAT":
        pose=game.expected
        return {"lean":-1 if pose=="LEFT" else 1 if pose=="RIGHT" else 0,"crouch":pose=="DUCK","both_up":pose=="HANDS UP"}
    return {}


def run():
    folder=ROOT/"artifacts/v2"
    folder.mkdir(parents=True,exist_ok=True)
    report={"status":"RUNNING","screenshots":[],"solo":{},"ai":{},"duo":{},"party":{}}
    with tempfile.TemporaryDirectory() as temp:
        app=App(Config(endless=False),demo=True,windowed=True,data_path=Path(temp)/"acceptance.sqlite3",settings_path=Path(temp)/"config.json")
        app.rng.seed(2026)
        now=time.perf_counter()
        def tick(seconds,**controls):
            nonlocal now
            for _ in range(round(seconds*60)):
                now+=1/60
                app.step(1/60,now,events=[],controls=controls)
        def capture(name):
            app.transition_from=None
            app.buttons=app.screens.buttons()
            app.render(now)
            pygame.image.save(app.canvas,str(folder/(name+".png")))
            report["screenshots"].append(name+".png")
        def select(key):
            button=next((b for b in app.screens.buttons() if b.key==key and b.enabled),None)
            assert button is not None,f"No enabled button {key} on {app.scene}"
            app.input_mode="hand"
            tick(.22,cursor=(720,205))
            tick(2.05,cursor=button.rect.center)
        def begin(key,mode,party_count=2):
            app.activate("all_games",now)
            tick(.1)
            select(key)
            assert app.scene=="mode",(key,app.scene)
            select("mode_"+mode)
            if mode=="duo":
                tick(1.4)
                capture("09-two-player-lobby")
                tick(1.35,raise_hand=True,p2={"raise_hand":True})
                assert all(p.registered for p in app.bank.players),"Two-player raise-hand join failed"
            elif app.scene=="welcome":
                tick(1.4)
                tick(1.35,raise_hand=True)
                tick(1.1)
            assert app.scene=="briefing",(key,mode,app.scene)
            if mode=="party":
                while app.party_count<party_count:
                    select("party_more")
                while app.party_count>party_count:
                    select("party_less")
            if mode=="solo":
                capture("briefing-"+key)
            if mode=="ai" and key=="red_green":
                select("difficulty_easy")
                assert app.config.ai_difficulty=="easy"
                select("difficulty_normal")
                assert app.config.ai_difficulty=="normal"
            select("start")
            assert app.scene=="game",(key,mode,app.scene)
        def play(perfect=True,p2_perfect=True,capture_name=None,inject_penalty=False):
            frames=0
            captured=False
            penalty_captured=False
            while app.scene=="game" and frames<60*125:
                controls=controls_for(app.match.games[0],perfect)
                if inject_penalty and app.game.phase=="RED" and app.game.violations==0:
                    controls["running"]=True
                if app.match.human_count==2:
                    controls["p2"]=controls_for(app.match.games[1],p2_perfect)
                tick(1/60,**controls)
                frames+=1
                if inject_penalty and app.game.violations>0 and not penalty_captured:
                    capture("red-light-penalty")
                    penalty_captured=True
                if capture_name and not captured and app.game.countdown==0 and app.game.elapsed>4:
                    capture(capture_name)
                    captured=True
            assert app.scene=="results",f"Match stalled: {app.selected_game}/{app.session_mode} {app.player.message}"
            return {"won":app.game.won,"score":app.game.score,"elapsed":round(app.game.elapsed,3),"violations":app.game.violations}
        try:
            tick(1.2)
            capture("01-welcome")
            assert app.player.neutral is not None
            tick(1.35,raise_hand=True)
            assert app.player.registered
            tick(1.1)
            assert app.scene=="menu"
            capture("02-home")
            select("how")
            capture("03-how-to-play")
            select("back")
            select("settings")
            capture("04-settings")
            select("menu")
            select("play")
            capture("05-six-games")
            select("red_green")
            capture("06-player-modes")
            for key in GAMES:
                begin(key,"solo")
                # The first match also verifies manual and tracking-based pauses.
                if key=="red_green":
                    tick(3.1)
                    previous=app.game.elapsed
                    tick(.25,lost=True)
                    assert app.game.elapsed==previous
                    capture("07-tracking-pause")
                    tick(.1)
                    app.go_back(now)
                    previous=app.game.elapsed
                    tick(.3)
                    assert app.game.elapsed==previous
                    app.activate("resume",now)
                result=play(capture_name="game-"+key,inject_penalty=key=="red_green")
                assert result["won"],f"Synthetic body could not win {key}: {result}"
                report["solo"][key]=result
                capture("result-"+key)
                if key=="red_green":
                    best=app.storage.best(app.current_name,"demo","red_green","solo")
                    select("again")
                    assert app.scene=="game"
                    loss=play(perfect=False)
                    assert not loss["won"]
                    assert app.storage.best(app.current_name,"demo","red_green","solo")==best
                    report["rematch_loss"]=loss
                    capture("rematch-timeout")
            for key in GAMES:
                begin(key,"ai")
                result=play(capture_name="ai-"+key if key in ("sprint","timekeeper") else None)
                assert app.match.finished and app.match.games[1].finished
                assert result["won"],(key,result)
                result["ai_score"]=app.match.games[1].score
                result["winner_indices"]=app.match.winner_indices
                report["ai"][key]=result
            capture("08-ai-results")
            for key in GAMES:
                begin(key,"duo")
                capture("09-two-players-ready")
                result=play(perfect=False,p2_perfect=True,capture_name="two-player-"+key)
                assert app.match.games[1].won,"Player 2's body did not control their game"
                assert app.match.winner_indices==[1],"Player 2 should beat idle Player 1"
                report["duo"][key]={"player1":result,"player2_score":app.match.games[1].score}
            capture("10-two-player-results")
            # A remaining second player can drive the menu when Player 1 steps out.
            button=next(b for b in app.screens.buttons() if b.key=="all_games")
            app.input_mode="hand"
            tick(2.3,lost=True,p2={"cursor":button.rect.center})
            assert app.scene=="select" and app.menu_controller==1,"Player 2 could not navigate after Player 1 left"
            report["player2_menu_handoff"]=True
            for count,key in [(2,key) for key in GAMES]+[(4,"dodge")]:
                begin(key,"party",count)
                seeds=[]
                for turn in range(count):
                    if turn:
                        select("next_player")
                        assert app.scene=="handoff"
                        if count==4 and turn==1:
                            capture("11-party-handoff")
                        tick(1.3)
                        tick(1.35,raise_hand=True)
                        tick(1.1)
                        assert app.scene=="briefing"
                        select("start")
                    seeds.append(app.match.seed)
                    play(perfect=turn==0)
                assert len(set(seeds))==1,"Party challenge changed between players"
                assert len(app.party_results)==count
                report["party"][key+"_"+str(count)]={"game":key,"turns":len(app.party_results),"shared_seed":seeds[0]}
                capture(f"party-{key}-{count}-results")
            # Exactly one record per human finish. AI never enters the human board.
            saved=app.storage.connection.execute("SELECT COUNT(*) FROM results").fetchone()[0]
            assert saved==6+1+6+6*2+6*2+4,(saved,"Expected 41 human records")
            report["saved_human_results"]=saved
            report["gesture_navigation"]="actual synthetic wrist landmarks, smoothing and dwell"
            report["status"]="PASS"
            (folder/"acceptance-report.json").write_text(json.dumps(report,indent=2)+"\n")
            print(json.dumps({k:v for k,v in report.items() if k!="screenshots"},indent=2))
        except Exception:
            capture("FAILURE-"+app.scene)
            raise
        finally:
            app.close()
    return 0
