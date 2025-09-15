Spinning Playlist Generator

Questo progetto genera playlist per lezioni di spinning bilanciando i gusti musicali dei partecipanti e le diverse fasi della lezione (warmup, flat, climb, sprint, cooldown).
Le playlist vengono create usando funzioni fuzzy e dati estratti da Spotify.

Avvio rapido

Clona il repository

```bash
git clone https://github.com/<tuo-utente>/spinning-playlist.git
cd spinning-playlist
```

Crea l’ambiente ed installa le dipendenze

```bash
pip install -r requirements.txt
```

Configura le credenziali Spotify

Copia il modello:

```bash
cp .env.example .env
```

Apri .env e inserisci i tuoi valori reali:

```bash
SPOTIFY_CLIENT_ID=tuo_client_id
SPOTIFY_CLIENT_SECRET=tuo_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:8080/callback
SPOTIFY_SCOPE="user-library-read playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private"
```

Il file .env è incluso nel .gitignore e non verrà caricato su GitHub.
Solo il modello .env.example rimane pubblico per mostrare quali variabili servono.

Esegui lo script principale

```bash
python main.py
```

Questo comando esegue l’intera pipeline: estrazione tracce, calcolo punteggi, generazione playlist.

Perché usare .env e os.getenv in config.py

Nel file config.py le credenziali Spotify (CLIENT_ID, CLIENT_SECRET, ecc.) non sono scritte in chiaro ma vengono lette tramite:

```bash
import os
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8080/callback")
```

Questa scelta garantisce:

Sicurezza – le credenziali reali restano solo nel file .env, che non viene mai caricato su GitHub.

Portabilità – ogni utente può inserire i propri valori senza modificare il codice.

Facilità di sviluppo – con la libreria python-dotenv le variabili vengono caricate automaticamente dal file .env quando il progetto è eseguito in locale.

Struttura del progetto

```bash
spinning-playlist/
│─ main.py             # esegue l'intera pipeline
│─ config.py           # legge le variabili da .env
│─ rank_playlist.py    # ranking in modalità democratica
│─ rank_instructor.py  # ranking con preferenze istruttore
│─ output/             # file generati (playlist, voti, statistiche)
│─ profiles/           # personas e istruttore (JSON)
│─ requirements.txt
│─ .env.example        # modello delle variabili
│─ .gitignore
```
