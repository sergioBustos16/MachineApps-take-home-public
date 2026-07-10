import pytest
from pydantic import ValidationError
from domain.models import Position, RobotConfiguration

def test_valid_configuration():
    config = RobotConfiguration(
        cube_position=Position(x=100, y=200, z=0),
        destination_position=Position(x=500, y=600, z=10),
        safe_z=300,
        home_position=Position(x=0, y=0, z=0),
        travel_speed=80.0,
        home_speed=40.0
    )
    assert config.travel_speed == 80.0
    assert config.safe_z == 300.0

def test_invalid_safe_z_fails():
    with pytest.raises(ValidationError, match="safe_z must be above both cube and destination"):
        RobotConfiguration(
            cube_position=Position(x=100, y=200, z=200),
            destination_position=Position(x=500, y=600, z=10),
            safe_z=150,  # Safe Z is under Cube Z!
            home_position=Position(x=0, y=0, z=0)
        )

def test_out_of_bounds_coordinates_fails():
    with pytest.raises(ValidationError, match="outside valid limits"):
        RobotConfiguration(
            cube_position=Position(x=-1500, y=200, z=0),  # X out of limits!
            destination_position=Position(x=500, y=600, z=10),
            safe_z=300,
            home_position=Position(x=0, y=0, z=0)
        )

def test_non_finite_coordinates_fails():
    with pytest.raises(ValidationError, match="Coordinates must be finite real numbers"):
        RobotConfiguration(
            cube_position=Position(x=float('nan'), y=200, z=0),
            destination_position=Position(x=500, y=600, z=10),
            safe_z=300,
            home_position=Position(x=0, y=0, z=0)
        )

def test_identical_positions_fails():
    with pytest.raises(ValidationError, match="Cube and destination coordinates cannot be identical"):
        RobotConfiguration(
            cube_position=Position(x=100, y=100, z=0),
            destination_position=Position(x=100, y=100, z=0),  # Identical!
            safe_z=300,
            home_position=Position(x=0, y=0, z=0)
        )

def test_invalid_speed_bounds_fails():
    with pytest.raises(ValidationError, match="Speeds must be between 0 and 100"):
        RobotConfiguration(
            cube_position=Position(x=100, y=200, z=0),
            destination_position=Position(x=500, y=600, z=10),
            safe_z=300,
            home_position=Position(x=0, y=0, z=0),
            travel_speed=120.0  # Speed over 100!
        )
