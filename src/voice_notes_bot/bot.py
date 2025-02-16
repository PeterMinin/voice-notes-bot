import argparse
import asyncio
import json
from pathlib import Path

import telegram as tg
from telegram.constants import ReactionEmoji

from .audiofile import get_as_ogg_opus
from .config import Config
from .state import State


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "secrets_json",
        type=Path,
        help='Path to a JSON file with an "api_token" field',
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


def is_done_reaction(reaction_updated: tg.MessageReactionUpdated) -> bool:
    for reaction in reaction_updated.new_reaction:
        if isinstance(reaction, tg.ReactionTypeEmoji) and reaction.emoji in [
            ReactionEmoji.THUMBS_UP,
            ReactionEmoji.OK_HAND_SIGN,
        ]:
            return True
    return False


async def handle_reaction(
    reaction: tg.MessageReactionUpdated, config: Config, state: State
) -> bool:
    message_id = reaction.message_id
    if not is_done_reaction(reaction):
        print(
            f"Info: Ignoring reaction {reaction.new_reaction} for message {message_id}"
        )
        return True
    try:
        source_filename = state.message_id_to_filename[str(message_id)]
    except KeyError:  # May happen if multiple instances of the server exist
        print(
            f"Warning: Ignoring reaction to message {message_id} that we don't remember sending"
        )
        return True
    if source_filename is None:
        print(f"Info: Ignoring a repeated Done reaction for message {message_id}")
        return True
    file = config.recordings_dir / source_filename
    if file.is_file():
        file.unlink()
    else:
        print(f"Info: Note source {source_filename} already deleted")
    ok = await reaction.chat.set_message_reaction(message_id, ReactionEmoji.HANDSHAKE)
    assert ok
    state.message_id_to_filename[str(message_id)] = None
    return True


async def handle_update(update: tg.Update, config: Config, state: State) -> bool:
    if update.message:
        if update.message.chat.id != config.chat_id:
            print("New chat: ID", update.message.chat.id)
            print("Raw update:", update)
            return True
        if update.message.text == "/start":
            bot = update.get_bot()
            await bot.send_message(text="Hi!", chat_id=config.chat_id)
            return True
    if update.message_reaction:
        return await handle_reaction(update.message_reaction, config, state)
    print("Unexpected update:", update)
    return False


async def process_updates(bot: tg.Bot, config: Config, state: State):
    last_update_id = state.last_update_id
    updates = await bot.get_updates(
        offset=last_update_id + 1,
        allowed_updates=[tg.Update.MESSAGE, tg.Update.MESSAGE_REACTION],
    )
    if not updates:
        print("No updates")
        return
    if not config.background:
        print(f"Processing updates: {len(updates)}")
    for i, update in enumerate(updates):
        if await handle_update(update, config, state):
            state.last_update_id = update.update_id
        else:
            print(f"Updates left unprocessed: {len(updates) - i} of {len(updates)}")
            return
    if config.background:
        print(f"Updates processed: {len(updates)}")


async def send_voice_note(
    bot: tg.Bot, chat_id: int, audio_file: Path, semaphore
) -> tg.Message:
    assert audio_file.is_file()
    with get_as_ogg_opus(audio_file) as ogg_file:
        await semaphore.acquire()
        try:
            return await bot.send_voice(chat_id, ogg_file, caption=audio_file.stem)
        finally:
            semaphore.release()


async def process_voice_notes(bot: tg.Bot, config: Config, state: State):
    chat_id = config.chat_id
    recordings_dir = config.recordings_dir
    background = config.background
    assert chat_id is not None

    old_files = set(state.message_id_to_filename.values())
    old_files.discard(None)
    new_files = [
        file for file in recordings_dir.glob("*.m4a") if file.name not in old_files
    ]
    if not new_files:
        print("No new notes")
        return
    new_files = sorted(new_files, key=lambda file: file.name)
    if not background:
        print(f"Sending notes: {len(new_files)}")
    # Sending asynchronously: send one at a time, convert the rest while sending,
    # delete converted as soon as it's been sent.
    # Potentially all converted notes will be stored simultaneously.
    semaphore = asyncio.BoundedSemaphore()
    tasks = []
    async with asyncio.TaskGroup() as taskGroup:
        for file in new_files:
            tasks.append(
                taskGroup.create_task(send_voice_note(bot, chat_id, file, semaphore))
            )
    for task, file in zip(tasks, new_files):
        message = await task
        state.message_id_to_filename[message.id] = file.name
    if background:
        print(f"Notes sent: {len(new_files)}")


async def run_bot(token: str, config: Config, state: State):
    bot = tg.Bot(token)
    async with bot:
        await process_updates(bot, config, state)
        if config.chat_id is None:
            return
        await process_voice_notes(bot, config, state)


def main():
    args = get_args()
    token = get_api_token(args.secrets_json)
    config = Config.load(args.config_json)
    state = State.load(args.state_dir)
    asyncio.run(run_bot(token, config, state))
    state.save()


if __name__ == "__main__":
    main()
