#!/usr/bin/env python3
import sys, runpy, random
from pathlib import Path
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(".") / ".env")  # carica le variabili da .env

ROOT = Path(__file__).resolve().parent
OUT  = ROOT / "output"
PROF = ROOT / "profiles"

REQUIRED = {
    "csv": ROOT / "Feature_Ranges_Espansi.csv",
    "personas": PROF / "personas.json",
    "coach": PROF / "istruttore.json",
}

SCRIPTS = [
    "extract_tracks.py",    # genera output/tracks_by_genre.json
    "rank_playlist.py",     # modalità “classe” (AWM-majority)
    "rank_instructor.py",   # modalità “istruttore” (MRP + AWM)
]

def ensure_layout():
    OUT.mkdir(parents=True, exist_ok=True)
    PROF.mkdir(parents=True, exist_ok=True)
    missing = [k for k,p in REQUIRED.items() if not p.exists()]
    if missing:
        raise SystemExit(f"⚠️  Mancano risorse: {', '.join(missing)}. Attesi in {ROOT}")

def run_script(path, seed=None):
    argv_backup = sys.argv[:]
    try:
        sys.argv = [path]
        if seed is not None:
            sys.argv += ["--seed", str(seed)]
        runpy.run_path(str(ROOT / path), run_name="__main__")
    finally:
        sys.argv = argv_backup

def main():
    ensure_layout()
    seed = None  # metti un intero per riproducibilità (es. 42)
    for s in SCRIPTS:
        print(f"\n▶ {s}")
        run_script(s, seed=seed)
    print("\n✅ Pipeline terminata.")

if __name__ == "__main__":
    main()
