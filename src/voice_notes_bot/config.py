import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    chat_id: int | None
    recordings_dirs: list[Path]
    background: bool  # Adjust output for automated execution, not interactive

    def __post_init__(self):
        if not self.recordings_dirs:
            raise ValueError("No recordings_dirs provided")
        for path in self.recordings_dirs:
            if not path.is_dir():
                raise ValueError(f"Not a directory: {path}")

    @classmethod
    def load(cls, config_json: Path | str):
        with open(config_json, encoding="utf-8") as f:
            data = json.load(f)
        recordings_dirs = data["recordings_dirs"]
        for i in range(len(recordings_dirs)):
            recordings_dirs[i] = Path(recordings_dirs[i]).expanduser()
        return Config(
            chat_id=data.get("chat_id"),
            recordings_dirs=recordings_dirs,
            background=data.get("background", False),
        )
