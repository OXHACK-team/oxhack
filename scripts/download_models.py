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
EXPECTED = {
    "pose_landmarker_lite.task": {
        "bytes": 5777746,
        "sha256": "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a",
    },
    "hand_landmarker.task": {
        "bytes": 7819105,
        "sha256": "fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1",
    },
}


def verified(path, expected):
    if not path.is_file() or path.stat().st_size != expected["bytes"]:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == expected["sha256"]


def download():
    folder = ROOT / "models"
    folder.mkdir(exist_ok=True)
    manifest = {}
    for name, url in MODELS.items():
        path = folder / name
        expected = EXPECTED[name]
        temp = path.with_suffix(".part")
        try:
            if not verified(path, expected):
                print(f"Downloading verified {name} ...", flush=True)
                with urlopen(url, timeout=60) as response, temp.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                if not verified(temp, expected):
                    raise RuntimeError(f"Checksum verification failed for {name}. The cached file was not replaced; retry setup.")
                temp.replace(path)
        finally:
            temp.unlink(missing_ok=True)
        manifest[name] = {"url": url, **expected}
        print(f"Ready: {name} ({path.stat().st_size:,} bytes)", flush=True)
    manifest_path = folder / "manifest.json"
    manifest_temp = folder / "manifest.json.part"
    try:
        manifest_temp.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        manifest_temp.replace(manifest_path)
    finally:
        manifest_temp.unlink(missing_ok=True)


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    download()
