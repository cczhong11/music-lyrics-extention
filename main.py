from StreamServiceBase import StreamServiceBase
import asyncio
import websockets
import threading
from unidecode import unidecode
import requests
import json

import tkinter as tk


class WebSocketServer:
    def __init__(self, port, app):
        self.app = app
        self.port = port
        self.current_song = None
        self.lyrics = {}
        self.stream_service = StreamServiceBase()

    async def handle_connection(self, ws, path):
        while True:
            message = await ws.recv()
            # print(f"Received message: {message}")
            res = json.loads(message)
            self.get_lyrics(res)
            if int(res["currentDuration"]) in self.lyrics:
                lyric = self.lyrics[int(res["currentDuration"])]
                self.app.update_lyrics(lyric)

    async def start(self):
        print("starting server...")
        server = await websockets.serve(self.handle_connection, "127.0.0.1", self.port)
        await server.wait_closed()

    # Method to fetch the lyrics based on the song details sent by Chromium extension
    def get_lyrics(self, song_details) -> None:
        if None in song_details.values():
            return

        self.current_duration = song_details["currentDuration"]

        song_name = song_details["songName"].lower()
        song_artists_and_album = song_details["songArtistsAndAlbum"].lower()

        song = f"{song_name} - {song_artists_and_album}"
        if (
            song != self.current_song
        ):  # don't fetch lyrics again until the track is changed
            self.current_song = song

            self.lyrics.clear()
            self.lyrics_not_found = False

            result = self.stream_service.get_lyrics(song_name, song_artists_and_album)
            self.create_lyrics_mappings(result)

    def create_lyrics_mappings(self, res) -> None:  # NOQA
        for line in res:
            self.lyrics[line["seconds"]] = line["lyrics"]

        current_line = ""
        for second in range(list(self.lyrics.keys())[-1]):
            try:
                current_line = self.lyrics[second]
            except KeyError:
                self.lyrics[second] = current_line
        print(self.lyrics)


class LyricsApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Floating Window")

        # Set window attributes to always stay on top
        self.root.wm_attributes("-topmost", 1)

        self.root.configure(bg="black")

        # Example label in the window with larger font
        self.lyrics_label = tk.Label(
            self.root,
            text="This window is always on top!",
            font=("Helvetica", 24),
            bg="black",
            fg="white",
        )
        self.lyrics_label.pack(padx=20, pady=20)

    def run_websocket_server(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ws_server = WebSocketServer(8765, self)
        loop.run_until_complete(ws_server.start())

    def run(self):
        threading.Thread(target=self.run_websocket_server, daemon=True).start()
        self.root.mainloop()

    def update_lyrics(self, lyric):
        self.lyrics_label.config(text=lyric)


def main():
    app = LyricsApp()
    # asyncio.create_task(app.run_server())
    app.run()


if __name__ == "__main__":
    main()
