import argparse
import asyncio
import json
from pathlib import Path

from telegram import Bot, Update

from .audiofile import get_as_ogg_opus
from .config import Config
from .state import State


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "bot_json",
        type=Path,
        help='Path to a secret JSON file with an "api_token" field',
    )
    parser.add_argument("config_json", type=Path)
    parser.add_argument("state_dir", type=Path)
    args = parser.parse_args()
    return args


def get_api_token(bot_json: Path) -> str:
    with open(bot_json) as f:
        data = json.load(f)
    api_token = data["api_token"]
    return api_token


async def handle_update(update: Update, bot: Bot, config: Config) -> bool:
    if update.message.chat.id != config.chat_id:
        print("New chat:", update)
        return True
    if update.message.text == "/start":
        await bot.send_message(text="Hi!", chat_id=config.chat_id)
        return True
    print("Unexpected update:", update)
    return False


async def process_updates(bot: Bot, config: Config, state: State):
    last_update_id = state.last_update_id
    updates = await bot.get_updates(offset=last_update_id + 1)
    if not updates:
        print("No updates")
        return
    for i, update in enumerate(updates):
        if await handle_update(update, bot, config):
            state.last_update_id = update.update_id
        else:
            print(f"Updates left unprocessed: {len(updates) - i}")
            return
    print("All updates processed")


async def send_voice_note(bot: Bot, chat_id: int, audio_file: Path):
    assert audio_file.is_file()
    with get_as_ogg_opus(audio_file) as ogg_file:
        await bot.send_voice(chat_id, ogg_file, caption=audio_file.stem)


async def process_voice_notes(
    bot: Bot, chat_id: int, recordings_dir: Path, state: State
):
    old_files = state.old_files

    audio_files = sorted(recordings_dir.glob("*.m4a"), key=lambda file: file.name)
    sent_files = []
    for file in audio_files:
        if file.name in old_files:
            continue
        await send_voice_note(bot, chat_id, file)
        sent_files.append(file.name)

    if sent_files:
        state.old_files = old_files + sent_files
        print(f"Notes sent: {len(sent_files)}")
    else:
        print("No new notes")


async def run_bot(token: str, config: Config, state: State):
    bot = Bot(token)
    async with bot:
        await process_updates(bot, config, state)
        if config.chat_id is None:
            return
        await process_voice_notes(bot, config.chat_id, config.recordings_dir, state)


def main():
    args = get_args()
    token = get_api_token(args.bot_json)
    config = Config.load(args.config_json)
    state = State.load(args.state_dir)
    asyncio.run(run_bot(token, config, state))
    state.save()


if __name__ == "__main__":
    main()
