from datetime import datetime
from functools import partial
from StreamServiceBase import StreamServiceBase
import asyncio
import websockets
import threading
from unidecode import unidecode
import requests
import json
import logging
import tkinter as tk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketServer:
    def __init__(self, port, app):
        self.app = app
        self.port = port
        self.current_song = None
        self.app.lyrics = {}
        self.stream_service = StreamServiceBase()

    async def handle_connection(self, ws, path):
        try:
            while True:
                message = await ws.recv()
                # print(f"Received message: {message}")
                res = json.loads(message)
                self.get_lyrics(res)
                if (
                    res["currentDuration"] != "NaN"
                    and int(res["currentDuration"]) in self.app.lyrics
                ):
                    lyric = self.app.lyrics_seconds[int(res["currentDuration"])]
                    self.app.update_lyrics(lyric)
                    self.app.current_seconds = int(res["currentDuration"])
                    self.app.logged_timestamp = datetime.now().timestamp()
        except websockets.exceptions.ConnectionClosedOK:
            print("Connection closed normally.")
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed with error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    async def start(self):
        print("starting server...")
        async with websockets.serve(
            self.handle_connection, "127.0.0.1", self.port
        ) as server:
            await server.wait_closed()
        # server = await websockets.serve(self.handle_connection, "127.0.0.1", self.port)
        # await server.wait_closed()

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

            self.app.lyrics.clear()
            self.lyrics_not_found = False

            result = self.stream_service.get_lyrics(song_name, song_artists_and_album)
            self.create_lyrics_mappings(result)

    def create_lyrics_mappings(self, res) -> None:  # NOQA
        self.app.menu.delete(0, "end")
        self.app.lyrics_list = res
        for index, line in enumerate(res):
            self.app.lyrics[line["seconds"]] = line["lyrics"]
            self.app.menu.add_command(
                label=line["lyrics"],
                command=partial(self.app.reset_lyrics, index),
            )
        current_line = ""
        for second in range(res[-1]["seconds"]):
            try:
                current_line = self.app.lyrics[second]
                self.app.lyrics_seconds[second] = current_line
            except KeyError:
                self.app.lyrics_seconds[second] = current_line


class LyricsApp:
    def __init__(self):
        self.lyrics = {}
        self.lyrics_list = []
        self.lyrics_seconds = {}
        self.current_seconds = 0
        self.logged_timestamp = 0
        self.root = tk.Tk()
        self.root.title("Floating Window")
        self.root.transient()
        # Set window attributes to always stay on top
        self.root.wm_attributes("-topmost", 1)

        self.root.overrideredirect(True)
        # self.root.attributes("-alpha", 0.4)  # 完全透明
        self.root.attributes("-transparent", True)
        self.root.config(bg="systemTransparent")
        self.root.wm_attributes("-topmost", 1)

        # move the root to the middle of the screen and botton
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 1000
        window_height = 100
        # 计算窗口位置
        x_position = (screen_width - window_width) // 2
        y_position = screen_height - window_height

        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        # Example label in the window with larger font
        self.lyrics_label = tk.Label(
            self.root,
            text="Music Lyrics",
            font=("Helvetica", 40),
            bg="systemTransparent",
            fg="white",
        )
        self.lyrics_label.pack(expand=True)
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Option 1", command=self.reset_lyrics)

        self.menu.add_separator()
        self.menu.add_command(label="Exit", command=self.root.quit)

        # Bind right-click to the label
        self.lyrics_label.bind("<Button-2>", self.show_menu)

    def show_menu(self, event):
        self.menu.post(event.x_root, event.y_root)

    def reset_lyrics(self, index=0):

        known_time = self.lyrics_list[index]["seconds"]
        current_time = self.current_seconds

        current_timestamp = datetime.now().timestamp()
        logger.info(
            f"{self.lyrics_list[index]} selected in {self.current_seconds+int(current_timestamp - self.logged_timestamp)} seconds"
        )
        offset = (
            current_time + int(current_timestamp - self.logged_timestamp) - known_time
        )
        new_lyrics = {}
        for second in range(self.lyrics_list[-1]["seconds"]):
            try:
                current_line = self.lyrics[second]
                new_lyrics[second + offset] = current_line
            except KeyError:
                new_lyrics[second + offset] = current_line

        self.lyrics_seconds = new_lyrics

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
