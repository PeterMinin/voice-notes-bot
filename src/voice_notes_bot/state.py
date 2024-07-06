import json
from dataclasses import dataclass
from pathlib import Path

_state_filename = "state.json"


@dataclass
class State:
    _state_dir: Path
    last_update_id: int
    message_id_to_filename: dict[str, str]

    @classmethod
    def load(cls, state_dir: Path | str) -> "State":
        state_dir = Path(state_dir)
        state_dir.mkdir(exist_ok=True)
        filepath = state_dir / _state_filename
        if filepath.is_file():
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
        return State(
            _state_dir=state_dir,
            last_update_id=data.get("last_update_id", 0),
            message_id_to_filename=data.get("message_id_to_filename", {})
        )

    def save(self) -> None:
        data = {
            "last_update_id": self.last_update_id,
            "message_id_to_filename": self.message_id_to_filename,
        }
        with open(self._state_dir / _state_filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent="\t")
