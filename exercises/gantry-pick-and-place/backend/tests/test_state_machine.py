import pytest
import time
from unittest.mock import patch
from robot_sim import Robot
from robot_adapter import RobotAdapter
from gantry_fsm import GantryRobotStateMachine, RobotStates, RobotOperationStates, PickAndPlaceStates
from domain.exceptions import RobotBusyError, FaultResetError
from domain.enums import CubeStatus
from domain.models import Position, RobotConfiguration

@pytest.fixture
def test_config():
    return RobotConfiguration(
        cube_position=Position(x=100.0, y=100.0, z=0.0),
        destination_position=Position(x=800.0, y=800.0, z=0.0),
        safe_z=500.0,
        home_position=Position(x=0.0, y=0.0, z=0.0),
        travel_speed=90.0,
        home_speed=50.0
    )

def test_homing_block_and_successful_sequence_cycle(test_config):
    # Setup mock time advancement to make the simulated physical movement run instantly
    current_fake_time = 100.0

    def mock_perf_counter():
        nonlocal current_fake_time
        current_fake_time += 0.2  # Advance 200ms per clock check
        return current_fake_time

    with patch("time.perf_counter", side_effect=mock_perf_counter):
        robot = Robot()
        adapter = RobotAdapter(robot)
        fsm = GantryRobotStateMachine(adapter)
        
        # 1. State machine defaults to requires_homing=True
        assert fsm.requires_homing
        
        # 2. Starting sequence before homing must raise RobotBusyError
        with pytest.raises(RobotBusyError, match="Gantry must be homed"):
             fsm.start_sequence(test_config)
             
        # 3. Trigger homing (starts at (0,0,0) and targets (0,0,0), instant completion)
        fsm.start_homing(test_config)
        assert fsm.state == str(RobotOperationStates.HOMING)
        
        # Simulate ticks until homing completes
        ticks = 0
        while fsm.state == str(RobotOperationStates.HOMING) and ticks < 100:
             fsm.execute_current_callback()
             ticks += 1
             
        assert fsm.state == "ready"
        assert not fsm.requires_homing  # requires_homing is now cleared!
        
        # 4. Trigger actual sequence
        fsm.start_sequence(test_config)
        assert fsm.state == str(PickAndPlaceStates.MOVEABOVECUBE)
        assert fsm.cube_status == CubeStatus.AT_SOURCE
        
        # Simulate sequence ticks
        # Step 1: Raise to safe Z, traverse X/Y at safe Z, then settle above cube
        ticks = 0
        while fsm.state == str(PickAndPlaceStates.MOVEABOVECUBE) and ticks < 100:
             fsm.execute_current_callback()
             ticks += 1
        assert fsm.state == str(PickAndPlaceStates.LOWERTOCUBE)

        # Step 2: Lower to cube (100,100,500) -> (100,100,0)
        ticks = 0
        while fsm.state == str(PickAndPlaceStates.LOWERTOCUBE) and ticks < 100:
             fsm.execute_current_callback()
             ticks += 1
        assert fsm.state == str(PickAndPlaceStates.CLOSEGRIPPER)

        # Step 3: Close gripper -> cube attached
        fsm.execute_current_callback()
        assert fsm.state == str(PickAndPlaceStates.LIFTCUBE)
        assert fsm.cube_status == CubeStatus.ATTACHED

        # Ensure while attached, the cube's position tracks the gantry
        fsm.execute_current_callback()
        gantry_pos = adapter.get_position()
        assert fsm.cube_current_position == gantry_pos

def test_fault_stops_active_motion(test_config):
    robot = Robot(initial_position=[800.0, 800.0, 500.0])
    adapter = RobotAdapter(robot)
    fsm = GantryRobotStateMachine(adapter)

    fsm.start_homing(test_config)
    fsm.execute_current_callback()
    assert adapter.is_moving()

    fsm._state_started_at = time.monotonic() - 61.0
    fsm.execute_current_callback()

    assert fsm.state == "fault"
    assert fsm.last_error.code == "MOTION_TIMEOUT"
    assert not adapter.is_moving()
    assert adapter.get_velocity() == (0, 0, 0)

def test_move_above_cube_raises_to_safe_z_before_xy_travel(test_config):
    robot = Robot(initial_position=[0.0, 0.0, 0.0])
    adapter = RobotAdapter(robot)
    fsm = GantryRobotStateMachine(adapter)
    fsm.requires_homing = False

    fsm.start_sequence(test_config)
    fsm.execute_current_callback()

    vx, vy, vz = adapter.get_velocity()
    assert vx == 0.0
    assert vy == 0.0
    assert vz > 0.0


def test_homing_raises_to_safe_z_before_xy_travel(test_config):
    robot = Robot(initial_position=[800.0, 800.0, 0.0])
    adapter = RobotAdapter(robot)
    fsm = GantryRobotStateMachine(adapter)

    fsm.start_homing(test_config)
    fsm.execute_current_callback()

    vx, vy, vz = adapter.get_velocity()
    assert vx == 0.0
    assert vy == 0.0
    assert vz > 0.0
