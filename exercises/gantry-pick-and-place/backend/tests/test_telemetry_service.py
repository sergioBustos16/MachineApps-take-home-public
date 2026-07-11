from types import SimpleNamespace

import pytest

from domain.models import MotionPlan, Position, RobotConfiguration
from gantry_fsm import PickAndPlaceStates, RobotOperationStates
from telemetry_service import get_current_target


@pytest.fixture
def motion_plan():
    config = RobotConfiguration(
        cube_position=Position(x=100.0, y=100.0, z=0.0),
        destination_position=Position(x=800.0, y=800.0, z=0.0),
        safe_z=500.0,
        home_position=Position(x=0.0, y=0.0, z=0.0),
        travel_speed=90.0,
        home_speed=50.0,
    )
    return MotionPlan.from_config(config)


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (str(RobotOperationStates.HOMING), (0.0, 0.0, 0.0)),
        (str(PickAndPlaceStates.MOVEABOVECUBE), (100.0, 100.0, 500.0)),
        (str(PickAndPlaceStates.LOWERTOCUBE), (100.0, 100.0, 0.0)),
        (str(PickAndPlaceStates.LIFTCUBE), (100.0, 100.0, 500.0)),
        (str(PickAndPlaceStates.MOVEABOVEDESTINATION), (800.0, 800.0, 500.0)),
        (str(PickAndPlaceStates.LOWERTODESTINATION), (800.0, 800.0, 0.0)),
        (str(PickAndPlaceStates.LIFTFROMDESTINATION), (800.0, 800.0, 500.0)),
    ],
)
def test_get_current_target_maps_motion_states(motion_plan, state, expected):
    fsm = SimpleNamespace(state=state, motion_plan=motion_plan)

    target = get_current_target(fsm)

    assert target is not None
    assert (target.x, target.y, target.z) == expected


@pytest.mark.parametrize(
    "state",
    [
        "ready",
        str(PickAndPlaceStates.CLOSEGRIPPER),
        str(PickAndPlaceStates.OPENGRIPPER),
        str(PickAndPlaceStates.COMPLETED),
    ],
)
def test_get_current_target_returns_none_when_no_motion_target(motion_plan, state):
    fsm = SimpleNamespace(state=state, motion_plan=motion_plan)

    assert get_current_target(fsm) is None
