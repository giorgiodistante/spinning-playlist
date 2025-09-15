"""
   extract_tracks.py
"""


import json
import random
import re
from pathlib import Path

import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth

import config

# Config percorsi

FAVORITES_PATH = Path("output/brani_preferiti.json")
RANGES_CSV     = Path("Feature_Ranges_Espansi.csv")
OUTPUT_PATH    = Path("output/tracks_by_genre.json")


# Autenticazione Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=config.CLIENT_ID,
    client_secret=config.CLIENT_SECRET,
    redirect_uri=config.REDIRECT_URI,
    scope=config.SCOPE
))

# Carica i range per genere (CSV)
def _to_pair(s):
    s = str(s).strip().strip("()").replace(" ", "")
    a, b = s.split(",")
    return float(a), float(b)

try:
    df_ranges = pd.read_csv(RANGES_CSV)
except Exception as e:
    raise SystemExit(f"❌ Impossibile leggere {RANGES_CSV}: {e}")

range_dict = {}
for _, row in df_ranges.iterrows():
    try:
        g = row['Genere']
        range_dict[g] = {
            'bpm':          _to_pair(row['BPM']),
            'danceability': _to_pair(row['Danceability']),
            'valence':      _to_pair(row['Valence']),
        }
    except Exception:
        # Se per un genere manca qualcosa, lo saltiamo
        continue

# Util
def generate_feature_value(low, high):
    return round(random.uniform(low, high), 3)

_BASE62 = re.compile(r'^[A-Za-z0-9]+$')
def is_valid_playlist_id(pid: str) -> bool:
    return isinstance(pid, str) and len(pid) >= 10 and len(pid) <= 40 and bool(_BASE62.match(pid))

# Dizionario genere → playlist Spotify (ID o lista di ID)
genre_playlists = {
    "Pop": "0LIRHeEM4hvTLeaMl24cN2",
    "Pop italiano": "6ly6bwJeLhCvHQoEKOReLB",
    "Rock": "1YYWoRa7CAOLox6SdzeVnL",
    "Rock italiano": "74XUtm9W6lMOp49GJV8EAa",
    "Alternative": ["3yh8cGd3nxSevKHEsVE0TA", "6sKkUORUkw7Rx1Vw6tnaZU"],
    "Dance": ["01RfZu6FlRC4bE9zr2emdI", "7u85KJoQbptZ0NiPXpNKBZ"],
    "Disco": "1S2dCmQOidkat39fQvA8Nl",
    "Electro-pop": "0HakySAzvTDlseQXMoQQ1D",
    "EDM": "23lnRnRpH7rQ1hMXF5VdET",
    "Techno": "1f6rj4MBfOcnmD556w4MWK",
    "Tech-house": "5AU5LMrn0xiO4t3BjcBfVt",
    "Tropical house": "32P4QMWAn2YEVSrzR9KzCa",
    "Acid techno": "7A0PJ6KMVSZGALokxY2xGy",
    "Hard trance": "0OAOgtD5y4aTN4hJuwuPUk",
    "Reggaeton": "1snzyygERp2JBYQ9q8eFHI",
    "Latin": "0fD4fokduav63kMGUaZgV9",
    "R&B": "2kzDEJl05lZ6ngGQwd3hhI",
    "Funk": "7oO7OUcP0arDhuSw8QRhuQ",
    "G-Funk": "7EtGlNWTPVO3QTbmnySm7Q",
    "Electro-funk": "3qiH93eAikX5ndeEZLK1zt",
    "Trap": "7qU2NOvI2temEGHI8k36EL",
    "Trap francese": "1yiICZBiOiKAnzNg1RLaQf",
    "Hip-hop": "7GP6vJoLDwbBZehwDCugUK",
    "Rap Italiano": "5Q74gbNKdtyzwGqJ4SqCwc",
    "Indie elettronico": "0rkrKleUKHF7AlZgoxw6nW",
    "Synthwave": "4rO3iTPbAsROUrVYxIx16C",
    "Ambient": "5QatLtmu0WjSZTmDhYSwue",
    "Downtempo": "6ozwWNwHi9K0eikGbZaudy",
    "Chillstep": "72KCEYMv6sayfKrCDa7BJC",
    "Italo-disco": "74VPHZTHwFAYi0uxfcwCKd",
    "Afro house": "1Dod7jVweAoJIYJJl6o3FF",
    "Remix": "0AnqfnjV8lwh50aPpDFS1r",
    "Folk": "48ieg2otOvhk19OMoCb7or",
    "World Music": "2t5EGbUwuw4UGViiJDMe13",
    "Bossa nova": "3EZjnt0dLItYjWuXwmKhXu",
    "Jazz": "0IRbiwXRB5Xyk4InIaQGqB",
    "Swing": "1cFvEObAcSMOTxDQrxjY82",
    "Electro-swing": "6KE30UUG4PU5pOF0TdrgWY",
    "Lounge": "226Y2jQjJfFO0cZspsspg0",
    "Commerciale": "6ly6bwJeLhCvHQoEKOReLB",
    "Post-rock": "5Li9UcncOtV6M8GRXHcDXB",
    "Punk": "7KnsdkgJMabTY1WnboY0bx",
    "Drum and bass": "0PrMbVZ5oeWxKf7hIKjoaK",
    "Lo-fi beats": "1JkHNtbwCoukFz59Bvb1O1",
    "Blues": "1qXOQSuCHd9HO9XvipK3Pk",
    "Big room": "0AqPvAKUhkvbSvmNFs0IZU",
    "Deep house": "4kfREUzGkWFGZ1NuvGXEMw",
    "Britpop": "23Blh1tOdvsndbX87r0jvo",
    "Neo-soul": "1l2vR5aFjTLb5bSxMtaIJU",
    "Phonk": "3eX5OX6wOu17nFv3xVHN9Y",
    "Musica italiana": "4bAH30CMtW6DpG1y5atHQy",
    "Jazz vocale": "3gCpSPIzrwSYIEU67wAZO3",
    "Grunge": "2iNz4tBnzNAF55haYlq8oT",
    "Disco funky": "1MmrYbhxWKJA3Fs4XqTIWx",
    "Berlin techno": "5GwdFmLFbnLawmoETWikV9",
    "Dance 2000": "0rOqzamDvbFQJHpMBSG843",
}

# Output containers
output = []
seen_ids = set()

# Fase 1 — Aggiunta PREFERITI
def load_favorites(path: Path):
    if not path.exists():
        print(f"ℹ️  Nessun file di preferiti trovato: {path} (skip)")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Errore nel parsing di {path}: {e}")
        return {}

favorites_map = load_favorites(FAVORITES_PATH)

fav_candidates = []  # (person_name, fav_obj)
if isinstance(favorites_map, dict):
    for person, items in favorites_map.items():
        if not isinstance(items, list) or not items:
            continue
        random.shuffle(items)
        fav_candidates.append((person, items[0]))  # max 1 per persona
elif isinstance(favorites_map, list):
    random.shuffle(favorites_map)
    for fav in favorites_map[:10]:
        fav_candidates.append(("anon", fav))

random.shuffle(fav_candidates)
fav_selected = fav_candidates[:10]  # cap 10 totali

added_favs = 0
fav_added_list = []
fav_skipped = []

for person, fav in fav_selected:
    try:
        title = fav.get("title")
        artist = fav.get("artist")
        genre  = fav.get("genre")
        sid    = fav.get("spotify_id") or fav.get("id")

        if not sid:
            fav_skipped.append((person, title or "?", "manca spotify_id"))
            continue
        if sid in seen_ids:
            fav_skipped.append((person, title or "?", "duplicato"))
            continue
        if genre not in range_dict:
            fav_skipped.append((person, title or "?", f"genere assente nei range: {genre}"))
            continue

        features = range_dict[genre]
        # Preferiti PRIMA e ben marcati
        output.append({
            "title": title,
            "note": f"## BRANO PREFERITO DI {person}",
            "artist": artist,
            "genre": genre,
            "id": sid,
            "bpm": generate_feature_value(*features["bpm"]),
            "danceability": generate_feature_value(*features["danceability"]),
            "valence": generate_feature_value(*features["valence"])
        })
        seen_ids.add(sid)
        fav_added_list.append((person, title or "?", genre))
        added_favs += 1
    except Exception as e:
        fav_skipped.append((person, fav.get("title","?"), f"errore: {e}"))

# Fase 2 — Raccolta dalle PLAYLIS
for genre, playlists in genre_playlists.items():
    pl_list = playlists if isinstance(playlists, list) else [playlists]

    for playlist_id in pl_list:
        if not is_valid_playlist_id(playlist_id):
            print(f"⚠️  Playlist ID non valido (skip): {playlist_id} (genere: {genre})")
            continue
        try:
            results = sp.playlist_tracks(playlist_id, limit=100)
            items = results.get('items', []) or []
            random.shuffle(items)
            selected = items[:20]  # pick fino a 20 per playlist

            for track in selected:
                try:
                    t = track.get('track') or {}
                    tid = t.get('id')
                    if not tid or tid in seen_ids:
                        continue
                    if genre not in range_dict:
                        continue
                    features = range_dict[genre]

                    track_info = {
                        "title": t.get('name'),
                        "artist": (t.get('artists') or [{}])[0].get('name'),
                        "genre": genre,
                        "id": tid,
                        "bpm": generate_feature_value(*features["bpm"]),
                        "danceability": generate_feature_value(*features["danceability"]),
                        "valence": generate_feature_value(*features["valence"]),
                    }
                    output.append(track_info)
                    seen_ids.add(tid)
                except Exception:
                    continue

        except Exception as e:
            print(f"❌ Errore nella playlist {playlist_id}: {e}")

# Log finale + salvataggio
if fav_added_list:
    print("\n⭐ Preferiti inseriti (in testa al file):")
    for who, title, genre in fav_added_list:
        print(f"  - {title}  [{genre}]  — di {who}")

if fav_skipped:
    print("\nℹ️ Preferiti saltati:")
    for who, title, reason in fav_skipped:
        print(f"  - {title} — di {who}  → {reason}")

print(f"\n🎯 Aggiunti {added_favs} brani da brani_preferiti.profiles (max 1 per persona, max 10 totali)")
print(f"📦 Totale brani raccolti: {len(output)}")

with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ Salvato: {OUTPUT_PATH}")
