import re
import requests
import os
import openai
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PATH = os.path.dirname(os.path.abspath(__file__))
with open(f"{PATH}/api.json", "r") as f:
    json_data = json.load(f)
    api_key = json_data["openai"]
client = openai.Client(api_key=api_key)


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

    def get_lrc_url(self, song_name: str, artist_name: str):
        song_name = (
            song_name.replace("feat.", "")
            .replace("original motion picture soundtrack", "")
            .replace("from the original motion picture", "")
        )
        logger.info(f"Searching for {song_name} by {artist_name}")
        return f"https://lrc.tczhong.com/lyrics?title={song_name}&artist={artist_name}"

    def get_lyrics(self, song_name: str, artist_name: str):
        url = self.get_lrc_url(song_name, artist_name)
        if not url:
            return {}
        lrc = self.check_lrc(url)
        if not lrc:
            # try again with new song name
            song_name = song_name.split("-")[0].strip()
            url = self.get_lrc_url(song_name, artist_name)
            lrc = self.check_lrc(url)
        if not lrc:
            result = self.call_openai(song_name, artist_name)
            result = json.loads(result)
            url = self.get_lrc_url(result["song_name"], result["artist_name"])
            lrc = self.check_lrc(url)
        if not lrc:
            return []
        # parse lrc
        result = []
        print(lrc)
        for line in lrc.split("\n"):
            if re.findall(r"\[\d+:\d+\.\d+\]", line):
                time = line[1:9]
                lyrics = line[11:]
                if "0" not in time or "offset" in time:
                    continue
                # seconds
                second = int(time.split(":")[0]) * 60 + int(float(time.split(":")[1]))
                result.append({"seconds": second, "lyrics": lyrics})
        return result

    def call_openai(self, song_name, artist_name):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"帮我找到歌名和歌手,如果是中文歌 只返回中文，歌手也是。一般书名号里的是歌曲名。 格式可能是[歌手] - [歌名]: {song_name} uploader: {artist_name} ,输出json，key是song_name and artist_name",
                }
            ],
            response_format={"type": "json_object"},
        )
        print(response.choices)
        return response.choices[0].message.content

    def check_lrc(self, url):
        result = requests.get(url, verify=False)
        lrc = result.text
        if "未找到匹配的歌词" in lrc or "Lyrics not found." in lrc:
            return None
        return lrc
