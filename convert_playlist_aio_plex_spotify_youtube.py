"""
convert_playlist_aio_plex_spotify_youtube.py

Version: 1.1
Date: 2024-10-28
Author: ergosteur (LLM assisted)
Github: https://github.com/ergosteur/streaming-service-playlist-copy

Description:
    This script syncs playlists between Spotify, YouTube Music, and Plex, supporting multiple directions (e.g., Spotify to Plex, Plex to YouTube Music).
    It handles playlist creation, updating, and duplicates, with options for exact or fuzzy album matching and conflict management.

Library Requirements:
    This script requires the following libraries:
        - requests
        - spotipy
        - ytmusicapi
        - plexapi

    To install these dependencies, run:
        pip install requests spotipy ytmusicapi plexapi
"""

import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from ytmusicapi import YTMusic
from plexapi.server import PlexServer
from http.cookiejar import MozillaCookieJar
import argparse
import sys
import csv
import re
import time

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Sync playlists between Spotify, YouTube Music, and Plex.")
parser.add_argument('--source-service', choices=['plex', 'spotify', 'ytmusic'], required=True, help="Source service: Spotify or YouTube Music")
parser.add_argument('--destination-service', choices=['plex', 'spotify', 'ytmusic'], required=True, help="Destination service: Plex, Spotify, or YouTube Music")
parser.add_argument('--playlist-url', help="URL of the source playlist")
parser.add_argument('--cookies-path', help="Path to cookies.txt file (for Spotify)")
parser.add_argument('--yt-oauth-json', help="Path to YouTube Music OAuth JSON file")
parser.add_argument('--plex-url', help="Plex server URL")
parser.add_argument('--plex-token', help="Plex authentication token")
parser.add_argument('--plex-library', default='Music', help="Plex library section name (default: Music)")
parser.add_argument('--playlist-name', help="Name for the destination playlist")
parser.add_argument('--append', action='store_true', help="Append to existing playlist if it exists")
parser.add_argument('--replace', action='store_true', help="Replace the existing playlist if it exists")
parser.add_argument('--unmatched-output', help="File to save unmatched track details")
parser.add_argument('--unmatched-format', choices=['text', 'csv'], default='text', help="Format of unmatched output file")
parser.add_argument('--force-album-match', choices=['exact', 'fuzzy'], help="Enforce exact or fuzzy album match for track matching")
parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose output for debugging")
args = parser.parse_args()

# Initialize services based on source and destination
ytmusic = YTMusic(args.yt_oauth_json) if 'ytmusic' in [args.source_service, args.destination_service] else None
plex = PlexServer(args.plex_url, args.plex_token) if 'plex' in [args.source_service, args.destination_service] else None
music_library = plex.library.section(args.plex_library) if 'plex' in [args.source_service, args.destination_service] else None

# Spotify authentication
def spotify_authenticate(cookies_path):
    if not cookies_path:
        sys.exit("Error: Cookies path is required for Spotify authentication.")
    # Proceed with authentication
    token_url = 'https://open.spotify.com/get_access_token'
    cookie_jar = MozillaCookieJar(cookies_path)
    cookie_jar.load(ignore_discard=True, ignore_expires=True)
    response = requests.get(token_url, cookies=cookie_jar)
    if response.status_code == 200:
        return response.json().get('accessToken')
    else:
        sys.exit(f"Failed to retrieve Spotify access token: {response.status_code} - {response.text}")


spotify_access_token = spotify_authenticate(args.cookies_path) if 'spotify' in [args.source_service, args.destination_service] else None
spotify = spotipy.Spotify(auth=spotify_access_token) if spotify_access_token else None

# Function to retrieve YouTube Music playlist tracks
def get_youtube_playlist_tracks(yt_playlist_url):
    yt_playlist_id = re.search(r"list=([a-zA-Z0-9_-]+)", yt_playlist_url).group(1)
    yt_tracks = []
    playlist_items = ytmusic.get_playlist(yt_playlist_id, limit=500)['tracks']
    for item in playlist_items:
        yt_tracks.append({
            'title': item['title'],
            'artist': item['artists'][0]['name'],
            'album': item.get('album', {}).get('name') if item.get('album') else None
        })
    return yt_tracks

# Function to retrieve Spotify playlist tracks
def get_spotify_playlist_tracks(spotify_url):
    spotify_id = re.search(r"playlist/([a-zA-Z0-9]+)", spotify_url).group(1)
    url = f'https://api.spotify.com/v1/playlists/{spotify_id}/tracks'
    headers = {'Authorization': f'Bearer {spotify_access_token}'}
    response = requests.get(url, headers=headers)
    return [
        {
            'title': item['track']['name'],
            'artist': item['track']['artists'][0]['name'],
            'album': item['track']['album']['name']
        }
        for item in response.json()['items']
    ]

# Function to retrieve Plex playlist tracks with connection check
def get_plex_playlist_tracks(playlist_name):
    if not plex:
        sys.exit("Error: Plex server not initialized. Please provide valid --plex-url and --plex-token.")
    
    # Retrieve specified Plex playlist
    plex_playlist = next((p for p in plex.playlists() if p.title.lower() == playlist_name.lower()), None)
    if not plex_playlist:
        sys.exit(f"Error: Playlist '{playlist_name}' not found on Plex.")
    
    plex_tracks = []
    for item in plex_playlist.items():
        if item.TYPE == "track":
            plex_tracks.append({
                'title': item.title,
                'artist': item.originalTitle or item.grandparentTitle,
                'album': item.parentTitle
            })
    if args.verbose:
        print(f"Retrieved {len(plex_tracks)} tracks from Plex playlist '{playlist_name}'.")
    return plex_tracks

# Function to add tracks to Spotify
def add_to_spotify_playlist(tracks):
    playlist_name = args.playlist_name or "Synced Playlist"
    playlists = spotify.current_user_playlists()['items']
    existing_playlist = next((p for p in playlists if p['name'].lower() == playlist_name.lower()), None)
    
    # Create or replace the playlist as necessary
    if existing_playlist and args.replace:
        spotify.user_playlist_unfollow(spotify.me()['id'], existing_playlist['id'])
        existing_playlist = None
    if not existing_playlist:
        playlist_id = spotify.user_playlist_create(spotify.me()['id'], playlist_name, public=False)['id']
        if args.verbose:
            print(f"Created new Spotify playlist '{playlist_name}'.")
    else:
        playlist_id = existing_playlist['id']
        if args.verbose:
            print(f"Using existing Spotify playlist '{playlist_name}' (ID: {playlist_id}).")

    unmatched_tracks = []

    # Add each track to the Spotify playlist
    for track in tracks:
        spotify_track_id = search_spotify_track(spotify, track['title'], track['artist'], track.get('album'))
        if spotify_track_id:
            spotify.playlist_add_items(playlist_id, [spotify_track_id])
            if args.verbose:
                print(f"Added '{track['title']}' by '{track['artist']}' to Spotify playlist.")
        else:
            unmatched_tracks.append(track)
            if args.verbose:
                print(f"No match found on Spotify for '{track['title']}' by '{track['artist']}'.")

    # Optionally output unmatched tracks
    if args.unmatched_output and unmatched_tracks:
        with open(args.unmatched_output, 'w', newline='') as f:
            if args.unmatched_format == 'csv':
                writer = csv.DictWriter(f, fieldnames=["title", "artist", "album"])
                writer.writeheader()
                writer.writerows(unmatched_tracks)
                if args.verbose:
                    print(f"Unmatched track details saved to {args.unmatched_output} in CSV format.")
            else:
                for track in unmatched_tracks:
                    f.write(f"{track['title']} - {track['artist']}\n")
                if args.verbose:
                    print(f"Unmatched track details saved to {args.unmatched_output} in text format.")


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

# Enhanced function to search for track by artist, album, and track title in Plex with exact or fuzzy album match
def find_track_in_plex(artist_name, track_name, album_name=None):
    # Search for the artist
    artist_results = [
        artist for artist in music_library.search(title=artist_name)
        if artist.type == 'artist' and artist.title.lower() == artist_name.lower()
    ]

    if not artist_results:
        # Fall back to searching for close matches if no exact match is found
        artist_results = [
            artist for artist in music_library.search(title=artist_name)
            if artist.type == 'artist' and artist_name.lower() in artist.title.lower()
        ]
    
    # If no artists are found, return None
    if not artist_results:
        print(f"No results found for artist '{artist_name}'.")
        return None

    # Step 1: Try to find a match based on force-album-match option (exact or fuzzy)
    for artist in artist_results:
        for album in artist.albums():
            if album_name:
                if args.force_album_match == 'exact' and album.title.lower() != album_name.lower():
                    continue  # Skip if exact match is required and titles don't match
                elif args.force_album_match == 'fuzzy' and album_name.lower() not in album.title.lower():
                    continue  # Skip if fuzzy match is required and title is not a substring

            for track in album.tracks():
                if track.title.lower() == track_name.lower():
                    print(f"Match found: {track.title} in album '{album.title}' by '{artist.title}'")
                    return track

    # Step 2: Fallback to double match (artist and track only, ignoring album) if no force-album-match is set
    if not args.force_album_match:
        for artist in artist_results:
            for album in artist.albums():
                for track in album.tracks():
                    if track.title.lower() == track_name.lower():
                        print(f"Partial match found (without album): {track.title} in album '{album.title}' by '{artist.title}'")
                        return track

    # If no matches are found, return None
    print(f"No track named '{track_name}' found for artist '{artist_name}' with the specified criteria.")
    return None

# Function to add tracks to Plex
def add_to_plex_playlist(tracks):
    playlist_name = args.playlist_name or "Synced Playlist"
    
    existing_playlist = plex.playlist(playlist_name) if playlist_name in [p.title for p in plex.playlists()] else None
    
    # Collect matched Plex tracks
    plex_tracks = []
    for track in tracks:
        plex_track = find_track_in_plex(track['artist'], track['title'], track.get('album'))
        if plex_track:
            plex_tracks.append(plex_track)
            if args.verbose:
                print(f"Match found for '{track['title']}' by '{track['artist']}'")


    # Only create or update playlist if there are items to add
    if not plex_tracks:
        print("No matching tracks found in Plex to add to the playlist.")
        return

    # Handle playlist creation or update
    if existing_playlist:
        if args.replace:
            existing_playlist.delete()
            existing_playlist = None
        elif args.append:
            print(f"Appending to existing Plex playlist '{playlist_name}'.")
            existing_playlist.addItems(plex_tracks)
            return

    # Create a new playlist with matched items
    plex.createPlaylist(playlist_name, items=plex_tracks)
    print(f"Plex playlist '{playlist_name}' created with {len(plex_tracks)} tracks.")

# Function to add tracks to YouTube Music with conflict handling and duplicate checking
def add_to_youtube_playlist(tracks):
    playlist_name = args.playlist_name or "Synced Playlist"
    playlist_description = ""
    # Check for existing playlists on YouTube Music
    existing_playlists = ytmusic.get_library_playlists()
    existing_playlist = next((p for p in existing_playlists if p['title'].lower() == playlist_name.lower()), None)
    
    # Create or update the playlist
    if existing_playlist:
        if args.replace:
            ytmusic.delete_playlist(existing_playlist['playlistId'])
            if args.verbose:
                print(f"Replaced existing YouTube Music playlist '{playlist_name}'.")
            if 'plex' in [args.source_service]:
                playlist_description = "Synced from Plex"
            elif 'spotify' in [args.source_service]:
                playlist_description = "Synced from Spotify"
            playlist_id = ytmusic.create_playlist(playlist_name, playlist_description)
        elif args.append:
            if args.verbose:
                print(f"Appending to existing YouTube Music playlist '{playlist_name}'.")
            playlist_id = existing_playlist['playlistId']
        else:
            sys.exit(f"Playlist '{playlist_name}' already exists on YouTube Music. Use --append or --replace to modify.")
    else:
        if 'plex' in [args.source_service]:
                playlist_description = "Synced from Plex"
        elif 'spotify' in [args.source_service]:
                playlist_description = "Synced from Spotify"
        playlist_id = ytmusic.create_playlist(playlist_name, playlist_description)
        if args.verbose:
            print(f"Created new YouTube Music playlist '{playlist_name}'.")

    unmatched_tracks = []  # Track unmatched items

    # Get current tracks to prevent duplicates
    existing_track_ids = set()
    if existing_playlist:
        existing_items = ytmusic.get_playlist(playlist_id, limit=500)['tracks']
        existing_track_ids.update(item['videoId'] for item in existing_items)

    # Search for each track on YouTube Music and add it if not a duplicate
    for track in tracks:
        search_query = f"{track['title']} {track['artist']}"
        search_results = ytmusic.search(search_query, filter="songs")
        
        if search_results:
            yt_track_id = search_results[0]['videoId']
            
            # Check for duplicate track
            if yt_track_id in existing_track_ids:
                if args.verbose:
                    print(f"Track '{track['title']}' already exists in the playlist. Skipping.")
                continue
            
            # Attempt to add the track, with retry handling
            try:
                ytmusic.add_playlist_items(playlist_id, [yt_track_id])
                existing_track_ids.add(yt_track_id)
                if args.verbose:
                    print(f"Added '{track['title']}' by '{track['artist']}' to YouTube Music playlist.")
            except Exception as e:
                print(f"Error adding track '{track['title']}': {e}. Retrying after delay.")
                time.sleep(2)  # Brief pause before retrying
                try:
                    ytmusic.add_playlist_items(playlist_id, [yt_track_id])
                    existing_track_ids.add(yt_track_id)
                    if args.verbose:
                        print(f"Added '{track['title']}' by '{track['artist']}' (Retry)")
                except Exception as retry_e:
                    print(f"Failed again on '{track['title']}'. Skipping this track.")
                    unmatched_tracks.append(track)
        else:
            if args.verbose:
                print(f"No match found on YouTube Music for '{track['title']}' by '{track['artist']}'")
            unmatched_tracks.append(track)

    # Save unmatched track details if specified
    if args.unmatched_output and unmatched_tracks:
        with open(args.unmatched_output, 'w', newline='') as f:
            if args.unmatched_format == 'csv':
                writer = csv.DictWriter(f, fieldnames=["title", "artist", "album"])
                writer.writeheader()
                writer.writerows(unmatched_tracks)
                if args.verbose:
                    print(f"Unmatched track details saved to {args.unmatched_output} in CSV format.")
            else:
                for track in unmatched_tracks:
                    f.write(f"{track['title']} - {track['artist']}\n")
                if args.verbose:
                    print(f"Unmatched track details saved to {args.unmatched_output} in text format.")




# Main execution logic
if args.source_service == 'spotify' and args.destination_service == 'ytmusic':
    tracks = get_spotify_playlist_tracks(args.playlist_url)
    add_to_youtube_playlist(tracks)
elif args.source_service == 'spotify' and args.destination_service == 'plex':
    tracks = get_spotify_playlist_tracks(args.playlist_url)
    add_to_plex_playlist(tracks)
elif args.source_service == 'ytmusic' and args.destination_service == 'spotify':
    tracks = get_youtube_playlist_tracks(args.playlist_url)
    add_to_spotify_playlist(tracks)
elif args.source_service == 'ytmusic' and args.destination_service == 'plex':
    tracks = get_youtube_playlist_tracks(args.playlist_url)
    add_to_plex_playlist(tracks)
elif args.source_service == 'plex' and args.destination_service == 'spotify':
    tracks = get_plex_playlist_tracks(args.playlist_name)
    add_to_spotify_playlist(tracks)
elif args.source_service == 'plex' and args.destination_service == 'ytmusic':
    tracks = get_plex_playlist_tracks(args.playlist_name)
    add_to_youtube_playlist(tracks)
else:
    sys.exit("Error: Unsupported source-destination combination.")
