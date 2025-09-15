# spotify_auth.py
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SCOPE

def get_spotify_user():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        show_dialog=True,
        cache_path=".cache"  # Salva il token di accesso
    ))


def get_spotify_public():
    return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    ))
