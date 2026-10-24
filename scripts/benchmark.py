"""Measure uncapped native drawing and synthetic input; not a webcam FPS claim."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames",type=int,default=300)
    parser.add_argument("--headless",action="store_true")
    parser.add_argument("--mode",choices=("solo","ai","duo"),default="solo")
    parser.add_argument("--game",choices=("red_green","lightning","dodge","sprint","timekeeper","echo"),default="red_green")
    args=parser.parse_args()
    if args.headless:
        os.environ["SDL_VIDEODRIVER"]="dummy"
        os.environ["SDL_AUDIODRIVER"]="dummy"
    from config import Config
    from game_manager import App
    from tracking_types import neutral_pose
    import numpy as np
    with tempfile.TemporaryDirectory() as temp:
        app=App(Config(),demo=True,windowed=True,data_path=Path(temp)/"benchmark.sqlite3")
        try:
            now=time.perf_counter()
            app.session_mode=args.mode
            app.selected_game=args.game
            app.dual_active=args.mode=="duo"
            app.step(1/60,now,events=[])
            app.quick_join(now)
            app.start_match(now)
            times=[]
            for i in range(args.frames+10):
                start=time.perf_counter()
                now+=1/60
                app.step(1/60,now,events=[],controls={"running":getattr(app.game,"phase","GREEN")=="GREEN","p2":{"running":True}})
                app.render(now)
                elapsed=(time.perf_counter()-start)*1000
                if i>=10:
                    times.append(elapsed)
            report={"frames":len(times),"driver":"dummy" if args.headless else "native window","mode":args.mode,"game":args.game,
                    "median_frame_ms":float(np.median(times)),"p95_frame_ms":float(np.quantile(times,.95)),
                    "uncapped_mean_fps":1000/float(np.mean(times)),"scope":"render + synthetic input; webcam inference measured separately"}
            (ROOT/"artifacts").mkdir(exist_ok=True)
            name="benchmark-report.json" if args.mode=="solo" else f"benchmark-{args.mode}-report.json"
            (ROOT/"artifacts"/name).write_text(json.dumps(report,indent=2)+"\n")
            print(json.dumps(report,indent=2))
        finally:
            app.close()


if __name__=="__main__":
    main()
