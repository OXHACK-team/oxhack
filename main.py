"""CHRONO ARENA native application entry point."""
import argparse
import os
import sys


def main():
    parser=argparse.ArgumentParser(description="CHRONO ARENA - move with time")
    parser.add_argument("--demo",action="store_true",help="Simulate body input; see per-game controls in the footer")
    parser.add_argument("--windowed",action="store_true")
    parser.add_argument("--headless",action="store_true",help="Use SDL dummy video/audio drivers")
    parser.add_argument("--no-camera",action="store_true",help="Exercise the camera-unavailable interface")
    parser.add_argument("--max-frames",type=int,default=0)
    parser.add_argument("--screenshot",help="Save the last rendered canvas to PNG")
    parser.add_argument("--data-path",help="Override SQLite path (useful for isolated tests)")
    parser.add_argument("--smoke-test",action="store_true",help="Verify all six games in Solo, AI, 2 Players and Party modes")
    args=parser.parse_args()
    if args.headless or args.smoke_test:
        os.environ["SDL_VIDEODRIVER"]="dummy"
        os.environ["SDL_AUDIODRIVER"]="dummy"
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT","1")
    if args.smoke_test:
        from tests.smoke import run
        return run()
    from config import Config
    from game_manager import App
    app=None
    try:
        cfg=Config.load()
        app=App(cfg,demo=args.demo,windowed=args.windowed or args.headless,data_path=args.data_path,no_camera=args.no_camera)
        app.run(args.max_frames,args.screenshot)
    except (ValueError,OSError) as exc:
        print(f"CHRONO ARENA could not start: {exc}",file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        if app:
            app.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
