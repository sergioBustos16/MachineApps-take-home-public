from types import SimpleNamespace

from controller import RobotController
from domain.enums import CubeStatus
from domain.models import Position, RobotConfiguration
from robot_adapter import RobotAdapter
from robot_sim import Robot


class StubConfigService:
    def __init__(self, config):
        self._config = config

    def get_cached(self):
        return self._config


def test_ready_snapshot_reports_cube_current_position_at_configured_source():
    config = RobotConfiguration(
        cube_position=Position(x=200.0, y=200.0, z=0.0),
        destination_position=Position(x=800.0, y=800.0, z=0.0),
        safe_z=500.0,
        home_position=Position(x=0.0, y=0.0, z=0.0),
    )
    adapter = RobotAdapter(Robot())
    fsm = SimpleNamespace(
        robot=adapter,
        execution_config=None,
        active_sequence_id=None,
        state="ready",
        requires_homing=True,
        motion_plan=None,
        cube_status=CubeStatus.AT_SOURCE,
        cube_current_position=(0.0, 0.0, 0.0),
        last_error=None,
    )
    controller = RobotController(fsm, StubConfigService(config))

    snapshot = controller.get_latest_snapshot()

    assert snapshot.cube_position == snapshot.cube_current_position
    assert snapshot.cube_current_position.x == 200.0
    assert snapshot.cube_current_position.y == 200.0
    assert snapshot.cube_current_position.z == 0.0