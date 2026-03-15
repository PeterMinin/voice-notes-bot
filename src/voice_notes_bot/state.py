import json
from dataclasses import dataclass
from pathlib import Path

from .config import Config

_state_filename = "state.json"
_version = 2


@dataclass
class State:
    _state_dir: Path
    last_update_id: int
    message_id_to_file_path: dict[str, str | None]  # None means the file has been deleted

    @classmethod
    def load(cls, state_dir: Path | str, config: Config) -> "State":
        state_dir = Path(state_dir)
        state_dir.mkdir(exist_ok=True)
        filepath = state_dir / _state_filename
        if filepath.is_file():
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            version = data.get("version", 1)
            if version < 2:
                # Filenames to file paths
                message_id_to_filename = data.pop("message_id_to_filename")
                message_id_to_file_path = {}
                for message_id, filename in message_id_to_filename.items():
                    if filename is None:
                        message_id_to_file_path[message_id] = None
                        continue
                    for recordings_dir in config.recordings_dirs:
                        path = recordings_dir / filename
                        if path.is_file():
                            message_id_to_file_path[message_id] = str(path)
                            break
                    else:
                        print(f"Warning: couldn't find {filename} to migrate")
                        message_id_to_file_path[message_id] = None
                data["message_id_to_file_path"] = message_id_to_file_path
        else:
            data = {}
        return State(
            _state_dir=state_dir,
            last_update_id=data.get("last_update_id", 0),
            message_id_to_file_path=data.get("message_id_to_file_path", {}),
        )

    def save(self) -> None:
        data = {
            "version": _version,
            "last_update_id": self.last_update_id,
            "message_id_to_file_path": self.message_id_to_file_path,
        }
        with open(self._state_dir / _state_filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent="\t")
