"""JSON syntax is a YAML subset, keeping this initial demo dependency-free."""
import json
import os
from dataclasses import dataclass, fields
from pathlib import Path

@dataclass(frozen=True)
class AppConfig:
    device_id: str = "edge_node_01"
    camera_id: str = "camera_01"
    confidence_threshold: float = 0.5
    detector: str = "demo"
    transport: str = "console"
    log_level: str = "INFO"

    def __post_init__(self):
        for name in ("device_id", "camera_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        if (type(self.confidence_threshold) not in (int, float)
                or not 0 <= self.confidence_threshold <= 1):
            raise ValueError("confidence_threshold must be between 0 and 1")
        if self.detector != "demo" or self.transport != "console":
            raise ValueError("Only demo detector and console transport are implemented")
        if self.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            raise ValueError("Unsupported log_level")

def load_config(path: str | Path | None = None) -> AppConfig:
    values = {}
    if path is not None:
        try:
            values = json.loads(Path(path).read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("Config must use JSON-compatible YAML syntax; see default.yaml") from exc
        if not isinstance(values, dict):
            raise ValueError("Config must be an object")
        unknown = set(values) - {field.name for field in fields(AppConfig)}
        if unknown:
            raise ValueError(f"Unknown config keys: {sorted(unknown)}")
    for name in ("device_id", "camera_id"):
        env_name = "EDGEAI_" + name.upper()
        if env_name in os.environ:
            values[name] = os.environ[env_name]
    return AppConfig(**values)
