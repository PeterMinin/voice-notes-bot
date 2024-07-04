import argparse
import asyncio
import contextlib
import json
import tempfile
from pathlib import Path
from typing import Iterator

import ffmpeg
from telegram import Bot


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


def get_config(config_json: Path) -> dict:
    with open(config_json, encoding="utf-8") as f:
        data = json.load(f)
    return data


def ensure_dir(dir_path: Path) -> Path:
    dir_path.mkdir(exist_ok=True)
    return dir_path


async def process_updates(bot: Bot, target_chat_id: int | None):
    updates = await bot.get_updates()
    if not updates:
        print("No updates")
        return
    for update in updates:
        if update.message.chat.id != target_chat_id:
            print("New chat:", update)
            continue
        if update.message.text == "/start":
            await bot.send_message(text="Hi!", chat_id=target_chat_id)


def is_ogg_opus(audio_file: Path) -> bool:
    probe = ffmpeg.probe(audio_file)
    streams = probe["streams"]
    assert len(streams) == 1
    stream = streams[0]
    return stream["format_name"] == "ogg" and stream["codec_name"] == "opus"


def convert_to_ogg_opus(input_audio_file: Path, output_file: Path):
    if output_file.suffix.lower() != ".ogg":
        raise ValueError(f"Expected a .ogg output file, got {output_file.name}")
    stream = ffmpeg.input(input_audio_file)
    stream = ffmpeg.filter(
        stream,
        "silenceremove",
        stop_periods=-1,
        stop_duration=1,
        stop_threshold="-50dB",
    )
    stream = ffmpeg.output(
        stream, str(output_file), acodec="libopus", audio_bitrate=128 * 1024
    )
    ffmpeg.run(stream, quiet=True)
    assert output_file.is_file()


@contextlib.contextmanager
def get_as_ogg_opus(audio_file: Path) -> Iterator[Path]:
    if audio_file.suffix.lower() == ".ogg":
        if is_ogg_opus(audio_file):
            yield audio_file
            return
    with tempfile.TemporaryDirectory() as tmpdir:
        converted_file = Path(tmpdir) / (audio_file.stem + ".ogg")
        convert_to_ogg_opus(audio_file, converted_file)
        yield converted_file


async def send_voice_note(bot: Bot, chat_id: int, audio_file: Path):
    assert audio_file.is_file()
    with get_as_ogg_opus(audio_file) as ogg_file:
        await bot.send_voice(chat_id, ogg_file, caption=audio_file.stem)


async def process_voice_notes(
    bot: Bot, chat_id: int, recordings_dir: Path, state_dir: Path
):
    old_files_list = state_dir / "old_files.json"
    if old_files_list.is_file():
        with open(old_files_list) as f:
            old_files = json.load(f)
            if not isinstance(old_files, list):
                raise ValueError(f"Unexpected format in {old_files_list}")
    else:
        old_files = []

    audio_files = sorted(recordings_dir.glob("*.m4a"), key=lambda file: file.name)
    sent_files = []
    for file in audio_files:
        if file.name in old_files:
            continue
        await send_voice_note(bot, chat_id, file)
        sent_files.append(file.name)

    if sent_files:
        with open(old_files_list, "w") as f:
            json.dump(old_files + sent_files, f)
        print(f"Notes sent: {len(sent_files)}")
    else:
        print("No new notes")


async def run_bot(token: str, config: dict, state_dir: Path):
    bot = Bot(token)
    async with bot:
        chat_id = config.get("chat_id")
        if chat_id is None:
            await process_updates(bot, None)
            return

        recordings_dir = Path(config["recordings_dir"])
        if not recordings_dir.is_dir():
            raise ValueError(f"recordings_dir must be a dir ({recordings_dir})")
        assert state_dir.is_dir()

        await process_voice_notes(bot, chat_id, recordings_dir, state_dir)


def main():
    args = get_args()
    token = get_api_token(args.bot_json)
    config = get_config(args.config_json)
    state_dir = ensure_dir(Path(args.state_dir))
    asyncio.run(run_bot(token, config, state_dir))


if __name__ == "__main__":
    main()
