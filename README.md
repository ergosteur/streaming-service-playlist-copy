
# convert_playlist_aio_plex_spotify_youtube.py

**Version:** 1.1  
**Date:** 2024-10-28  
**Author:** ergo

## Description
`convert_playlist_aio_plex_spotify_youtube.py` is a versatile Python script designed to sync playlists between Spotify, YouTube Music, and Plex. It supports multiple sync directions (e.g., Spotify to Plex, Plex to YouTube Music) with options for exact or fuzzy album matching and conflict management, preventing duplicate additions. The script can create new playlists or update existing ones, handling various platform-specific quirks seamlessly.

## Library Requirements
This script depends on the following libraries:
- `requests`
- `spotipy`
- `ytmusicapi`
- `plexapi`

Install these dependencies with:
```bash
pip install requests spotipy ytmusicapi plexapi
```

## Usage
The script requires several command-line arguments to specify the source and destination services, playlist details, and other options.

### Command-line Arguments
- `--source-service` (required): Source platform for the playlist (`spotify`, `ytmusic`, or `plex`).
- `--destination-service` (required): Destination platform for the playlist (`plex`, `spotify`, or `ytmusic`).
- `--playlist-url` (optional): URL of the source playlist (required only for Spotify and YouTube Music).
- `--playlist-name`: Name of the destination playlist.
- `--cookies-path`: Path to `cookies.txt` for Spotify API access.
- `--yt-oauth-json`: Path to YouTube Music OAuth JSON file.
- `--plex-url`: URL of your Plex server.
- `--plex-token`: Plex authentication token.
- `--append`: Append to an existing playlist (if it exists).
- `--replace`: Replace an existing playlist (if it exists).
- `--unmatched-output`: Path to save unmatched track details.
- `--unmatched-format`: Format of the unmatched output file (`text` or `csv`, default is `text`).
- `--verbose` or `-v`: Enable verbose output for detailed feedback.

### Generating Required Files

#### `cookies.txt` for Spotify Authentication
1. **Download and Install**: Use the browser extension [Get cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt/) for Chrome or Firefox to export your cookies.
2. **Login to Spotify**: Open Spotify in your browser and log in to your account.
3. **Export cookies**: Click the extension icon and export cookies from the `open.spotify.com` domain. Save the file as `cookies.txt` in the desired location.
4. **Use `--cookies-path`**: Specify the path to this file using the `--cookies-path` argument.

#### `oauth.json` for YouTube Music Authentication
1. **Install `ytmusicapi` CLI**: Run the following command:
   ```bash
   python -m ytmusicapi oauth
   ```
2. **Follow the Authentication Process**: This command will open a browser for Google account authentication. Follow the steps to grant `ytmusicapi` access.
3. **Save the File**: After successful authentication, an `oauth.json` file will be created. Use this file as the path for the `--yt-oauth-json` argument.

### Example Use Cases

#### Sync Spotify to YouTube Music
```bash
python convert_playlist_aio_plex_spotify_youtube.py --source-service spotify --destination-service ytmusic --playlist-url "https://open.spotify.com/playlist/your_spotify_playlist_id" --yt-oauth-json path/to/ytmusic_oauth.json --playlist-name "Synced Playlist" --verbose
```

#### Sync Spotify to Plex
```bash
python convert_playlist_aio_plex_spotify_youtube.py --source-service spotify --destination-service plex --playlist-url "https://open.spotify.com/playlist/your_spotify_playlist_id" --plex-url "http://your_plex_server:32400" --plex-token "your_plex_token" --playlist-name "Synced Playlist" --verbose
```

#### Sync YouTube Music to Spotify
```bash
python convert_playlist_aio_plex_spotify_youtube.py --source-service ytmusic --destination-service spotify --playlist-url "https://music.youtube.com/playlist?list=your_ytmusic_playlist_id" --cookies-path path/to/spotify_cookies.txt --playlist-name "Synced Playlist" --verbose
```

#### Sync YouTube Music to Plex
```bash
python convert_playlist_aio_plex_spotify_youtube.py --source-service ytmusic --destination-service plex --playlist-url "https://music.youtube.com/playlist?list=your_ytmusic_playlist_id" --plex-url "http://your_plex_server:32400" --plex-token "your_plex_token" --playlist-name "Synced Playlist" --verbose
```

#### Sync Plex to Spotify
```bash
python convert_playlist_aio_plex_spotify_youtube.py --source-service plex --destination-service spotify --playlist-name "Synced Playlist" --cookies-path path/to/spotify_cookies.txt --verbose
```

#### Sync Plex to YouTube Music
```bash
python convert_playlist_aio_plex_spotify_youtube.py --source-service plex --destination-service ytmusic --playlist-name "Synced Playlist" --yt-oauth-json path/to/ytmusic_oauth.json --verbose
```

## Version History
- **v1.0:** Initial version with basic syncing functionality.
- **v1.1:** Improved flexibility by making `--playlist-url` optional for Plex sources; enhanced README for ease of use.

---

Enjoy seamless playlist syncing between Spotify, YouTube Music, and Plex!
