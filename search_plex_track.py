import argparse
from plexapi.server import PlexServer

# Parse command-line arguments
parser = argparse.ArgumentParser(
    description="Search for a specific track and artist in Plex by navigating the artist-based library structure.",
    usage="python search_plex_track.py --plex-url PLEX_URL --plex-token PLEX_TOKEN --artist ARTIST_NAME --track TRACK_NAME"
)
parser.add_argument('--plex-url', required=True, help="Plex server URL (e.g., http://your-plex-server:32400)")
parser.add_argument('--plex-token', required=True, help="Plex authentication token")
parser.add_argument('--artist', required=True, help="Artist name to search for")
parser.add_argument('--track', required=True, help="Track name to search for")
parser.add_argument('--plex-library', default="Music", help="Plex library section name (default: Music)")
args = parser.parse_args()

# Initialize Plex server and library section
plex = PlexServer(args.plex_url, args.plex_token)
music_library = plex.library.section(args.plex_library)

# Search for the track by navigating artist -> album -> track
def search_track_by_artist_structure(artist_name, track_name):
    print(f"Searching for artist '{artist_name}'...")

    # Step 1: Search for artists and filter results to find exact matches or close matches
    artist_results = [
        artist for artist in music_library.search(title=artist_name)
        if artist.type == 'artist' and artist.title.lower() == artist_name.lower()
    ]

    # If exact match is not found, try finding a close match (substring)
    if not artist_results:
        artist_results = [
            artist for artist in music_library.search(title=artist_name)
            if artist.type == 'artist' and artist_name.lower() in artist.title.lower()
        ]
    
    if not artist_results:
        print(f"No results found for artist '{artist_name}'.")
        return
    
    print(f"Found {len(artist_results)} artist(s) matching '{artist_name}':")
    for artist in artist_results:
        print(f"  - {artist.title}")

    # Step 2: Search each album of the matching artists for the track
    for artist in artist_results:
        print(f"\nSearching albums for artist: {artist.title}")
        for album in artist.albums():
            print(f"  Searching in album: {album.title}")
            
            # Step 3: Search each track in the album
            for track in album.tracks():
                if track.title.lower() == track_name.lower():
                    print(f"    Match found: {track.title} in album '{album.title}' by '{artist.title}'")
                    return track
    
    print(f"No track named '{track_name}' found for artist '{artist_name}'.")

# Run the search
search_track_by_artist_structure(args.artist, args.track)
