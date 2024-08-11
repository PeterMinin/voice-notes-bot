import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    chat_id: int | None
    recordings_dir: Path

    def __post_init__(self):
        if not self.recordings_dir.is_dir():
            raise ValueError(f"recordings_dir must be a dir ({self.recordings_dir})")

    @classmethod
    def load(cls, config_json: Path | str):
        with open(config_json, encoding="utf-8") as f:
            data = json.load(f)
        return Config(
            chat_id=data.get("chat_id"),
            recordings_dir=Path(data["recordings_dir"]).expanduser(),
        )
