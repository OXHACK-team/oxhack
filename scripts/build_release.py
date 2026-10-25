"""Build an upload ZIP with source, artwork and models; keep local data private."""
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from config import Config
from validate_release import validate

DIRECTORIES=("games","ui","scripts","tests","assets","models")
EXCLUDED={".venv",".venv-mac","venv",".git","__pycache__","data","artifacts","release","node_modules"}
ROOT_SUFFIXES={".py",".ps1",".cmd",".command",".md"}


def release_files(root=ROOT):
    root=Path(root).resolve()
    files=[p for p in root.iterdir() if p.is_file() and
           (p.suffix.lower() in ROOT_SUFFIXES or p.name in ("requirements.txt","config.json",".gitignore"))]
    for folder in DIRECTORIES:
        base=root/folder
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            relative=path.relative_to(root)
            if any(part in EXCLUDED for part in relative.parts) or path.is_symlink() or not path.is_file():
                continue
            if path.suffix.lower() in (".pyc",".pyo",".tmp",".part"):
                continue
            files.append(path)
    return sorted(set(files),key=lambda p:p.relative_to(root).as_posix())


def build(output,release_date,root=ROOT):
    root=Path(root).resolve()
    report=validate(root)
    if report["status"]!="PASS":
        raise ValueError("Source validation failed: "+"; ".join(report["errors"]))
    output=Path(output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix(output.suffix+".tmp")
    entries=[]
    # A submission starts with normal defaults, not the team's camera settings.
    defaults=(json.dumps(asdict(Config()),indent=2)+"\n").encode("utf-8")
    with zipfile.ZipFile(temporary,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in release_files(root):
            relative=path.relative_to(root).as_posix()
            payload=defaults if relative=="config.json" else path.read_bytes()
            info=zipfile.ZipInfo("oxhack/"+relative)
            info.create_system=3
            info.external_attr=(0o100755 if path.suffix==".command" else 0o100644)<<16
            info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,payload)
            entries.append({"path":relative,"bytes":len(payload),"sha256":hashlib.sha256(payload).hexdigest()})
        manifest={"project":"CHRONO ARENA","release_date":release_date,
                  "python":"3.11 (64-bit)","files":entries,
                  "excluded":"Local environments, Git history, player records, caches and QA artifacts"}
        archive.writestr("oxhack/RELEASE_MANIFEST.json",json.dumps(manifest,indent=2)+"\n")
    with zipfile.ZipFile(temporary) as archive:
        bad=archive.testzip()
        if bad:
            raise ValueError("ZIP integrity failed: "+bad)
        for entry in archive.namelist():
            parts=Path(entry).parts
            if not entry.startswith("oxhack/") or ".." in parts or any(part in EXCLUDED for part in parts):
                raise ValueError("Unexpected file in release: "+entry)
    temporary.replace(output)
    checksum=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix+".sha256").write_text(f"{checksum}  {output.name}\n",encoding="ascii")
    return {"status":"PASS","zip":str(output),"files":len(entries)+1,
            "bytes":output.stat().st_size,"sha256":checksum,"release_date":release_date}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"release/CHRONO_ARENA_OxHack_Release.zip")
    parser.add_argument("--release-date",default=datetime.now(timezone.utc).date().isoformat())
    args=parser.parse_args()
    try:
        result=build(args.output,args.release_date)
    except (OSError,ValueError,zipfile.BadZipFile) as exc:
        print(f"Release build failed: {exc}",file=sys.stderr)
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
