import requests
from plexapi.server import PlexServer
from http.cookiejar import MozillaCookieJar
import argparse
import sys
import csv
import re

# Define default values here
DEFAULT_PLEX_URL = 'http://YOUR_PLEX_SERVER_IP:32400'  # Replace with your Plex server URL
DEFAULT_PLEX_TOKEN = 'YOUR_PLEX_TOKEN'
DEFAULT_PLAYLIST_NAME = 'My Spotify Playlist'
DEFAULT_COOKIES_PATH = 'cookies.txt'
DEFAULT_PLEX_LIBRARY = 'Music'  # Default library section

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Sync Spotify playlist or album to Plex.")
parser.add_argument('--plex-url', default=DEFAULT_PLEX_URL, help="Plex server URL (default: set in script)")
parser.add_argument('--plex-token', default=DEFAULT_PLEX_TOKEN, help="Plex authentication token (default: set in script)")
parser.add_argument('--playlist-name', default=DEFAULT_PLAYLIST_NAME, help="Name for the Plex playlist (default: set in script)")
parser.add_argument('--spotify-url', required=True, help="Spotify URL for a playlist or album")
parser.add_argument('--cookies-path', default=DEFAULT_COOKIES_PATH, help="Path to Spotify cookies.txt file (default: set in script)")
parser.add_argument('--plex-library', default=DEFAULT_PLEX_LIBRARY, help="Plex library section name (default: Music)")
parser.add_argument('--append', action='store_true', help="Append to the existing Plex playlist if it exists")
parser.add_argument('--replace', action='store_true', help="Replace the existing Plex playlist if it exists")
parser.add_argument('--unmatched-output', help="File to save unmatched Spotify track URLs")
parser.add_argument('--unmatched-format', choices=['text', 'csv'], default='text', help="Format of unmatched output file (text or csv, default: text)")
parser.add_argument('--force-album-match', choices=['exact', 'fuzzy'], help="Enforce exact or fuzzy album match for track matching in Plex")
args = parser.parse_args()

# Validate that only one of --append or --replace is set
if args.append and args.replace:
    sys.exit("Error: Specify only one of --append or --replace.")

# Initialize Plex server and library section
plex = PlexServer(args.plex_url, args.plex_token)
music_library = plex.library.section(args.plex_library)

# Load cookies from the specified path
cookie_jar = MozillaCookieJar(args.cookies_path)
cookie_jar.load(ignore_discard=True, ignore_expires=True)

# Function to determine Spotify type and extract ID
def parse_spotify_url(spotify_url):
    match = re.search(r"open\.spotify\.com/(album|playlist)/([a-zA-Z0-9]+)", spotify_url)
    if match:
        spotify_type = match.group(1)
        spotify_id = match.group(2)
        return spotify_type, spotify_id
    else:
        print("Error: Unsupported Spotify URL. Please provide a valid album or playlist URL.")
        sys.exit()

# Function to get Spotify access token
def get_spotify_access_token():
    token_url = 'https://open.spotify.com/get_access_token'
    response = requests.get(token_url, cookies=cookie_jar)
    if response.status_code == 200:
        return response.json().get('accessToken')
    else:
        print(f"Failed to retrieve access token: {response.status_code} - {response.text}")
        return None

# Function to get Spotify tracks from either a playlist or an album
def get_spotify_tracks(spotify_id, spotify_type):
    access_token = get_spotify_access_token()
    if not access_token:
        exit("Unable to retrieve Spotify access token.")

    # API URLs for playlist and album
    url = f'https://api.spotify.com/v1/{spotify_type}s/{spotify_id}/tracks'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to retrieve {spotify_type}: {response.status_code} - {response.text}")
        return []

    tracks = response.json()['items']

    if spotify_type == 'playlist':
        # For playlists, extract track details directly
        return [(track['track']['name'], track['track']['artists'][0]['name'], track['track']['album']['name'], track['track']['external_urls']['spotify']) for track in tracks]
    elif spotify_type == 'album':
        # For albums, get the album name separately
        album_info_url = f'https://api.spotify.com/v1/albums/{spotify_id}'
        album_info_response = requests.get(album_info_url, headers=headers)
        
        if album_info_response.status_code == 200:
            album_name = album_info_response.json()['name']
            return [(track['name'], track['artists'][0]['name'], album_name, track['external_urls']['spotify']) for track in tracks]
        else:
            print(f"Failed to retrieve album information: {album_info_response.status_code} - {album_info_response.text}")
            return []

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

# Function to create or update a Plex playlist based on specified behavior
def create_or_update_plex_playlist(playlist_name, spotify_tracks):
    # Check if playlist already exists
    existing_playlist = plex.playlist(playlist_name) if playlist_name in [p.title for p in plex.playlists()] else None

    # Handle existing playlist based on options
    if existing_playlist:
        if args.append:
            print(f"Appending to existing playlist '{playlist_name}'.")
            existing_tracks = existing_playlist.items()
            plex_tracks = [track for track in existing_tracks]  # Start with current tracks

        elif args.replace:
            print(f"Replacing existing playlist '{playlist_name}'.")
            existing_playlist.delete()
            plex_tracks = []  # Start fresh for replacement

        else:
            sys.exit(f"Warning: Playlist '{playlist_name}' already exists. Specify --append or --replace to proceed.")
    else:
        plex_tracks = []  # Start with an empty list for new playlist

    unmatched_tracks = []  # List to store data of unmatched tracks

    # Search and add matching tracks from Spotify playlist
    for track_name, artist_name, album_name, spotify_url in spotify_tracks:
        plex_track = find_track_in_plex(artist_name, track_name, album_name)
        if plex_track:
            plex_tracks.append(plex_track)
        else:
            print(f"No match found for '{track_name}' by '{artist_name}'. Adding to unmatched list.")
            unmatched_tracks.append({
                "track_name": track_name,
                "artist_name": artist_name,
                "album_name": album_name,
                "spotify_url": spotify_url
            })
    
    # Create or update the playlist in Plex
    if plex_tracks:
        if existing_playlist and args.append:
            # Add tracks to existing playlist
            existing_playlist.addItems(plex_tracks)
        else:
            # Create a new playlist
            plex.createPlaylist(playlist_name, items=plex_tracks)
        print(f"Plex playlist '{playlist_name}' updated successfully with {len(plex_tracks)} tracks.")
    else:
        print("No matching tracks found in Plex.")

    # Output unmatched tracks based on format specified
    if args.unmatched_output and unmatched_tracks:
        with open(args.unmatched_output, 'w', newline='') as f:
            if args.unmatched_format == 'csv':
                writer = csv.DictWriter(f, fieldnames=["artist_name", "track_name", "album_name", "spotify_url"])
                writer.writeheader()
                writer.writerows(unmatched_tracks)
                print(f"Unmatched Spotify track details saved to {args.unmatched_output} in CSV format.")
            else:
                for track in unmatched_tracks:
                    f.write(track["spotify_url"] + '\n')
                print(f"Unmatched Spotify track URLs saved to {args.unmatched_output} in text format.")

# Determine Spotify type and ID
spotify_type, spotify_id = parse_spotify_url(args.spotify_url)

# Fetch Spotify tracks and create or update Plex playlist
spotify_tracks = get_spotify_tracks(spotify_id, spotify_type)
create_or_update_plex_playlist(args.playlist_name, spotify_tracks)
