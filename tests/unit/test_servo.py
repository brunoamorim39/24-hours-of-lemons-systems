"""Unit tests for servo controller."""

import pytest
from libs.hw.servo import ServoController


def test_servo_init_dry_run():
    """Test servo initialization in dry-run mode."""
    servo = ServoController(
        channel=0, min_angle=0, max_angle=90, dry_run=True
    )

    assert servo.dry_run is True
    assert servo.channel == 0
    assert servo.min_angle == 0
    assert servo.max_angle == 90


def test_servo_set_angle():
    """Test setting servo angle."""
    servo = ServoController(
        channel=0, min_angle=0, max_angle=90, dry_run=True
    )

    servo.set_angle(45)
    assert servo.get_angle() == 45

    servo.set_angle(90)
    assert servo.get_angle() == 90


def test_servo_angle_limits():
    """Test servo angle safety limits."""
    servo = ServoController(
        channel=0, min_angle=0, max_angle=90, dry_run=True
    )

    # Should raise on out-of-range angle
    with pytest.raises(ValueError):
        servo.set_angle(-10)

    with pytest.raises(ValueError):
        servo.set_angle(100)


def test_servo_angle_to_pulse():
    """Test angle to PWM pulse conversion."""
    servo = ServoController(
        channel=0,
        min_angle=0,
        max_angle=180,
        min_pulse=150,
        max_pulse=600,
        dry_run=True,
    )

    # Test min angle
    pulse_min = servo._angle_to_pulse(0)
    assert pulse_min == 150

    # Test max angle
    pulse_max = servo._angle_to_pulse(180)
    assert pulse_max == 600

    # Test mid angle
    pulse_mid = servo._angle_to_pulse(90)
    assert pulse_mid == 375  # Midpoint of 150 and 600
