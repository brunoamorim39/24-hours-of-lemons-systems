"""Unit tests for GPIO controller."""

import pytest
from libs.hw.gpio import GPIOController


def test_gpio_init_dry_run():
    """Test GPIO initialization in dry-run mode."""
    pin_config = {"DRS_BTN": 17, "BRAKE_SWITCH": 27, "DRS_LED": 22}

    gpio = GPIOController(pin_config, dry_run=True)

    assert gpio.dry_run is True
    assert gpio.pin_config == pin_config


def test_gpio_read_input_dry_run():
    """Test reading GPIO input in dry-run mode."""
    pin_config = {"DRS_BTN": 17}
    gpio = GPIOController(pin_config, dry_run=True)

    # Initially should be False
    assert gpio.read_input("DRS_BTN") is False

    # Set mock input
    gpio.set_mock_input("DRS_BTN", True)
    assert gpio.read_input("DRS_BTN") is True


def test_gpio_write_output_dry_run():
    """Test writing GPIO output in dry-run mode."""
    pin_config = {"DRS_LED": 22}
    gpio = GPIOController(pin_config, dry_run=True)

    # Should not raise error
    gpio.write_output("DRS_LED", True)
    assert gpio._state["DRS_LED"] is True

    gpio.write_output("DRS_LED", False)
    assert gpio._state["DRS_LED"] is False


def test_gpio_callback():
    """Test GPIO callback on state change."""
    pin_config = {"DRS_BTN": 17}
    gpio = GPIOController(pin_config, dry_run=True)

    callback_called = []

    def callback(value):
        callback_called.append(value)

    gpio.register_callback("DRS_BTN", callback)

    # Trigger state change
    gpio.set_mock_input("DRS_BTN", True)

    assert len(callback_called) == 1
    assert callback_called[0] is True


def test_gpio_debounce():
    """Test GPIO debouncing."""
    pin_config = {"DRS_BTN": 17}
    gpio = GPIOController(pin_config, dry_run=True)

    # Set initial state
    gpio.set_mock_input("DRS_BTN", True)

    # Read with debounce
    value1 = gpio.read_input("DRS_BTN", debounce_ms=100)
    assert value1 is True

    # Change state immediately
    gpio._state["DRS_BTN"] = False

    # Should still read old value due to debounce
    value2 = gpio.read_input("DRS_BTN", debounce_ms=100)
    assert value2 is True  # Debounced
