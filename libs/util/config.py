"""Configuration loading and merging utilities."""

import os
from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(*config_paths: str) -> Dict[str, Any]:
    """
    Load and merge YAML configuration files.

    Args:
        *config_paths: Paths to YAML config files (later files override earlier)

    Returns:
        Merged configuration dictionary

    Example:
        config = load_config("config/roles/drs.yaml", "config/cars/car1.yaml")
    """
    merged_config = {}

    for path in config_paths:
        if not Path(path).exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r") as f:
            config = yaml.safe_load(f) or {}

        # Deep merge
        merged_config = _deep_merge(merged_config, config)

    # Environment variable expansion
    merged_config = _expand_env_vars(merged_config)

    return merged_config


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """Recursively merge two dictionaries."""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def _expand_env_vars(config: Any) -> Any:
    """Recursively expand environment variables in config values."""
    if isinstance(config, dict):
        return {key: _expand_env_vars(value) for key, value in config.items()}
    elif isinstance(config, list):
        return [_expand_env_vars(item) for item in config]
    elif isinstance(config, str):
        return os.path.expandvars(config)
    else:
        return config


def get_nested(config: Dict, path: str, default: Any = None) -> Any:
    """
    Get nested config value using dot notation.

    Args:
        config: Configuration dictionary
        path: Dot-separated path (e.g., "servo.open_angle")
        default: Default value if path not found

    Returns:
        Config value or default

    Example:
        angle = get_nested(config, "servo.open_angle", 90)
    """
    keys = path.split(".")
    value = config

    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]

    return value
