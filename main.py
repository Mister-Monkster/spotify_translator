import spotipy
import spotipy.util as util

import os

from gtts import gTTS
from dotenv import load_dotenv
import asyncio

from pyrogram import Client, filters, enums
from pyrogram.handlers import MessageHandler, DeletedMessagesHandler
from pyrogram.types import ChatEvent

global is_translate

is_translate: bool = False

load_dotenv()
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')

app = Client("my_account", api_id, api_hash)
app.set_parse_mode(enums.ParseMode.HTML)


async def spotify_translator(client, message):
    global is_translate
    await app.delete_messages(message.chat.id, message.id)
    is_translate = True

    try:
        spotipy_client = os.getenv("SPOTIFY_CLIENT")
        spotipy_secret = os.getenv("SPOTIFY_SECRET")
        scope = 'user-library-read user-read-playback-state user-read-currently-playing'
        token = util.prompt_for_user_token(
            scope,
            client_id=spotipy_client,
            client_secret=spotipy_secret,
            redirect_uri="http://localhost:8888/callback"
        )
        spotify = spotipy.Spotify(auth=token)
    except Exception as e:
        print(e)

    async def get_track_info(spotify_client):
        current_track = spotify_client.current_user_playing_track()
        data = current_track['item']
        result = {}
        artists = []
        for i in data['album']['artists']:
            if 'name' in i:
                url = i['external_urls']['spotify']
                name = i['name']
                artists.append(f'<a href="{url}">{name}</a>')

            track_name = data['name']
            track_url = data['external_urls']['spotify']
            duration = int(data['duration_ms']) / 1000
            duration_min = int(duration // 60)
            duration_sec = int(duration - duration_min * 60)
            progress = int(current_track['progress_ms'] / 1000)
            progress_min = int(progress // 60)
            progress_sec = int(progress - progress_min * 60)

            if len(str(progress_sec)) == 1:
                progress_sec = '0' + str(progress_sec)

            if len(str(duration_sec)) == 1:
                duration_sec = '0' + str(duration_sec)

            result['artists'] = ', '.join(artists)
            result['img_url'] = data['album']['images'][0]['url']
            result['track'] = f'<a href="{track_url}">{track_name}</a>'
            result['duration'] = f'{duration_min}:{duration_sec}'
            result['progress'] = f'{progress_min}:{progress_sec}'

            return result

    track = await get_track_info(spotify)
    text = ('<b>Вот что я слушаю в Spotify:</b>\n'
            f'{track["track"]}'
            f'\n{track["artists"]}'
            f'\n{track["progress"]}/{track["duration"]}')
    track_message = await app.send_photo(message.chat.id,
                                         track['img_url'], text)

    while track['progress'] != track['duration']:
        if not is_translate:
            await app.delete_messages(track_message.chat.id, track_message.id)
            return None
        try:
            await asyncio.sleep(1)
            new_track = await get_track_info(spotify)
            new_text = ('<b>Вот что я слушаю в Spotify:</b>\n'
                        f'{new_track["track"]}'
                        f'\n{new_track["artists"]}'
                        f'\n{new_track["progress"]}/{new_track["duration"]}')

            if new_text != text and track_message is not None:
                text = new_text
                await track_message.edit_text(new_text)

            elif new_text != text and track_message is None:
                track_message = await app.send_photo(message.chat.id,
                                                     new_track['img_url'],
                                                     new_text)
            else:
                await asyncio.sleep(0.75)
                await app.delete_messages(track_message.chat.id,
                                          track_message.id)
                track_message = None

            if new_track['img_url'] != track['img_url'] or new_track['track'] != track['track']:
                track = new_track
                await app.delete_messages(track_message.chat.id,
                                          track_message.id)
                track_message = await app.send_photo(message.chat.id,
                                                     new_track['img_url'],
                                                     new_text)

        except Exception as e:
            print(e)


async def stop(client, message):
    global is_translate
    await app.delete_messages(message.chat.id, message.id)
    is_translate = False


app.add_handler(MessageHandler(spotify_translator, filters=filters.me & filters.command('spotify', prefixes='/')))
app.add_handler(MessageHandler(stop, filters=filters.me & filters.command('stop', prefixes='/')))

app.run()
