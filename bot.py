import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
from pytgcalls.exceptions import NoActiveGroupCall
from yt_dlp import YoutubeDL

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

# ================== GLOBALS ==================
queues = {}  # chat_id: list of dicts {"title": str, "file": str}
current_song = {}  # chat_id: dict {"title": str, "file": str}

# ================== HELPERS ==================
ydl_opts = {
    "format": "bestaudio/best",
    "outtmpl": "%(title)s.%(ext)s",
    "quiet": True,
}

async def download_song(url: str) -> dict:
    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, lambda: YoutubeDL(ydl_opts).extract_info(url, download=True))
    file_path = YoutubeDL(ydl_opts).prepare_filename(info)
    return {"title": info.get("title", "Unknown"), "file": file_path}

async def play_next(chat_id: int):
    if chat_id not in queues or not queues[chat_id]:
        current_song.pop(chat_id, None)
        await call_py.leave_group_call(chat_id)
        return

    next_song = queues[chat_id].pop(0)
    current_song[chat_id] = next_song
    await call_py.change_stream(chat_id, AudioPiped(next_song["file"]))

# ================== COMMANDS ==================
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(_, message: Message):
    await message.reply_text(
        "🎧 **Music Bot Alive!**\n\n"
        "Add me to your group and start a group voice chat.\n"
        "Use `/play` replying to an audio or sending YouTube/Spotify URL.",
        quote=True
    )

@app.on_message(filters.command("play") & filters.group)
async def play_cmd(_, message: Message):
    chat_id = message.chat.id
    url_or_reply = None

    if message.reply_to_message and message.reply_to_message.audio:
        file_path = await message.reply_to_message.audio.download()
        song = {"title": message.reply_to_message.audio.file_name, "file": file_path}
    elif len(message.command) > 1:
        url_or_reply = message.command[1]
        try:
            song = await download_song(url_or_reply)
        except Exception as e:
            await message.reply_text(f"❌ Download error: {e}")
            return
    else:
        await message.reply_text("❌ Reply to audio or provide a YouTube/Spotify URL")
        return

    if chat_id in current_song:
        queues.setdefault(chat_id, []).append(song)
        await message.reply_text(f"✅ Added to queue: {song['title']}")
    else:
        current_song[chat_id] = song
        try:
            await call_py.join_group_call(chat_id, AudioPiped(song["file"]))
            await message.reply_text(f"▶️ Now playing: {song['title']}")
        except NoActiveGroupCall:
            await message.reply_text("❌ Start a group voice chat first")

@app.on_message(filters.command("skip") & filters.group)
async def skip_cmd(_, message: Message):
    chat_id = message.chat.id
    if chat_id not in current_song:
        await message.reply_text("❌ No active music to skip")
        return
    await play_next(chat_id)
    next_song = current_song.get(chat_id)
    if next_song:
        await message.reply_text(f"⏭️ Skipped! Now playing: {next_song['title']}")
    else:
        await message.reply_text("⏹️ Queue empty. Music stopped.")

@app.on_message(filters.command("pause") & filters.group)
async def pause_cmd(_, message: Message):
    chat_id = message.chat.id
    try:
        await call_py.pause_stream(chat_id)
        await message.reply_text("⏸️ Music paused")
    except Exception:
        await message.reply_text("❌ No active music")

@app.on_message(filters.command("resume") & filters.group)
async def resume_cmd(_, message: Message):
    chat_id = message.chat.id
    try:
        await call_py.resume_stream(chat_id)
        await message.reply_text("▶️ Music resumed")
    except Exception:
        await message.reply_text("❌ No active music")

@app.on_message(filters.command("stop") & filters.group)
async def stop_cmd(_, message: Message):
    chat_id = message.chat.id
    try:
        queues.pop(chat_id, None)
        current_song.pop(chat_id, None)
        await call_py.leave_group_call(chat_id)
        await message.reply_text("⏹️ Music stopped")
    except Exception:
        await message.reply_text("❌ No active music")

# ================== INLINE BUTTONS ==================
@app.on_message(filters.command("controls") & filters.group)
async def controls_cmd(_, message: Message):
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏯️ Pause", callback_data="pause"),
                InlineKeyboardButton("▶️ Resume", callback_data="resume"),
                InlineKeyboardButton("⏭️ Skip", callback_data="skip"),
                InlineKeyboardButton("⏹️ Stop", callback_data="stop"),
            ]
        ]
    )
    await message.reply_text("🎛️ Music Controls:", reply_markup=buttons)

@app.on_callback_query()
async def button_cb(_, query):
    chat_id = query.message.chat.id
    if query.data == "pause":
        await call_py.pause_stream(chat_id)
        await query.answer("⏸️ Paused")
    elif query.data == "resume":
        await call_py.resume_stream(chat_id)
        await query.answer("▶️ Resumed")
    elif query.data == "skip":
        await play_next(chat_id)
        next_song = current_song.get(chat_id)
        if next_song:
            await query.answer(f"⏭️ Skipped! Now playing: {next_song['title']}")
        else:
            await query.answer("⏹️ Queue empty")
    elif query.data == "stop":
        queues.pop(chat_id, None)
        current_song.pop(chat_id, None)
        await call_py.leave_group_call(chat_id)
        await query.answer("⏹️ Stopped")

# ================== MAIN ==================
async def main():
    await app.start()
    await call_py.start()
    print("✅ Music Bot Started")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())