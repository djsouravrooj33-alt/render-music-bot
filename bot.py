import os
from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client("musicbot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
call = PyTgCalls(app)

@app.on_message(filters.command("play") & filters.group)
async def play(_, msg):
    if not msg.reply_to_message:
        await msg.reply("🎵 mp3 file reply করে /play দিন")
        return
    audio = await msg.reply_to_message.download()
    await call.join_group_call(
        msg.chat.id,
        AudioPiped(audio, HighQualityAudio()),
    )
    await msg.reply("▶️ Music started")

@app.on_message(filters.command("stop") & filters.group)
async def stop(_, msg):
    await call.leave_group_call(msg.chat.id)
    await msg.reply("⏹️ Music stopped")

app.start()
call.start()
print("Bot running...")
