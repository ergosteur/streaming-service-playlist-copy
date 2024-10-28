import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import threading

def run_script():
    # Clear the output console
    output_text.delete("1.0", tk.END)
    
    # Collect user inputs
    source_service = source_var.get()
    destination_service = destination_var.get()
    playlist_url = url_entry.get()
    playlist_name = name_entry.get()
    append_replace = append_replace_var.get()
    unmatched_output = unmatched_output_entry.get()
    verbose = verbose_var.get()
    cookies_path = cookies_entry.get()
    oauth_path = oauth_entry.get()
    plex_url = plex_url_entry.get()
    plex_token = plex_token_entry.get()

    # Build command list
    command = [
        "python", "convert_playlist_aio_plex_spotify_youtube.py",
        "--source-service", source_service,
        "--destination-service", destination_service,
    ]
    if playlist_url:
        command.extend(["--playlist-url", playlist_url])
    if playlist_name:
        command.extend(["--playlist-name", playlist_name])
    if append_replace:
        command.append("--append" if append_replace == "Append" else "--replace")
    if unmatched_output:
        command.extend(["--unmatched-output", unmatched_output])
    if verbose:
        command.append("--verbose")
    if cookies_path:
        command.extend(["--cookies-path", cookies_path])
    if oauth_path:
        command.extend(["--yt-oauth-json", oauth_path])
    if plex_url:
        command.extend(["--plex-url", plex_url])
    if plex_token:
        command.extend(["--plex-token", plex_token])

    # Run the command in a separate thread to keep GUI responsive
    thread = threading.Thread(target=execute_command, args=(command,))
    thread.start()

def execute_command(command):
    # Run the command and capture output
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Continuously read and display the output in the Text widget
    for line in process.stdout:
        output_text.insert(tk.END, line)
        output_text.see(tk.END)  # Scroll to the end of the output
        root.update_idletasks()  # Refresh the GUI window
    
    process.stdout.close()
    process.wait()
    if process.returncode == 0:
        output_text.insert(tk.END, "\nScript completed successfully!\n")
    else:
        output_text.insert(tk.END, "\nScript encountered an error.\n")

def browse_file(entry_field):
    file_path = filedialog.askopenfilename()
    entry_field.delete(0, tk.END)
    entry_field.insert(0, file_path)

# Initialize GUI
root = tk.Tk()
root.title("Playlist Sync Tool")
root.geometry("600x750")

# Grid Layout Configuration
root.grid_columnconfigure(1, weight=1)

# Source Service Dropdown
tk.Label(root, text="Source Service:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
source_var = tk.StringVar(value="spotify")
source_dropdown = tk.OptionMenu(root, source_var, "spotify", "ytmusic", "plex")
source_dropdown.grid(row=0, column=1, sticky="w", padx=5, pady=5)

# Destination Service Dropdown
tk.Label(root, text="Destination Service:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
destination_var = tk.StringVar(value="ytmusic")
destination_dropdown = tk.OptionMenu(root, destination_var, "spotify", "ytmusic", "plex")
destination_dropdown.grid(row=1, column=1, sticky="w", padx=5, pady=5)

# Playlist URL Entry
tk.Label(root, text="Playlist URL (optional):").grid(row=2, column=0, sticky="e", padx=5, pady=5)
url_entry = tk.Entry(root, width=40)
url_entry.grid(row=2, column=1, sticky="w", padx=5, pady=5)

# Playlist Name Entry
tk.Label(root, text="Playlist Name (optional):").grid(row=3, column=0, sticky="e", padx=5, pady=5)
name_entry = tk.Entry(root, width=40)
name_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)

# Append/Replace Option
tk.Label(root, text="Mode:").grid(row=4, column=0, sticky="e", padx=5, pady=5)
append_replace_var = tk.StringVar(value="Append")
append_replace_dropdown = tk.OptionMenu(root, append_replace_var, "Append", "Replace")
append_replace_dropdown.grid(row=4, column=1, sticky="w", padx=5, pady=5)

# Unmatched Output Entry
tk.Label(root, text="Unmatched Output (optional):").grid(row=5, column=0, sticky="e", padx=5, pady=5)
unmatched_output_entry = tk.Entry(root, width=40)
unmatched_output_entry.grid(row=5, column=1, sticky="w", padx=5, pady=5)

# Verbose Mode Checkbox
verbose_var = tk.BooleanVar()
verbose_check = tk.Checkbutton(root, text="Verbose Mode", variable=verbose_var)
verbose_check.grid(row=6, column=1, sticky="w", padx=5, pady=5)

# Cookies Path Entry with Browse Button
tk.Label(root, text="Cookies Path (optional):").grid(row=7, column=0, sticky="e", padx=5, pady=5)
cookies_entry = tk.Entry(root, width=30)
cookies_entry.grid(row=7, column=1, sticky="w", padx=5, pady=5)
cookies_browse = tk.Button(root, text="Browse", command=lambda: browse_file(cookies_entry))
cookies_browse.grid(row=7, column=2, padx=5, pady=5)

# OAuth JSON Path Entry with Browse Button
tk.Label(root, text="OAuth JSON Path (optional):").grid(row=8, column=0, sticky="e", padx=5, pady=5)
oauth_entry = tk.Entry(root, width=30)
oauth_entry.grid(row=8, column=1, sticky="w", padx=5, pady=5)
oauth_browse = tk.Button(root, text="Browse", command=lambda: browse_file(oauth_entry))
oauth_browse.grid(row=8, column=2, padx=5, pady=5)

# Plex URL Entry
tk.Label(root, text="Plex URL:").grid(row=9, column=0, sticky="e", padx=5, pady=5)
plex_url_entry = tk.Entry(root, width=40)
plex_url_entry.grid(row=9, column=1, sticky="w", padx=5, pady=5)

# Plex Token Entry
tk.Label(root, text="Plex Token:").grid(row=10, column=0, sticky="e", padx=5, pady=5)
plex_token_entry = tk.Entry(root, width=40)
plex_token_entry.grid(row=10, column=1, sticky="w", padx=5, pady=5)

# Output Console
output_text = tk.Text(root, wrap="word", height=10)
output_text.grid(row=11, column=0, columnspan=3, padx=5, pady=5)

# Run Button
run_button = tk.Button(root, text="Run Script", command=run_script)
run_button.grid(row=12, column=1, pady=20)

# Start GUI loop
root.mainloop()
