#!/usr/bin/env python3
# counter_genre.py
import sys
import json
import argparse
from pathlib import Path
from collections import Counter

# Percorso di default (se non passi argomenti)
DEFAULT_FILE = Path("profiles/personas.json")

def iter_input_paths(paths):
    for p in paths:
        p = Path(p)
        if p.is_dir():
            yield from sorted(p.glob("*.json"))
        else:
            # Se è un glob non espanso (su Windows/cmd), prova noi
            if any(ch in str(p) for ch in "*?[]"):
                yield from sorted(Path().glob(str(p)))
            else:
                yield p

# Carica un JSON da file
def load_json_any(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Errore JSON in {path}: {e}") from e
    except FileNotFoundError:
        raise ValueError(f"File non trovato: {path}")

    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError(f"{path} non contiene un JSON lista o oggetto valido.")

# Conta le occorrenze dei generi preferiti delle personas
def collect_genres(files):
    counter = Counter()
    for fp in files:
        personas = load_json_any(Path(fp))
        for p in personas:
            genres = p.get("generi_preferiti") or []
            if not isinstance(genres, list):
                continue
            for g in genres:
                if isinstance(g, str) and g.strip():
                    counter[g.strip()] += 1
    return counter

def main():
    ap = argparse.ArgumentParser(
        description="Conta le ricorrenze dei generi (campo 'generi_preferiti') in uno o più file JSON."
    )
    ap.add_argument(
        "paths",
        nargs="*",
        help="File o directory JSON (es. profiles/personas.json istruttore.json oppure 'profiles/*.json')"
    )
    ap.add_argument("--top", type=int, default=None, help="Mostra solo i primi N generi")
    ap.add_argument("--csv", type=Path, default=None, help="Se specificato, salva anche l'output in CSV")
    args = ap.parse_args()

    # Se non passi percorsi, prova il default
    if not args.paths:
        if DEFAULT_FILE.exists():
            args.paths = [DEFAULT_FILE]
            print(f"⚠  Nessun percorso passato: uso il default {DEFAULT_FILE}")
        else:
            print("❌ Nessun percorso specificato e file di default non trovato.")
            sys.exit(1)

    paths = list(iter_input_paths(args.paths))
    if not paths:
        print("❌ Nessun file JSON trovato nei percorsi forniti.")
        sys.exit(1)

    try:
        counts = collect_genres(paths)
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)

    if not counts:
        print("ℹ️  Nessun genere trovato.")
        sys.exit(0)

    items = counts.most_common(args.top)

    # Stampa tabellare
    width = max(len(k) for k, _ in items)
    print(f"{'Genere'.ljust(width)}  Conteggio")
    print(f"{'-'*width}  ---------")
    for genre, c in items:
        print(f"{genre.ljust(width)}  {c}")

    if args.csv:
        try:
            import csv
            with args.csv.open("w", newline="", encoding="utf-8") as f:
                wr = csv.writer(f)
                wr.writerow(["genre", "count"])
                wr.writerows(items)
            print(f"\n✅ Salvato CSV: {args.csv}")
        except Exception as e:
            print(f"\n❌ Errore salvataggio CSV su {args.csv}: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
