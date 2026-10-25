"""Validate an extracted CHRONO ARENA release without installing dependencies.

Read-only by default. Use --root to check another extracted folder and --output
to write a JSON report. The command does not start a camera, import Pygame,
create a database, download models, or create Python bytecode caches.
"""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys


ROOT=Path(__file__).resolve().parents[1]
REQUIRED=(
    "main.py","config.py","config.json","game_manager.py","ai_opponent.py",
    "audio.py","avatar.py","camera.py","gesture_controller.py","match.py",
    "motion_input.py","movement.py","player_bank.py","player_manager.py",
    "pose_tracker.py","progression.py","simulated_input.py","sprite_rig.py",
    "storage.py","tracking_types.py","requirements.txt","README.md","START_HERE.md",
    "setup.ps1","run.ps1","Setup CHRONO ARENA.cmd","Launch CHRONO ARENA.cmd","Launch Demo.cmd",
    "Setup Mac.command","Launch Mac.command","Launch Demo Mac.command",
    "games/__init__.py","games/timed.py","games/red_light_green_light.py",
    "games/lightning_strike.py","games/dodge_or_die.py","games/chrono_sprint.py",
    "games/timekeeper.py","games/echo_shift.py","ui/__init__.py","ui/art.py",
    "ui/components.py","ui/coach.py","ui/effects.py","ui/ratings.py","ui/screens.py","ui/theme.py",
    "ui/tracking_preview.py",
    "ui/world_geometry.py","ui/worlds.py","assets/manifest.json","assets/PROMPTS.md",
    "models/manifest.json","scripts/download_models.py","scripts/verify_tracking.py",
    "scripts/benchmark.py","scripts/validate_release.py","tests/__init__.py",
    "tests/smoke.py","tests/survival_smoke.py","SUBMISSION.md","scripts/build_release.py",
)
SKIP={".venv","venv",".git","__pycache__","data","artifacts","node_modules"}


def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda:source.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def validate(root):
    root=Path(root).resolve()
    errors=[]
    verified=[]
    checked_python=[]
    for name in REQUIRED:
        path=root/name
        if not path.is_file():
            errors.append(f"Missing {name}; include it when creating/extracting the release.")
        elif path.stat().st_size==0:
            # Empty __init__.py files are valid packages.
            if not name.endswith("__init__.py"):
                errors.append(f"Empty required file: {name}.")
    for folder in ("assets","models"):
        manifest=root/folder/"manifest.json"
        if not manifest.exists():
            continue
        try:
            entries=json.loads(manifest.read_text(encoding="utf-8-sig"))
            if not isinstance(entries,dict) or not entries:
                raise ValueError("expected a nonempty object of file records")
            for name,record in entries.items():
                relative=Path(name)
                if relative.is_absolute() or ".." in relative.parts:
                    errors.append(f"Unsafe path in {folder}/manifest.json: {name!r}.")
                    continue
                path=root/folder/relative
                display=f"{folder}/{name}"
                if not path.is_file():
                    errors.append(f"Missing {display}; include the bundled {folder} files.")
                    continue
                actual=digest(path)
                size=path.stat().st_size
                if size!=record.get("bytes") or actual!=record.get("sha256"):
                    errors.append(f"Corrupt or mismatched {display}; restore the file matching its manifest.")
                    continue
                if folder=="assets" and relative.suffix.lower()==".png":
                    header=path.open("rb")
                    with header:
                        data=header.read(26)
                    if len(data)<26 or data[:8]!=b"\x89PNG\r\n\x1a\n":
                        errors.append(f"Invalid PNG header: {display}.")
                        continue
                    dimensions=list(struct.unpack(">II",data[16:24]))
                    if record.get("size")!=dimensions:
                        errors.append(f"Wrong image dimensions: {display}.")
                        continue
                verified.append({"path":display,"bytes":size,"sha256":actual})
        except (OSError,ValueError,TypeError,AttributeError) as exc:
            errors.append(f"Cannot read {folder}/manifest.json: {exc}.")
    # Parse all included sources without importing third-party modules or writing
    # pycache. Also catch references to omitted files in our local packages.
    sources=list(root.glob("*.py"))
    for folder in ("games","ui","scripts","tests"):
        sources.extend((root/folder).rglob("*.py"))
    for path in sorted(set(sources)):
        if any(part in SKIP for part in path.relative_to(root).parts):
            continue
        try:
            tree=ast.parse(path.read_text(encoding="utf-8-sig"),filename=str(path))
            checked_python.append(path.relative_to(root).as_posix())
            for node in ast.walk(tree):
                if isinstance(node,ast.ImportFrom) and node.module and node.module.split(".")[0] in {"ui","games","tests"}:
                    imported=root.joinpath(*node.module.split("."))
                    if not imported.with_suffix(".py").is_file() and not (imported/"__init__.py").is_file():
                        errors.append(f"{path.relative_to(root)} imports omitted local module {node.module}.")
        except (OSError,UnicodeError,SyntaxError) as exc:
            errors.append(f"Invalid Python source {path.relative_to(root)}: {exc}.")
    if (root/"config.py").is_file() and (root/"config.json").is_file():
        try:
            # Config imports only the standard library and has no filesystem writes.
            spec=importlib.util.spec_from_file_location("_chrono_release_config",root/"config.py")
            module=importlib.util.module_from_spec(spec)
            sys.modules[spec.name]=module
            # exec(compiled source) deliberately avoids importlib's bytecode cache.
            exec(compile((root/"config.py").read_text(encoding="utf-8-sig"),str(root/"config.py"),"exec"),module.__dict__)
            module.Config.load(root/"config.json")
        except (OSError,ValueError,TypeError,AttributeError,KeyError,SyntaxError) as exc:
            errors.append(f"Invalid config.json: {exc}.")
        finally:
            sys.modules.pop("_chrono_release_config",None)
    required_bundles={"models/pose_landmarker_lite.task","models/hand_landmarker.task",
                      "assets/chrono-stadium.png","assets/game-atlas.png","assets/athlete-rig.png"}
    verified_names={item["path"] for item in verified}
    for name in sorted(required_bundles-verified_names):
        if not any(name in error for error in errors):
            errors.append(f"{name} is not verified by its folder's manifest.json.")
    return {"status":"FAIL" if errors else "PASS","root":str(root),
            "checked_utc":datetime.now(timezone.utc).isoformat(),
            "required_files":len(REQUIRED),"python_files_checked":len(checked_python),
            "verified_assets_and_models":verified,"errors":errors,
            "scope":"Static files, source syntax, config validation and bundled asset/model integrity. Does not test dependencies, camera or gameplay."}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=ROOT,help="Extracted project directory to validate")
    parser.add_argument("--output",type=Path,help="Optional JSON report path; otherwise no files are written")
    args=parser.parse_args()
    report=validate(args.root)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(f"Release validation: {report['status']} / {report['python_files_checked']} Python files / {len(report['verified_assets_and_models'])} hashed assets and models")
    for error in report["errors"]:
        print(f"  - {error}")
    return 0 if report["status"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
