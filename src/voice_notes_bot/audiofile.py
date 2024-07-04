import contextlib
import tempfile
from pathlib import Path
from typing import Iterator

import ffmpeg


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
