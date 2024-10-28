import requests
from ytmusicapi import YTMusic
from http.cookiejar import MozillaCookieJar
import argparse
import sys
import csv
import re
import time

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Sync Spotify playlist to YouTube Music.")
parser.add_argument('--spotify-url', required=True, help="Spotify URL for a playlist")
parser.add_argument('--cookies-path', default='cookies.txt', help="Path to Spotify cookies.txt file")
parser.add_argument('--yt-oauth-json', required=True, help="Path to YouTube Music OAuth JSON file")
parser.add_argument('--playlist-name', help="Name for the YouTube Music playlist")
parser.add_argument('--append', action='store_true', help="Append to existing YouTube playlist if it exists")
parser.add_argument('--replace', action='store_true', help="Replace the existing YouTube playlist if it exists")
parser.add_argument('--unmatched-output', help="File to save unmatched Spotify track URLs")
parser.add_argument('--unmatched-format', choices=['text', 'csv'], default='text', help="Format of unmatched output file")
parser.add_argument('--force-album-match', choices=['exact', 'fuzzy'], help="Enforce exact or fuzzy album match for track matching")
parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose output for debugging")
args = parser.parse_args()

# Load Spotify cookies
cookie_jar = MozillaCookieJar(args.cookies_path)
cookie_jar.load(ignore_discard=True, ignore_expires=True)

# Function to extract Spotify playlist ID
def parse_spotify_url(spotify_url):
    match = re.search(r"open\.spotify\.com/playlist/([a-zA-Z0-9]+)", spotify_url)
    if match:
        return match.group(1)
    else:
        sys.exit("Error: Invalid Spotify playlist URL.")

# Function to get Spotify access token
def get_spotify_access_token():
    token_url = 'https://open.spotify.com/get_access_token'
    response = requests.get(token_url, cookies=cookie_jar)
    if response.status_code == 200:
        return response.json().get('accessToken')
    else:
        print(f"Failed to retrieve access token: {response.status_code} - {response.text}")
        return None

# Function to get Spotify playlist tracks
def get_spotify_tracks(spotify_id):
    access_token = get_spotify_access_token()
    if not access_token:
        exit("Unable to retrieve Spotify access token.")

    url = f'https://api.spotify.com/v1/playlists/{spotify_id}/tracks'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to retrieve playlist: {response.status_code} - {response.text}")
        return []

    return [
        {
            'title': track['track']['name'],
            'artist': track['track']['artists'][0]['name'],
            'album': track['track']['album']['name']
        }
        for track in response.json()['items']
    ]

# Load YouTube Music API
ytmusic = YTMusic(args.yt_oauth_json)

# Function to find or create YouTube Music playlist and add tracks
def create_or_update_yt_playlist(playlist_name, spotify_tracks):
    existing_playlist = None
    
    # Check if playlist exists
    playlists = ytmusic.get_library_playlists()
    for playlist in playlists:
        if playlist['title'].lower() == playlist_name.lower():
            existing_playlist = playlist
            break
    
    if existing_playlist:
        if args.replace:
            ytmusic.delete_playlist(existing_playlist['playlistId'])
            existing_playlist = None  # Reset to create a new playlist
        elif args.append:
            if args.verbose:
                print(f"Appending to existing YouTube playlist '{playlist_name}'.")
    
    # Create new playlist if not existing or replaced
    if not existing_playlist:
        playlist_id = ytmusic.create_playlist(playlist_name, "Synced from Spotify")
        if args.verbose:
            print(f"Created new YouTube playlist '{playlist_name}'.")
    else:
        playlist_id = existing_playlist['playlistId']
    
    unmatched_tracks = []  # Track unmatched items

    # Retrieve current tracks in the playlist to avoid duplicates
    existing_track_ids = set()
    if existing_playlist:
        existing_items = ytmusic.get_playlist(playlist_id, limit=500)['tracks']
        existing_track_ids.update(item['videoId'] for item in existing_items)

    # Search and add each Spotify track to YouTube playlist
    for track in spotify_tracks:
        search_query = f"{track['title']} {track['artist']}"
        search_results = ytmusic.search(search_query, filter="songs")
        
        if search_results:
            yt_track_id = search_results[0]['videoId']
            
            # Check if track already exists to avoid duplicates
            if yt_track_id in existing_track_ids:
                if args.verbose:
                    print(f"Track '{track['title']}' already exists in the playlist. Skipping.")
                continue
            
            # Attempt to add the track, with error handling
            try:
                ytmusic.add_playlist_items(playlist_id, [yt_track_id])
                existing_track_ids.add(yt_track_id)  # Update set with added track ID
                if args.verbose:
                    print(f"Added '{track['title']}' by '{track['artist']}' (Exact match)")
            except Exception as e:
                print(f"Error adding track '{track['title']}': {e}. Retrying after delay.")
                time.sleep(2)  # Wait before retrying
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
                print(f"No match found for '{track['title']}' by '{track['artist']}'")
            unmatched_tracks.append(track)

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

# Run the sync
spotify_id = parse_spotify_url(args.spotify_url)
spotify_tracks = get_spotify_tracks(spotify_id)
create_or_update_yt_playlist(args.playlist_name or "My Synced Playlist", spotify_tracks)
