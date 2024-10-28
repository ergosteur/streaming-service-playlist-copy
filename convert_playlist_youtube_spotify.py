import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from ytmusicapi import YTMusic
from http.cookiejar import MozillaCookieJar
import argparse
import sys
import csv
import re
import time

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Sync YouTube Music playlist to Spotify.")
parser.add_argument('--yt-url', required=True, help="URL of the YouTube Music playlist to sync")
parser.add_argument('--cookies-path', default='cookies.txt', help="Path to Spotify cookies.txt file")
parser.add_argument('--yt-oauth-json', required=True, help="Path to YouTube Music OAuth JSON file")
parser.add_argument('--spotify-playlist-name', help="Name for the Spotify playlist")
parser.add_argument('--append', action='store_true', help="Append to existing Spotify playlist if it exists")
parser.add_argument('--replace', action='store_true', help="Replace the existing Spotify playlist if it exists")
parser.add_argument('--unmatched-output', help="File to save unmatched YouTube track details")
parser.add_argument('--unmatched-format', choices=['text', 'csv'], default='text', help="Format of unmatched output file")
parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose output for debugging")
args = parser.parse_args()

# Load YouTube Music API
ytmusic = YTMusic(args.yt_oauth_json)

# Function to extract YouTube playlist ID from URL
def parse_youtube_url(yt_url):
    match = re.search(r"list=([a-zA-Z0-9_-]+)", yt_url)
    if match:
        return match.group(1)
    else:
        sys.exit("Error: Invalid YouTube Music playlist URL.")

# Function to retrieve YouTube Music playlist tracks by ID
def get_youtube_playlist_tracks(yt_playlist_id):
    yt_tracks = []
    playlist_items = ytmusic.get_playlist(yt_playlist_id, limit=500)['tracks']
    for item in playlist_items:
        yt_tracks.append({
            'title': item['title'],
            'artist': item['artists'][0]['name'],
            'album': item.get('album', {}).get('name') if item.get('album') else None
        })
    if args.verbose:
        print(f"Retrieved {len(yt_tracks)} tracks from YouTube Music playlist with ID '{yt_playlist_id}'.")
    return yt_tracks

# Initialize Spotify API with cookie-based auth
def spotify_authenticate(cookies_path):
    token_url = 'https://open.spotify.com/get_access_token'
    cookie_jar = MozillaCookieJar(cookies_path)
    cookie_jar.load(ignore_discard=True, ignore_expires=True)
    response = requests.get(token_url, cookies=cookie_jar)
    if response.status_code == 200:
        return response.json().get('accessToken')
    else:
        sys.exit(f"Failed to retrieve Spotify access token: {response.status_code} - {response.text}")

# Search for a track on Spotify using title and artist (and album, if available)
def search_spotify_track(spotify, title, artist, album=None):
    query = f"{title} {artist}"
    if album:
        query += f" {album}"
    results = spotify.search(q=query, type='track', limit=1)
    tracks = results.get('tracks', {}).get('items', [])
    if tracks:
        return tracks[0]['id']
    return None

# Add tracks to Spotify playlist
def create_or_update_spotify_playlist(spotify, playlist_name, yt_tracks):
    # Check if playlist exists
    playlists = spotify.current_user_playlists()['items']
    existing_playlist = next((p for p in playlists if p['name'].lower() == playlist_name.lower()), None)
    
    # Create new playlist if not existing or replace is selected
    if existing_playlist:
        if args.replace:
            spotify.user_playlist_unfollow(spotify.me()['id'], existing_playlist['id'])
            existing_playlist = None
        elif args.append:
            print(f"Appending to existing Spotify playlist '{playlist_name}'.")
    
    if not existing_playlist:
        playlist = spotify.user_playlist_create(spotify.me()['id'], playlist_name, public=False)
        print(f"Created new Spotify playlist '{playlist_name}'.")
        playlist_id = playlist['id']
    else:
        playlist_id = existing_playlist['id']
    
    unmatched_tracks = []  # Track unmatched items
    track_ids_to_add = []

    for track in yt_tracks:
        spotify_track_id = search_spotify_track(spotify, track['title'], track['artist'], track['album'])
        if spotify_track_id:
            track_ids_to_add.append(spotify_track_id)
            if args.verbose:
                print(f"Added '{track['title']}' by '{track['artist']}' (Exact match)")
        else:
            unmatched_tracks.append(track)
            if args.verbose:
                print(f"No match found for '{track['title']}' by '{track['artist']}'")

    # Add tracks in batches of 100 (Spotify API limit)
    for i in range(0, len(track_ids_to_add), 100):
        spotify.playlist_add_items(playlist_id, track_ids_to_add[i:i+100])

    # Log unmatched tracks if specified
    if args.unmatched_output and unmatched_tracks:
        with open(args.unmatched_output, 'w', newline='') as f:
            if args.unmatched_format == 'csv':
                writer = csv.DictWriter(f, fieldnames=["title", "artist", "album"])
                writer.writeheader()
                writer.writerows(unmatched_tracks)
                print(f"Unmatched track details saved to {args.unmatched_output} in CSV format.")
            else:
                for track in unmatched_tracks:
                    f.write(f"{track['title']} - {track['artist']}\n")
                print(f"Unmatched track details saved to {args.unmatched_output} in text format.")

# Run the sync process
yt_playlist_id = parse_youtube_url(args.yt_url)
youtube_tracks = get_youtube_playlist_tracks(yt_playlist_id)
spotify_access_token = spotify_authenticate(args.cookies_path)
spotify = spotipy.Spotify(auth=spotify_access_token)
create_or_update_spotify_playlist(spotify, args.spotify_playlist_name or "YouTube Synced Playlist", youtube_tracks)
