import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
from pytgcalls.exceptions import NoActiveGroupCall

# ================== ENV ==================
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise RuntimeError("❌ API_ID / API_HASH / BOT_TOKEN missing")

# ================== CLIENTS ==================
app = Client(
    "music-bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

call_py = PyTgCalls(app)

# ================== START COMMAND ==================
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(_, message: Message):
    await message.reply_text(
        "🎧 **Music Bot is Alive!**\n\n"
        "Start a group voice chat\n"
        "Reply to an MP3 file with `/play`",
        quote=True
    )

# ================== PLAY COMMAND ==================
@app.on_message(filters.command("play") & filters.group)
async def play_cmd(_, message: Message):
    if not message.reply_to_message or not message.reply_to_message.audio:
        await message.reply_text("❌ Reply to an MP3 file and use `/play`")
        return

    audio = message.reply_to_message.audio
    file_path = await audio.download()

    chat_id = message.chat.id

    try:
        await call_py.join_group_call(
            chat_id,
            AudioPiped(file_path),
        )
        await message.reply_text("▶️ **Music started in voice chat**")

    except NoActiveGroupCall:
        await message.reply_text("❌ Please start the group voice chat first")

    except Exception as e:
        await message.reply_text(f"⚠️ Error: `{e}`")

# ================== STOP COMMAND ==================
@app.on_message(filters.command("stop") & filters.group)
async def stop_cmd(_, message: Message):
    try:
        await call_py.leave_group_call(message.chat.id)
        await message.reply_text("⏹️ Music stopped")
    except Exception:
        await message.reply_text("❌ No active music is playing")

# ================== MAIN ==================
async def main():
    await app.start()
    await call_py.start()
    print("✅ Music Bot Started")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())