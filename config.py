# config.py

import os

# credenziali lette da variabili d’ambiente
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8080/callback")
SCOPE = os.getenv(
    "SPOTIFY_SCOPE",
    "user-library-read playlist-read-private playlist-read-collaborative"
)
# Dizionario dei generi e delle relative playlist

GENERE_PLAYLIST = {
    "Pop": "0LIRHeEM4hvTLeaMl24cN2",               # Pop Rising (Spotify)
    "Pop italiano": "6ly6bwJeLhCvHQoEKOReLB",      # Hot Hits Italia (Spotify)
    "Rock": "1YYWoRa7CAOLox6SdzeVnL",              # Rock Classics (Spotify)
    "Rock italiano": "74XUtm9W6lMOp49GJV8EAa",     # Rock Italia (Spotify)
    "Alternative": [ "3yh8cGd3nxSevKHEsVE0TA",     # Alternative 10s (Spotify)
                     "6sKkUORUkw7Rx1Vw6tnaZU"     # Alternative 00s (Spotify)
                     ],
    "Dance": [ "01RfZu6FlRC4bE9zr2emdI",           # Dance Hits (Spotify)
               "7u85KJoQbptZ0NiPXpNKBZ"            # Dance Party (Spotify)
               ],
    "Disco": "1S2dCmQOidkat39fQvA8Nl",             # Disco Fever (Spotify)
    "Electro-pop": "0HakySAzvTDlseQXMoQQ1D",       # Electropop Experimental Mix (Spotify)
    "EDM": "23lnRnRpH7rQ1hMXF5VdET",               # EDM Hits (Spotify)
    "Techno": "1f6rj4MBfOcnmD556w4MWK",            # Techno Bunker (Spotify)
    "Tech-house": "5AU5LMrn0xiO4t3BjcBfVt",        # Tech House Mix (Spotify)
    "Tropical house": "32P4QMWAn2YEVSrzR9KzCa",    # Beach Tropical House Mix (Spotify)
    "Acid techno": "7A0PJ6KMVSZGALokxY2xGy",       # Acid Techno Mix (Spotify)
    "Hard trance": "0OAOgtD5y4aTN4hJuwuPUk",       # Hard Trance Mix (Spotify)
    "Reggaeton": "1snzyygERp2JBYQ9q8eFHI",         # Mix reggaeton (Spotify)
    "Latin": "0fD4fokduav63kMGUaZgV9",             # latincore (Spotify)
    "R&B": "2kzDEJl05lZ6ngGQwd3hhI",               # RNB X (Spotify)
    "Funk": "7oO7OUcP0arDhuSw8QRhuQ",              # Funk & Soul Classics (Spotify)
    "G-Funk": "7EtGlNWTPVO3QTbmnySm7Q",            # G-Funk - West Coast Oldschool Mix
    "Electro-funk": "3qiH93eAikX5ndeEZLK1zt",      # Electro Funk (Spotify)
    "Trap": "7qU2NOvI2temEGHI8k36EL",              # American Trap Mix (Spotify)
    "Trap francese": "1yiICZBiOiKAnzNg1RLaQf",     # French Trap Mix (Spotify)
    "Hip-hop": "7GP6vJoLDwbBZehwDCugUK",           # Global Hip-Hop (Spotify)
    "Rap Italiano": "5Q74gbNKdtyzwGqJ4SqCwc",      # Hit Rap Italiane (Spotify)
    "Indie elettronico": "0rkrKleUKHF7AlZgoxw6nW", # Avant Pop Meets Poptronica
    "Synthwave": "4rO3iTPbAsROUrVYxIx16C",         # Synthwave Mix (Spotify)
    "Ambient": "5QatLtmu0WjSZTmDhYSwue",           # Ambient Essentials
    "Downtempo": "6ozwWNwHi9K0eikGbZaudy",         # Downtempo Mix (Spotify)
    "Chillstep": "72KCEYMv6sayfKrCDa7BJC",         # Chillstep Mix (Spotify)
    "Italo-disco": "74VPHZTHwFAYi0uxfcwCKd",       # Italo Disco (Spotify)
    "Afro house": "1Dod7jVweAoJIYJJl6o3FF",        # Afro House Mix (Spotify)
    "Remix": "0AnqfnjV8lwh50aPpDFS1r",             # Remix Party 2025 (Spotify)
    "Folk": "48ieg2otOvhk19OMoCb7or",              # Mix Folk & Acustica (Spotify)
    "World Music": "2t5EGbUwuw4UGViiJDMe13",       # Top 50 Globale (Spotify)
    "Bossa nova": "3EZjnt0dLItYjWuXwmKhXu",        # Bossa Nova Classics (Spotify)
    "Jazz": "0IRbiwXRB5Xyk4InIaQGqB",              # Easy Jazz (Spotify)
    "Swing": "1cFvEObAcSMOTxDQrxjY82",             # Italian Swing Mix (Spotify)
    "Electro-swing": "6KE30UUG4PU5pOF0TdrgWY",     # Electro Swing Collection
    "Lounge": "226Y2jQjJfFO0cZspsspg0",            # Lounge Soft House (Spotify)
    "Commerciale": "6ly6bwJeLhCvHQoEKOReLB",       # Hot Hits Italia (Spotify)
    "Post-rock": "5Li9UcncOtV6M8GRXHcDXB",         # Post-Rock (Spotify)
    "Punk": "7KnsdkgJMabTY1WnboY0bx",              # Pure Pop Punk (Spotify)
    "Drum and bass" : "0PrMbVZ5oeWxKf7hIKjoaK",    # Drum and Bass Mix (Spotify)
    "Lo-fi beats": "1JkHNtbwCoukFz59Bvb1O1",       # lofi beats (Spotify)
    "Blues": "1qXOQSuCHd9HO9XvipK3Pk",             # Nu-Blue (Spotify)
    "Big room": "0AqPvAKUhkvbSvmNFs0IZU",          # Big Room 2025
    "Deep house": "4kfREUzGkWFGZ1NuvGXEMw",        # Deep House Mix (Spotify)
    "Britpop": "23Blh1tOdvsndbX87r0jvo",           # Britpop Mix (Spotify)
    "Neo-soul": "1l2vR5aFjTLb5bSxMtaIJU",          # Neo Soul Mix (Spotify)
    "Phonk": "3eX5OX6wOu17nFv3xVHN9Y",             # phonk (Spotify)
    "Musica italiana": "4bAH30CMtW6DpG1y5atHQy",   # MUSICA ITALIANA ANNI 90/2000
    "Jazz vocale": "3gCpSPIzrwSYIEU67wAZO3",       # Classic Voices in Jazz (Spotify)
    "Grunge": "2iNz4tBnzNAF55haYlq8oT",            # Grunge Mix (Spotify)
    "Disco funky": "1MmrYbhxWKJA3Fs4XqTIWx",       # Disco Funky Soul Mix (Spotify)
    "Berlin techno": "5GwdFmLFbnLawmoETWikV9",     # Berlin Techno Mix (Spotify)
    "Dance 2000": "0rOqzamDvbFQJHpMBSG843",        # Dance Anni 90 / 2000


    }



GENRE_TO_MACROGENRE = {
    "Pop": "Pop",
    "Pop italiano": "Pop",
    "Commerciale": "Pop",
    "Swing": "Swing",
    "Electro-swing": ["Swing", "Elettronica"],
    "Remix": "Elettronica",
    "Indie elettronico": ["Pop", "Elettronica"],
    "Electro-pop": ["Electropop", "Elettronica"],
    "Synthwave": "Synthwave",
    "Dance": "Dance",
    "Dance 2000": "Dance",
    "EDM": "Dance",
    "Big room": "Dance",
    "Deep house": "House",
    "Afro house": "House",
    "Tropical house": "House",
    "Tech-house": ["Techno", "House"],
    "Techno": "Techno",
    "Berlin techno": "Techno",
    "Acid techno": "Techno",
    "Hard trance": "Techno",
    "Disco": "Disco",
    "Italo-disco": "Disco",
    "Disco funky": ["Disco", "Funk"],
    "Funk": "Funk",
    "Electro-funk":  ["Funk", "Dance"],
    "Rock": "Rock",
    "Rock italiano": "Rock",
    "Post-rock": "Rock",
    "Britpop": "Rock",
    "Hip-hop": "Hip-Hop",
    "Rap Italiano": "Hip-Hop",
    "G-Funk": "Hip-Hop",
    "Trap": "Hip-Hop",
    "Trap francese": "Hip-Hop",
    "Latin": "Latin",
    "Reggaeton": "Latin",
    "Alternative": "Alternative",
    "Grunge": "Grunge",
    "Punk": "Punk",
    "Jazz": "Jazz",
    "Jazz vocale": "Jazz",
    "Lounge": "Lounge",
    "R&B": "R&B",
    "Neo-soul": "Soul",
    "Phonk": "Elettronica",
    "World Music": "World Music",
    "Bossa nova": "Bossa nova",
    "Ambient": "Chillstep",
    "Downtempo": "Chillstep",
    "Chillstep": "Chillstep",
    "Lo-fi beats": "Chillstep",
    "Musica italiana": "Musica italiana",
    "Folk": "Folk",
    "Drum and bass" : "Drum and bass",
    "Blues": "Blues"

}



# Percorso file personas
PERSONAS_PATH = "profiles/personas.json"
