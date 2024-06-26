import requests
from unidecode import unidecode


class StreamServiceBase:
    def __init__(self):
        self.song = None

    def get_textyl_url(self, song_name, song_info):
        query = []
        if song_name:
            song_name = (
                song_name.replace("feat.", "")
                .replace("original motion picture soundtrack", "")
                .replace("from the original motion picture", "")
            )
            song_name = "".join(
                char for char in song_name if char.isalnum() or char.isspace()
            ).split()
            for word in song_name:
                if word not in query:
                    query.append(word)

        if song_info:
            song_info = (
                song_info.replace("feat.", "")
                .replace("original motion picture soundtrack", "")
                .replace("from the original motion picture", "")
            )
            song_info = "".join(
                char for char in song_info if char.isalnum() or char.isspace()
            ).split()
            for word in song_info:
                if word not in query:
                    query.append(word)

        if query:
            # https://stackoverflow.com/a/64417359/14113019

            return f"http://api.textyl.co/api/lyrics?q={unidecode('%20'.join(query))}"

        return ""

    def get_lyrics(self, song_name: str, artist_name: str):
        url = self.get_textyl_url(song_name, artist_name)
        if not url:
            return {}
        result = requests.get(url, verify=False)
        return result.json()
