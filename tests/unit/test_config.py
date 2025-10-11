"""Unit tests for configuration loading."""

import tempfile
from pathlib import Path
import pytest
import yaml

from libs.util.config import load_config, get_nested, _deep_merge


def test_load_single_config():
    """Test loading a single config file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"key": "value", "number": 42}, f)
        config_path = f.name

    try:
        config = load_config(config_path)
        assert config["key"] == "value"
        assert config["number"] == 42
    finally:
        Path(config_path).unlink()


def test_load_merged_config():
    """Test loading and merging multiple config files."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f1:
        yaml.dump({"a": 1, "b": 2}, f1)
        config1 = f1.name

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f2:
        yaml.dump({"b": 99, "c": 3}, f2)
        config2 = f2.name

    try:
        config = load_config(config1, config2)
        assert config["a"] == 1
        assert config["b"] == 99  # Overridden by config2
        assert config["c"] == 3
    finally:
        Path(config1).unlink()
        Path(config2).unlink()


def test_deep_merge():
    """Test deep dictionary merging."""
    base = {"a": 1, "nested": {"x": 10, "y": 20}}
    override = {"b": 2, "nested": {"y": 99, "z": 30}}

    result = _deep_merge(base, override)

    assert result["a"] == 1
    assert result["b"] == 2
    assert result["nested"]["x"] == 10
    assert result["nested"]["y"] == 99  # Overridden
    assert result["nested"]["z"] == 30


def test_get_nested():
    """Test getting nested config values."""
    config = {"servo": {"open_angle": 90, "closed_angle": 0}}

    assert get_nested(config, "servo.open_angle") == 90
    assert get_nested(config, "servo.closed_angle") == 0
    assert get_nested(config, "servo.missing", default=42) == 42
    assert get_nested(config, "nonexistent.path", default="default") == "default"


def test_load_nonexistent_config():
    """Test loading a non-existent config file."""
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/config.yaml")
