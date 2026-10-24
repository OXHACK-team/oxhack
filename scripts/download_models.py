"""Fetch Google's official float16 Tasks assets once, then run offline."""
from pathlib import Path
from urllib.request import urlopen
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    "pose_landmarker_lite.task": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
    "hand_landmarker.task": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
}


def download():
    folder = ROOT / "models"
    folder.mkdir(exist_ok=True)
    manifest = {}
    for name, url in MODELS.items():
        path = folder / name
        if not path.exists():
            print(f"Downloading {name} ...", flush=True)
            temp = path.with_suffix(".part")
            try:
                with urlopen(url, timeout=60) as response, temp.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                if temp.stat().st_size < 100_000:
                    raise RuntimeError(f"Incomplete model: {name}")
                temp.replace(path)
            finally:
                temp.unlink(missing_ok=True)
        manifest[name] = {"url": url, "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        print(f"Ready: {name} ({path.stat().st_size:,} bytes)", flush=True)
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    download()
