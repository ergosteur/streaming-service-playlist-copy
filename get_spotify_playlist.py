import requests
from http.cookiejar import MozillaCookieJar

# Load cookies from cookies.txt
cookie_jar = MozillaCookieJar('cookies.txt')
cookie_jar.load(ignore_discard=True, ignore_expires=True)

# Step 2: Get the Access Token from Spotify using sp_dc
def get_access_token():
    # Spotify's endpoint to retrieve access token using `sp_dc` cookie
    token_url = 'https://open.spotify.com/get_access_token'
    response = requests.get(token_url, cookies=cookie_jar)

    if response.status_code == 200:
        access_token = response.json().get('accessToken')
        return access_token
    else:
        print(f"Failed to retrieve access token: {response.status_code} - {response.text}")
        return None

# Fetch the access token
access_token = get_access_token()
if access_token is None:
    exit("Unable to retrieve access token.")

# Step 3: Use the access token to retrieve the playlist
def get_playlist_tracks(playlist_id):
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        tracks = response.json()['items']
        for idx, item in enumerate(tracks):
            track = item['track']
            print(f"{idx + 1}. {track['name']} - {track['artists'][0]['name']}")
    else:
        print(f"Failed to retrieve playlist: {response.status_code} - {response.text}")

# Replace this with your playlist ID
playlist_id = '0gs7NUp6PWdSejauN7Mloa'
get_playlist_tracks(playlist_id)
