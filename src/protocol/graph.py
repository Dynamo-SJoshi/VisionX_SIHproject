# File: src/protocol/graph.py
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ProtocolStep:
    """Represents a single step in the experiment protocol."""
    id: str
    name: str
    description: str
    allowed_next: List[str]


class ProtocolGraph:
    """Loads and validates experiment protocol graphs from JSON definitions."""

    def __init__(self, config_path: str | Path):
        self.config_path = Path(config_path)
        self.experiment_id: str = ""
        self.description: str = ""
        self.start_step: str = ""
        self.steps: Dict[str, ProtocolStep] = {}
        self.load_config()

    def load_config(self) -> None:
        """Loads and parses the protocol JSON configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Protocol configuration file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.experiment_id = data.get("experiment_id", "unknown_experiment")
        self.description = data.get("description", "")
        self.start_step = data.get("start_step", "S1")

        raw_steps = data.get("steps", [])
        self.steps = {}
        for step_data in raw_steps:
            step = ProtocolStep(
                id=step_data["id"],
                name=step_data.get("name", ""),
                description=step_data.get("description", ""),
                allowed_next=step_data.get("allowed_next", [])
            )
            self.steps[step.id] = step

    def get_step(self, step_id: str) -> Optional[ProtocolStep]:
        """Returns step object by step ID, or None if not found."""
        return self.steps.get(step_id)

    def get_allowed_next(self, step_id: str) -> List[str]:
        """Returns list of allowed next step IDs following step_id."""
        step = self.get_step(step_id)
        return step.allowed_next if step else []

    def is_allowed_transition(self, current_step_id: str, target_step_id: str) -> bool:
        """Validates whether transitioning from current_step_id to target_step_id is permitted."""
        allowed = self.get_allowed_next(current_step_id)
        return target_step_id in allowed
